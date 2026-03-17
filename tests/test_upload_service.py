import io
import logging
from typing import Any

import pandas as pd
import pytest
from _pytest.monkeypatch import MonkeyPatch

from app.services import upload_service
from app.services.service_errors import AuthError, ValidationError
from app.services.service_models import RequestContext, UploadedFileInput


class DummyExcelFile:
    def __init__(self, *_args: object, sheet_names: list[str] | None = None, **_kwargs: object) -> None:
        self.sheet_names = sheet_names or ["목록"]


def _make_command(*, csrf_valid: bool = True) -> upload_service.UploadCommand:
    return upload_service.UploadCommand(
        context=RequestContext(
            request_id="req-1",
            actor="admin",
            client_ip="127.0.0.1",
            csrf_valid=csrf_valid,
        ),
        requested_sheet="목록",
        max_upload_size_mb=10,
        max_upload_rows=100,
    )


def _make_upload_file(name: str, content: bytes, content_type: str) -> UploadedFileInput:
    return UploadedFileInput(
        filename=name,
        content_type=content_type,
        file=io.BytesIO(content),
    )


def _valid_dataframe() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "소재지(지번)": ["addr"],
            "(공부상)지목": ["답"],
            "(공부상)면적(㎡)": [12.5],
            "행정재산": ["Y"],
            "일반재산": ["N"],
            "담당자연락처": ["010"],
        }
    )


def test_upload_service_success(build_app: Any, monkeypatch: MonkeyPatch, db_path: Any) -> None:
    build_app()
    from app.db.connection import db_connection
    from app.repositories import poi_repository

    with db_connection() as conn:
        poi_repository.init_db(conn)

    monkeypatch.setattr(pd, "ExcelFile", lambda *_args, **_kwargs: DummyExcelFile(sheet_names=["목록"]))
    monkeypatch.setattr(pd, "read_excel", lambda *_args, **_kwargs: _valid_dataframe())

    result = upload_service.handle_excel_upload(
        _make_command(),
        file_input=_make_upload_file(
            "upload.xlsx",
            b"PK\x03\x04dummy",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        ),
    )
    assert isinstance(result, upload_service.UploadSuccessResult)
    assert result.payload["success"] is True


def test_upload_service_emits_audit_log_on_success(
    build_app: Any, monkeypatch: MonkeyPatch, db_path: Any, caplog: pytest.LogCaptureFixture
) -> None:
    build_app()
    from app.db.connection import db_connection
    from app.repositories import poi_repository

    with db_connection() as conn:
        poi_repository.init_db(conn)

    monkeypatch.setattr(pd, "ExcelFile", lambda *_args, **_kwargs: DummyExcelFile(sheet_names=["목록"]))
    monkeypatch.setattr(pd, "read_excel", lambda *_args, **_kwargs: _valid_dataframe())

    with caplog.at_level(logging.INFO, logger="app.services.upload_service"):
        result = upload_service.handle_excel_upload(
            _make_command(),
            file_input=_make_upload_file(
                "upload.xlsx",
                b"PK\x03\x04dummy",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            ),
        )

    assert isinstance(result, upload_service.UploadSuccessResult)
    success_record = next(record for record in caplog.records if record.event == "admin.upload.succeeded")
    assert success_record.upload_filename == "upload.xlsx"
    assert success_record.row_count == 1
    assert success_record.geom_job_id == result.geom_job_id


def test_upload_service_emits_audit_log_on_validation_failure(
    monkeypatch: MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    monkeypatch.setattr(pd, "ExcelFile", lambda *_args, **_kwargs: DummyExcelFile(sheet_names=["목록"]))
    monkeypatch.setattr(pd, "read_excel", lambda *_args, **_kwargs: pd.DataFrame({"소재지(지번)": ["addr"]}))

    with caplog.at_level(logging.WARNING, logger="app.services.upload_service"):
        with pytest.raises(ValidationError):
            upload_service.handle_excel_upload(
                _make_command(),
                file_input=_make_upload_file(
                    "upload.xlsx",
                    b"PK\x03\x04dummy",
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                ),
            )

    rejected_record = next(record for record in caplog.records if record.event == "admin.upload.rejected")
    assert rejected_record.upload_filename == "upload.xlsx"
    assert rejected_record.reason == "missing_required_columns"
    assert rejected_record.row_count == 1


def test_upload_service_rejects_bad_extension() -> None:
    with pytest.raises(ValidationError) as exc:
        upload_service.handle_excel_upload(
            _make_command(),
            file_input=_make_upload_file("upload.txt", b"dummy", "text/plain"),
        )
    assert exc.value.status_code == 400


def test_upload_service_rejects_bad_content_type(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setattr(pd, "ExcelFile", lambda *_args, **_kwargs: DummyExcelFile(sheet_names=["목록"]))
    monkeypatch.setattr(pd, "read_excel", lambda *_args, **_kwargs: _valid_dataframe())

    with pytest.raises(ValidationError) as exc:
        upload_service.handle_excel_upload(
            _make_command(),
            file_input=_make_upload_file("upload.xlsx", b"PK\x03\x04dummy", "text/plain"),
        )
    assert exc.value.status_code == 400


def test_upload_service_missing_columns(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setattr(pd, "ExcelFile", lambda *_args, **_kwargs: DummyExcelFile(sheet_names=["목록"]))
    monkeypatch.setattr(pd, "read_excel", lambda *_args, **_kwargs: pd.DataFrame({"소재지(지번)": ["addr"]}))

    with pytest.raises(ValidationError) as exc:
        upload_service.handle_excel_upload(
            _make_command(),
            file_input=_make_upload_file(
                "upload.xlsx",
                b"PK\x03\x04dummy",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            ),
        )
    assert exc.value.status_code == 400


def test_upload_service_sheet_name_fallback(build_app: Any, monkeypatch: MonkeyPatch, db_path: Any) -> None:
    build_app()
    from app.db.connection import db_connection
    from app.repositories import poi_repository

    with db_connection() as conn:
        poi_repository.init_db(conn)

    called: dict[str, object] = {}

    def _read_excel(_excel: object, *, sheet_name: str) -> pd.DataFrame:
        called["sheet_name"] = sheet_name
        return _valid_dataframe()

    monkeypatch.setattr(pd, "ExcelFile", lambda *_args, **_kwargs: DummyExcelFile(sheet_names=["시트1"]))
    monkeypatch.setattr(pd, "read_excel", _read_excel)

    result = upload_service.handle_excel_upload(
        _make_command(),
        file_input=_make_upload_file(
            "upload.xlsx",
            b"PK\x03\x04dummy",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        ),
    )
    assert isinstance(result, upload_service.UploadSuccessResult)
    assert called["sheet_name"] == "시트1"


@pytest.mark.parametrize(
    ("filename", "expected_engine", "content_type", "content"),
    [
        (
            "upload.xlsx",
            "openpyxl",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            b"PK\x03\x04dummy",
        ),
        (
            "upload.xls",
            "xlrd",
            "application/vnd.ms-excel",
            b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1dummy",
        ),
    ],
)
def test_upload_service_selects_excel_engine_by_extension(
    build_app: Any,
    monkeypatch: MonkeyPatch,
    db_path: Any,
    filename: str,
    expected_engine: str,
    content_type: str,
    content: bytes,
) -> None:
    build_app()
    from app.db.connection import db_connection
    from app.repositories import poi_repository

    with db_connection() as conn:
        poi_repository.init_db(conn)

    called: dict[str, object] = {}

    def _excel_file(*_args: object, engine: str, **_kwargs: object) -> DummyExcelFile:
        called["engine"] = engine
        return DummyExcelFile(sheet_names=["목록"])

    monkeypatch.setattr(pd, "ExcelFile", _excel_file)
    monkeypatch.setattr(pd, "read_excel", lambda *_args, **_kwargs: _valid_dataframe())

    result = upload_service.handle_excel_upload(
        _make_command(),
        file_input=_make_upload_file(filename, content, content_type),
    )
    assert isinstance(result, upload_service.UploadSuccessResult)
    assert called["engine"] == expected_engine


@pytest.mark.unit
def test_upload_service_rejects_magic_bytes_mismatch() -> None:
    with pytest.raises(ValidationError) as exc:
        upload_service.handle_excel_upload(
            _make_command(),
            file_input=_make_upload_file(
                "malicious.xlsx",
                b"\x00\x00\x00\x00malicious content",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            ),
        )
    assert exc.value.status_code == 400


@pytest.mark.unit
def test_upload_service_emits_audit_log_on_magic_bytes_rejection(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.WARNING, logger="app.services.upload_service"):
        with pytest.raises(ValidationError):
            upload_service.handle_excel_upload(
                _make_command(),
                file_input=_make_upload_file(
                    "malicious.xlsx",
                    b"<html>not excel</html>",
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                ),
            )
    record = next(r for r in caplog.records if r.event == "admin.upload.rejected")
    assert record.reason == "invalid_magic_bytes"


@pytest.mark.unit
def test_upload_service_returns_rejected_result_on_row_validation_failure(
    monkeypatch: MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    df = pd.DataFrame(
        {
            "소재지(지번)": [""],
            "(공부상)지목": ["답"],
            "(공부상)면적(㎡)": [12.5],
            "행정재산": ["Y"],
            "일반재산": ["N"],
            "담당자연락처": ["010"],
        }
    )
    monkeypatch.setattr(pd, "ExcelFile", lambda *_args, **_kwargs: DummyExcelFile(sheet_names=["목록"]))
    monkeypatch.setattr(pd, "read_excel", lambda *_args, **_kwargs: df)

    with caplog.at_level(logging.WARNING, logger="app.services.upload_service"):
        result = upload_service.handle_excel_upload(
            _make_command(),
            file_input=_make_upload_file(
                "upload.xlsx",
                b"PK\x03\x04dummy",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            ),
        )

    assert isinstance(result, upload_service.UploadRejectedResult)
    assert result.status_code == 400
    assert result.payload == {
        "success": False,
        "message": "데이터 검증 실패",
        "failed": 1,
        "errors": [{"row": 1, "field": "address", "code": "missing", "value": ""}],
    }
    rejected_record = next(record for record in caplog.records if record.event == "admin.upload.rejected")
    assert rejected_record.reason == "row_validation_failed"
    assert rejected_record.failed_rows == 1


@pytest.mark.unit
def test_upload_service_returns_rejected_result_when_processing_crashes(
    monkeypatch: MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    monkeypatch.setattr(pd, "ExcelFile", lambda *_args, **_kwargs: DummyExcelFile(sheet_names=["목록"]))
    monkeypatch.setattr(pd, "read_excel", lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("boom")))

    with caplog.at_level(logging.ERROR, logger="app.services.upload_service"):
        result = upload_service.handle_excel_upload(
            _make_command(),
            file_input=_make_upload_file(
                "upload.xlsx",
                b"PK\x03\x04dummy",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            ),
        )

    assert isinstance(result, upload_service.UploadRejectedResult)
    assert result.status_code == 500
    assert result.payload == {"success": False, "message": "업로드 처리 중 오류가 발생했습니다."}
    failure_record = next(record for record in caplog.records if record.event == "admin.upload.failed")
    assert failure_record.upload_filename == "upload.xlsx"
    assert failure_record.reason == "unexpected_exception"


def test_upload_service_rejects_invalid_csrf() -> None:
    with pytest.raises(AuthError) as exc:
        upload_service.handle_excel_upload(
            _make_command(csrf_valid=False),
            file_input=_make_upload_file(
                "upload.xlsx",
                b"PK\x03\x04dummy",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            ),
        )
    assert exc.value.status_code == 403
