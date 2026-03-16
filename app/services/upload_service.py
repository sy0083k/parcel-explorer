import logging
import os
from dataclasses import dataclass
from typing import Literal

import pandas as pd
from fastapi import BackgroundTasks, HTTPException, Request, UploadFile
from fastapi.responses import JSONResponse

from app.db.connection import db_connection
from app.dependencies import validate_csrf_token
from app.logging_utils import RequestIdFilter
from app.repositories import poi_repository
from app.services.geo_service import enqueue_geom_update_job, run_geom_update_job
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


def handle_excel_upload(
    request: Request,
    background_tasks: BackgroundTasks,
    csrf_token: str,
    file: UploadFile,
) -> JSONResponse | dict:
    context = _build_upload_context(request, file)
    file_meta: UploadFileMeta | None = None
    try:
        file_meta = _validate_upload_request(request, csrf_token, file, context)
        dataframe_result = _load_upload_dataframe(file, context, file_meta)
        validated_rows = _validate_upload_dataframe(dataframe_result.dataframe, context, file_meta)
        if isinstance(validated_rows, JSONResponse):
            return validated_rows

        _replace_land_data(validated_rows.normalized_rows)
        return _finalize_upload(background_tasks, context, file_meta, validated_rows.row_count)
    except HTTPException:
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
        return JSONResponse(
            status_code=500,
            content={"success": False, "message": "업로드 처리 중 오류가 발생했습니다."},
        )


def _build_upload_context(request: Request, file: UploadFile) -> UploadContext:
    config = request.app.state.config
    original_filename = (file.filename or "").strip()
    return UploadContext(
        request_id=getattr(request.state, "request_id", "-"),
        actor=request.session.get("user", "anonymous"),
        client_ip=request.client.host if request.client else "unknown",
        requested_sheet=config.UPLOAD_SHEET_NAME,
        max_upload_size_mb=int(config.MAX_UPLOAD_SIZE_MB),
        max_upload_rows=int(config.MAX_UPLOAD_ROWS),
        original_filename=original_filename,
        filename=original_filename.lower(),
        content_type=(file.content_type or "").lower(),
    )


def _validate_upload_request(
    request: Request,
    csrf_token: str,
    file: UploadFile,
    context: UploadContext,
) -> UploadFileMeta:
    if not validate_csrf_token(request, csrf_token):
        raise HTTPException(status_code=403, detail="CSRF 토큰 검증에 실패했습니다.")

    if not context.filename.endswith((".xlsx", ".xls")):
        _log_upload_rejection(context, reason="invalid_extension", detail="엑셀 파일(.xlsx, .xls)만 업로드 가능합니다.")
        raise HTTPException(status_code=400, detail="엑셀 파일(.xlsx, .xls)만 업로드 가능합니다.")

    file.file.seek(0, os.SEEK_END)
    file_size = file.file.tell()
    file.file.seek(0)

    max_size_bytes = context.max_upload_size_mb * 1024 * 1024
    if file_size > max_size_bytes:
        _log_upload_rejection(
            context,
            reason="file_too_large",
            detail=f"파일 용량 제한({context.max_upload_size_mb}MB)을 초과했습니다.",
            file_size_bytes=file_size,
        )
        raise HTTPException(
            status_code=400,
            detail=f"파일 용량 제한({context.max_upload_size_mb}MB)을 초과했습니다.",
        )

    header = file.file.read(8)
    file.file.seek(0)
    if not land_validators.check_excel_magic_bytes(header, context.filename):
        _log_upload_rejection(
            context,
            reason="invalid_magic_bytes",
            detail="파일 형식이 선언된 확장자와 일치하지 않습니다.",
            file_size_bytes=file_size,
        )
        raise HTTPException(status_code=400, detail="파일 형식이 선언된 확장자와 일치하지 않습니다.")

    if context.content_type and context.content_type not in ALLOWED_CONTENT_TYPES:
        _log_upload_rejection(
            context,
            reason="unsupported_content_type",
            detail="지원하지 않는 파일 형식입니다.",
            file_size_bytes=file_size,
        )
        raise HTTPException(status_code=400, detail="지원하지 않는 파일 형식입니다.")

    excel_engine: Literal["xlrd", "openpyxl"] = "xlrd" if context.filename.endswith(".xls") else "openpyxl"
    return UploadFileMeta(file_size_bytes=file_size, excel_engine=excel_engine)


def _load_upload_dataframe(
    file: UploadFile,
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
    excel_book = pd.ExcelFile(file.file, engine=file_meta.excel_engine)
    selected_sheet = context.requested_sheet
    if context.requested_sheet in excel_book.sheet_names:
        dataframe = pd.read_excel(excel_book, sheet_name=context.requested_sheet)
    else:
        selected_sheet = excel_book.sheet_names[0]
        dataframe = pd.read_excel(excel_book, sheet_name=selected_sheet)
    return UploadDataFrameResult(dataframe=dataframe, selected_sheet=selected_sheet)


def _validate_upload_dataframe(
    df: pd.DataFrame,
    context: UploadContext,
    file_meta: UploadFileMeta,
) -> UploadValidatedRows | JSONResponse:
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
        raise HTTPException(status_code=400, detail=f"필수 컬럼 누락: {', '.join(missing)}")

    if row_count > context.max_upload_rows:
        _log_upload_rejection(
            context,
            reason="row_count_exceeded",
            detail=f"최대 업로드 행 수({context.max_upload_rows})를 초과했습니다.",
            file_size_bytes=file_meta.file_size_bytes,
            row_count=row_count,
        )
        raise HTTPException(
            status_code=400,
            detail=f"최대 업로드 행 수({context.max_upload_rows})를 초과했습니다.",
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
        return JSONResponse(
            status_code=400,
            content={
                "success": False,
                "message": "데이터 검증 실패",
                "failed": total_errors,
                "errors": errors,
            },
        )

    return UploadValidatedRows(normalized_rows=normalized_rows, row_count=row_count)


def _replace_land_data(rows: list[dict[str, object]]) -> None:
    with db_connection() as conn:
        poi_repository.delete_all(conn)
        for row in rows:
            poi_repository.insert_land(
                conn,
                address=str(row["address"]),
                land_type=str(row["land_type"]),
                area=float(row["area"]),
                adm_property=str(row["adm_property"]),
                gen_property=str(row["gen_property"]),
                contact=str(row["contact"]),
            )
        conn.commit()


def _finalize_upload(
    background_tasks: BackgroundTasks,
    context: UploadContext,
    file_meta: UploadFileMeta,
    row_count: int,
) -> dict[str, object]:
    job_id = enqueue_geom_update_job()
    background_tasks.add_task(run_geom_update_job, job_id, 5)
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
    return {
        "success": True,
        "total": row_count,
        "message": "엑셀 데이터 입력 완료",
        "geomJobId": job_id,
    }


def _log_upload_rejection(
    context: UploadContext,
    *,
    reason: str,
    detail: str,
    file_size_bytes: int | None = None,
    row_count: int | None = None,
    failed_rows: int | None = None,
) -> None:
    rejection_messages = {
        "invalid_extension": "upload rejected: invalid extension",
        "file_too_large": "upload rejected: file too large",
        "invalid_magic_bytes": "upload rejected: magic bytes mismatch",
        "unsupported_content_type": "upload rejected: unsupported content type",
        "missing_required_columns": "upload rejected: required columns missing",
        "row_count_exceeded": "upload rejected: row count exceeded",
        "row_validation_failed": "upload rejected: row validation failed",
    }
    _log_upload_audit(
        level=logging.WARNING,
        message=rejection_messages[reason],
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
