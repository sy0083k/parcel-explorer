import logging
import os
from dataclasses import dataclass
from typing import Literal, cast

import pandas as pd

from app.db.connection import db_connection
from app.logging_utils import RequestIdFilter
from app.repositories import land_repository
from app.services import geo_service
from app.services.service_errors import AuthError, ValidationError
from app.services.service_models import RequestContext, UploadedFileInput
from app.validators import land_validators

logger = logging.getLogger(__name__)
logger.addFilter(RequestIdFilter())

ALLOWED_CONTENT_TYPES = {
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/vnd.ms-excel",
    "application/octet-stream",
}


@dataclass(frozen=True)
class UploadContext:
    request_id: str
    actor: str
    client_ip: str
    requested_sheet: str
    max_upload_size_mb: int
    max_upload_rows: int
    original_filename: str
    filename: str
    content_type: str


@dataclass(frozen=True)
class UploadCommand:
    context: RequestContext
    requested_sheet: str
    max_upload_size_mb: int
    max_upload_rows: int


@dataclass(frozen=True)
class UploadFileMeta:
    file_size_bytes: int
    excel_engine: Literal["xlrd", "openpyxl"]


@dataclass(frozen=True)
class UploadDataFrameResult:
    dataframe: pd.DataFrame
    selected_sheet: str


@dataclass(frozen=True)
class UploadValidatedRows:
    normalized_rows: list[dict[str, object]]
    row_count: int


@dataclass(frozen=True)
class UploadRejectedResult:
    status_code: int
    payload: dict[str, object]


@dataclass(frozen=True)
class UploadSuccessResult:
    payload: dict[str, object]
    should_schedule_geom_job: bool
    geom_job_id: int


def build_upload_context(command: UploadCommand, file_input: UploadedFileInput) -> UploadContext:
    original_filename = file_input.filename.strip()
    return UploadContext(
        request_id=command.context.request_id,
        actor=command.context.actor,
        client_ip=command.context.client_ip,
        requested_sheet=command.requested_sheet,
        max_upload_size_mb=command.max_upload_size_mb,
        max_upload_rows=command.max_upload_rows,
        original_filename=original_filename,
        filename=original_filename.lower(),
        content_type=file_input.content_type.lower(),
    )


def handle_excel_upload(
    command: UploadCommand,
    *,
    file_input: UploadedFileInput,
) -> UploadSuccessResult | UploadRejectedResult:
    context = build_upload_context(command, file_input)
    file_meta: UploadFileMeta | None = None
    try:
        file_meta = _validate_upload_request(command, file_input, context)
        dataframe_result = _load_upload_dataframe(file_input, context, file_meta)
        validated_rows = _validate_upload_dataframe(dataframe_result.dataframe, context, file_meta)
        if isinstance(validated_rows, UploadRejectedResult):
            return validated_rows
        _replace_land_data(validated_rows.normalized_rows)
        return _finalize_upload(context, file_meta, validated_rows.row_count)
    except (AuthError, ValidationError):
        raise
    except Exception:
        logger.exception(
            "upload processing failed",
            extra={
                "request_id": context.request_id,
                "event": "admin.upload.failed",
                "actor": context.actor,
                "ip": context.client_ip,
                "status": 500,
                "upload_filename": context.original_filename or context.filename,
                "content_type": context.content_type,
                "file_size_bytes": file_meta.file_size_bytes if file_meta is not None else "-",
                "requested_sheet": context.requested_sheet,
                "reason": "unexpected_exception",
            },
        )
        return UploadRejectedResult(
            status_code=500,
            payload={"success": False, "message": "업로드 처리 중 오류가 발생했습니다."},
        )


def _log_upload_audit(
    *,
    level: int,
    message: str,
    request_id: str,
    actor: str,
    client_ip: str,
    status: int,
    event: str,
    filename: str,
    content_type: str,
    file_size_bytes: int | None,
    requested_sheet: str,
    reason: str | None = None,
    row_count: int | None = None,
    failed_rows: int | None = None,
    geom_job_id: int | None = None,
) -> None:
    extra = {
        "request_id": request_id,
        "event": event,
        "actor": actor,
        "ip": client_ip,
        "status": status,
        "upload_filename": filename,
        "content_type": content_type,
        "file_size_bytes": file_size_bytes if file_size_bytes is not None else "-",
        "requested_sheet": requested_sheet,
        "reason": reason or "-",
        "row_count": row_count if row_count is not None else "-",
        "failed_rows": failed_rows if failed_rows is not None else "-",
        "geom_job_id": geom_job_id if geom_job_id is not None else "-",
    }
    logger.log(level, message, extra=extra)


def _validate_upload_request(
    command: UploadCommand,
    file_input: UploadedFileInput,
    context: UploadContext,
) -> UploadFileMeta:
    if not command.context.csrf_valid:
        raise AuthError(status_code=403, message="CSRF 토큰 검증에 실패했습니다.")

    if not context.filename.endswith((".xlsx", ".xls")):
        _log_upload_rejection(context, reason="invalid_extension", detail="엑셀 파일(.xlsx, .xls)만 업로드 가능합니다.")
        raise ValidationError(status_code=400, message="엑셀 파일(.xlsx, .xls)만 업로드 가능합니다.")

    file_input.file.seek(0, os.SEEK_END)
    file_size = file_input.file.tell()
    file_input.file.seek(0)

    max_size_bytes = context.max_upload_size_mb * 1024 * 1024
    if file_size > max_size_bytes:
        _log_upload_rejection(
            context,
            reason="file_too_large",
            detail=f"파일 용량 제한({context.max_upload_size_mb}MB)을 초과했습니다.",
            file_size_bytes=file_size,
        )
        raise ValidationError(
            status_code=400,
            message=f"파일 용량 제한({context.max_upload_size_mb}MB)을 초과했습니다.",
        )

    header = file_input.file.read(8)
    file_input.file.seek(0)
    if not land_validators.check_excel_magic_bytes(header, context.filename):
        _log_upload_rejection(
            context,
            reason="invalid_magic_bytes",
            detail="파일 형식이 선언된 확장자와 일치하지 않습니다.",
            file_size_bytes=file_size,
        )
        raise ValidationError(status_code=400, message="파일 형식이 선언된 확장자와 일치하지 않습니다.")

    if context.content_type and context.content_type not in ALLOWED_CONTENT_TYPES:
        _log_upload_rejection(
            context,
            reason="unsupported_content_type",
            detail="지원하지 않는 파일 형식입니다.",
            file_size_bytes=file_size,
        )
        raise ValidationError(status_code=400, message="지원하지 않는 파일 형식입니다.")

    excel_engine: Literal["xlrd", "openpyxl"] = "xlrd" if context.filename.endswith(".xls") else "openpyxl"
    return UploadFileMeta(file_size_bytes=file_size, excel_engine=excel_engine)


def _load_upload_dataframe(
    file_input: UploadedFileInput,
    context: UploadContext,
    file_meta: UploadFileMeta,
) -> UploadDataFrameResult:
    _log_upload_audit(
        level=logging.INFO,
        message="upload started",
        request_id=context.request_id,
        actor=context.actor,
        client_ip=context.client_ip,
        status=202,
        event="admin.upload.started",
        filename=context.original_filename or context.filename,
        content_type=context.content_type,
        file_size_bytes=file_meta.file_size_bytes,
        requested_sheet=context.requested_sheet,
    )
    excel_book = pd.ExcelFile(file_input.file, engine=file_meta.excel_engine)
    selected_sheet = context.requested_sheet
    if context.requested_sheet in excel_book.sheet_names:
        dataframe = pd.read_excel(excel_book, sheet_name=context.requested_sheet)
    else:
        selected_sheet = cast(str, excel_book.sheet_names[0])
        dataframe = pd.read_excel(excel_book, sheet_name=selected_sheet)
    return UploadDataFrameResult(dataframe=dataframe, selected_sheet=selected_sheet)


def _validate_upload_dataframe(
    df: pd.DataFrame,
    context: UploadContext,
    file_meta: UploadFileMeta,
) -> UploadValidatedRows | UploadRejectedResult:
    row_count = len(df)
    missing = land_validators.validate_required_columns(df)
    if missing:
        _log_upload_rejection(
            context,
            reason="missing_required_columns",
            detail=f"필수 컬럼 누락: {', '.join(missing)}",
            file_size_bytes=file_meta.file_size_bytes,
            row_count=row_count,
        )
        raise ValidationError(status_code=400, message=f"필수 컬럼 누락: {', '.join(missing)}")

    if row_count > context.max_upload_rows:
        _log_upload_rejection(
            context,
            reason="row_count_exceeded",
            detail=f"최대 업로드 행 수({context.max_upload_rows})를 초과했습니다.",
            file_size_bytes=file_meta.file_size_bytes,
            row_count=row_count,
        )
        raise ValidationError(
            status_code=400,
            message=f"최대 업로드 행 수({context.max_upload_rows})를 초과했습니다.",
        )

    normalized_rows, errors, total_errors = land_validators.normalize_upload_rows(df)
    if total_errors:
        _log_upload_rejection(
            context,
            reason="row_validation_failed",
            detail="데이터 검증 실패",
            file_size_bytes=file_meta.file_size_bytes,
            row_count=row_count,
            failed_rows=total_errors,
        )
        return UploadRejectedResult(
            status_code=400,
            payload={
                "success": False,
                "message": "데이터 검증 실패",
                "failed": total_errors,
                "errors": errors,
            },
        )

    return UploadValidatedRows(normalized_rows=normalized_rows, row_count=row_count)


def _replace_land_data(rows: list[dict[str, object]]) -> None:
    with db_connection() as conn:
        land_repository.delete_all(conn)
        for row in rows:
            land_repository.insert_land(
                conn,
                address=str(row["address"]),
                land_type=str(row["land_type"]),
                area=float(str(row["area"])),
                adm_property=str(row["adm_property"]),
                gen_property=str(row["gen_property"]),
                contact=str(row["contact"]),
            )
        conn.commit()


def _finalize_upload(
    context: UploadContext,
    file_meta: UploadFileMeta,
    row_count: int,
) -> UploadSuccessResult:
    job_id = geo_service.enqueue_geom_update_job()
    _log_upload_audit(
        level=logging.INFO,
        message="upload accepted",
        request_id=context.request_id,
        actor=context.actor,
        client_ip=context.client_ip,
        status=200,
        event="admin.upload.succeeded",
        filename=context.original_filename or context.filename,
        content_type=context.content_type,
        file_size_bytes=file_meta.file_size_bytes,
        requested_sheet=context.requested_sheet,
        row_count=row_count,
        geom_job_id=job_id,
    )
    return UploadSuccessResult(
        payload={
            "success": True,
            "rows": row_count,
            "message": "업로드 완료. 경계선 수집 작업을 시작합니다.",
            "geomJobId": job_id,
        },
        should_schedule_geom_job=True,
        geom_job_id=job_id,
    )


def _log_upload_rejection(
    context: UploadContext,
    *,
    reason: str,
    detail: str,
    file_size_bytes: int | None = None,
    row_count: int | None = None,
    failed_rows: int | None = None,
) -> None:
    _log_upload_audit(
        level=logging.WARNING,
        message="upload rejected",
        request_id=context.request_id,
        actor=context.actor,
        client_ip=context.client_ip,
        status=400,
        event="admin.upload.rejected",
        filename=context.original_filename or context.filename,
        content_type=context.content_type,
        file_size_bytes=file_size_bytes,
        requested_sheet=context.requested_sheet,
        reason=reason,
        row_count=row_count,
        failed_rows=failed_rows,
    )
