import io

import pandas as pd
import pytest
from fastapi import BackgroundTasks, HTTPException
from starlette.datastructures import UploadFile
from starlette.requests import Request

from app.services import upload_service


def _make_request(app, *, csrf_token: str):
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

    async def receive():
        return {"type": "http.request", "body": b"", "more_body": False}

    return Request(scope, receive)


def _make_upload_file(name: str, content: bytes, content_type: str) -> UploadFile:
    return UploadFile(
        filename=name,
        file=io.BytesIO(content),
        headers={"content-type": content_type},
    )


def test_upload_service_success(build_app, monkeypatch, db_path):
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
    monkeypatch.setattr(pd, "read_excel", lambda *_args, **_kwargs: df)

    result = upload_service.handle_excel_upload(
        request=request,
        background_tasks=BackgroundTasks(),
        csrf_token="csrf",
        file=file,
    )
    assert result["success"] is True


def test_upload_service_rejects_bad_extension(build_app, db_path):
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


def test_upload_service_rejects_bad_content_type(build_app, monkeypatch, db_path):
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
    monkeypatch.setattr(pd, "read_excel", lambda *_args, **_kwargs: df)

    with pytest.raises(HTTPException) as exc:
        upload_service.handle_excel_upload(
            request=request,
            background_tasks=BackgroundTasks(),
            csrf_token="csrf",
            file=file,
        )
    assert exc.value.status_code == 400


def test_upload_service_missing_columns(build_app, monkeypatch, db_path):
    app = build_app()
    request = _make_request(app, csrf_token="csrf")
    file = _make_upload_file(
        "upload.xlsx", b"dummy", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    df = pd.DataFrame({"소재지(지번)": ["addr"]})
    monkeypatch.setattr(pd, "read_excel", lambda *_args, **_kwargs: df)

    with pytest.raises(HTTPException) as exc:
        upload_service.handle_excel_upload(
            request=request,
            background_tasks=BackgroundTasks(),
            csrf_token="csrf",
            file=file,
        )
    assert exc.value.status_code == 400
