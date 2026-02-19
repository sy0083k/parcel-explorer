import io
from typing import Any

import pandas as pd
import pytest
from _pytest.monkeypatch import MonkeyPatch
from fastapi import BackgroundTasks, HTTPException
from fastapi import FastAPI
from starlette.datastructures import UploadFile
from starlette.requests import Request

from app.services import upload_service


class DummyExcelFile:
    def __init__(self, *_args: object, sheet_names: list[str] | None = None, **_kwargs: object) -> None:
        self.sheet_names = sheet_names or ["목록"]


def _make_request(app: FastAPI, *, csrf_token: str) -> Request:
    scope = {
        "type": "http",
        "method": "POST",
        "path": "/admin/upload",
        "headers": [],
        "client": ("127.0.0.1", 50000),
        "server": ("testserver", 80),
        "scheme": "http",
        "root_path": "",
        "query_string": b"",
        "app": app,
        "session": {"user": "admin", "csrf_token": csrf_token},
    }

    async def receive() -> dict[str, Any]:
        return {"type": "http.request", "body": b"", "more_body": False}

    return Request(scope, receive)


def _make_upload_file(name: str, content: bytes, content_type: str) -> UploadFile:
    return UploadFile(
        filename=name,
        file=io.BytesIO(content),
        headers={"content-type": content_type},
    )


def test_upload_service_success(
    build_app: Any, monkeypatch: MonkeyPatch, db_path: Any
) -> None:
    app = build_app()
    from app.db.connection import db_connection
    from app.repositories import idle_land_repository

    with db_connection() as conn:
        idle_land_repository.init_db(conn)
    request = _make_request(app, csrf_token="csrf")
    file = _make_upload_file(
        "upload.xlsx", b"dummy", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

    df = pd.DataFrame(
        {
            "소재지(지번)": ["addr"],
            "(공부상)지목": ["답"],
            "(공부상)면적(㎡)": [12.5],
            "행정재산": ["Y"],
            "일반재산": ["N"],
            "담당자연락처": ["010"],
        }
    )
    monkeypatch.setattr(pd, "ExcelFile", lambda *_args, **_kwargs: DummyExcelFile(sheet_names=["목록"]))
    monkeypatch.setattr(pd, "read_excel", lambda *_args, **_kwargs: df)

    result = upload_service.handle_excel_upload(
        request=request,
        background_tasks=BackgroundTasks(),
        csrf_token="csrf",
        file=file,
    )
    assert result["success"] is True


def test_upload_service_rejects_bad_extension(build_app: Any, db_path: Any) -> None:
    app = build_app()
    request = _make_request(app, csrf_token="csrf")
    file = _make_upload_file("upload.txt", b"dummy", "text/plain")
    with pytest.raises(HTTPException) as exc:
        upload_service.handle_excel_upload(
            request=request,
            background_tasks=BackgroundTasks(),
            csrf_token="csrf",
            file=file,
        )
    assert exc.value.status_code == 400


def test_upload_service_rejects_bad_content_type(
    build_app: Any, monkeypatch: MonkeyPatch, db_path: Any
) -> None:
    app = build_app()
    request = _make_request(app, csrf_token="csrf")
    file = _make_upload_file("upload.xlsx", b"dummy", "text/plain")

    df = pd.DataFrame(
        {
            "소재지(지번)": ["addr"],
            "(공부상)지목": ["답"],
            "(공부상)면적(㎡)": [12.5],
            "행정재산": ["Y"],
            "일반재산": ["N"],
            "담당자연락처": ["010"],
        }
    )
    monkeypatch.setattr(pd, "ExcelFile", lambda *_args, **_kwargs: DummyExcelFile(sheet_names=["목록"]))
    monkeypatch.setattr(pd, "read_excel", lambda *_args, **_kwargs: df)

    with pytest.raises(HTTPException) as exc:
        upload_service.handle_excel_upload(
            request=request,
            background_tasks=BackgroundTasks(),
            csrf_token="csrf",
            file=file,
        )
    assert exc.value.status_code == 400


def test_upload_service_missing_columns(
    build_app: Any, monkeypatch: MonkeyPatch, db_path: Any
) -> None:
    app = build_app()
    request = _make_request(app, csrf_token="csrf")
    file = _make_upload_file(
        "upload.xlsx", b"dummy", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    df = pd.DataFrame({"소재지(지번)": ["addr"]})
    monkeypatch.setattr(pd, "ExcelFile", lambda *_args, **_kwargs: DummyExcelFile(sheet_names=["목록"]))
    monkeypatch.setattr(pd, "read_excel", lambda *_args, **_kwargs: df)

    with pytest.raises(HTTPException) as exc:
        upload_service.handle_excel_upload(
            request=request,
            background_tasks=BackgroundTasks(),
            csrf_token="csrf",
            file=file,
        )
    assert exc.value.status_code == 400


def test_upload_service_sheet_name_fallback(
    build_app: Any, monkeypatch: MonkeyPatch, db_path: Any
) -> None:
    app = build_app()
    from app.db.connection import db_connection
    from app.repositories import idle_land_repository

    with db_connection() as conn:
        idle_land_repository.init_db(conn)
    request = _make_request(app, csrf_token="csrf")
    file = _make_upload_file(
        "upload.xlsx", b"dummy", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    df = pd.DataFrame(
        {
            "소재지(지번)": ["addr"],
            "(공부상)지목": ["답"],
            "(공부상)면적(㎡)": [12.5],
            "행정재산": ["Y"],
            "일반재산": ["N"],
            "담당자연락처": ["010"],
        }
    )

    called: dict[str, object] = {}

    def _read_excel(_excel: object, *, sheet_name: str) -> pd.DataFrame:
        called["sheet_name"] = sheet_name
        return df

    monkeypatch.setattr(pd, "ExcelFile", lambda *_args, **_kwargs: DummyExcelFile(sheet_names=["시트1"]))
    monkeypatch.setattr(pd, "read_excel", _read_excel)

    result = upload_service.handle_excel_upload(
        request=request,
        background_tasks=BackgroundTasks(),
        csrf_token="csrf",
        file=file,
    )
    assert result["success"] is True
    assert called["sheet_name"] == "시트1"


@pytest.mark.parametrize(
    ("filename", "expected_engine", "content_type"),
    [
        ("upload.xlsx", "openpyxl", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
        ("upload.xls", "xlrd", "application/vnd.ms-excel"),
    ],
)
def test_upload_service_selects_excel_engine_by_extension(
    build_app: Any,
    monkeypatch: MonkeyPatch,
    db_path: Any,
    filename: str,
    expected_engine: str,
    content_type: str,
) -> None:
    app = build_app()
    from app.db.connection import db_connection
    from app.repositories import idle_land_repository

    with db_connection() as conn:
        idle_land_repository.init_db(conn)

    request = _make_request(app, csrf_token="csrf")
    file = _make_upload_file(filename, b"dummy", content_type)
    df = pd.DataFrame(
        {
            "소재지(지번)": ["addr"],
            "(공부상)지목": ["답"],
            "(공부상)면적(㎡)": [12.5],
            "행정재산": ["Y"],
            "일반재산": ["N"],
            "담당자연락처": ["010"],
        }
    )

    called: dict[str, object] = {}

    def _excel_file(*_args: object, engine: str, **_kwargs: object) -> DummyExcelFile:
        called["engine"] = engine
        return DummyExcelFile(sheet_names=["목록"])

    monkeypatch.setattr(pd, "ExcelFile", _excel_file)
    monkeypatch.setattr(pd, "read_excel", lambda *_args, **_kwargs: df)

    result = upload_service.handle_excel_upload(
        request=request,
        background_tasks=BackgroundTasks(),
        csrf_token="csrf",
        file=file,
    )
    assert result["success"] is True
    assert called["engine"] == expected_engine
