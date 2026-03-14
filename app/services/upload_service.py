import logging
import os
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
    config = request.app.state.config
    request_id = getattr(request.state, "request_id", "-")
    actor = request.session.get("user", "anonymous")
    client_ip = request.client.host if request.client else "unknown"
    requested_sheet = config.UPLOAD_SHEET_NAME

    if not validate_csrf_token(request, csrf_token):
        raise HTTPException(status_code=403, detail="CSRF 토큰 검증에 실패했습니다.")

    original_filename = (file.filename or "").strip()
    filename = original_filename.lower()
    content_type = (file.content_type or "").lower()
    if not filename.endswith((".xlsx", ".xls")):
        _log_upload_audit(
            level=logging.WARNING,
            message="upload rejected: invalid extension",
            request_id=request_id,
            actor=actor,
            client_ip=client_ip,
            status=400,
            event="admin.upload.rejected",
            filename=original_filename or filename,
            content_type=content_type,
            file_size_bytes=None,
            requested_sheet=requested_sheet,
            reason="invalid_extension",
        )
        raise HTTPException(status_code=400, detail="엑셀 파일(.xlsx, .xls)만 업로드 가능합니다.")

    file.file.seek(0, os.SEEK_END)
    file_size = file.file.tell()
    file.file.seek(0)
    max_size_bytes = int(config.MAX_UPLOAD_SIZE_MB) * 1024 * 1024
    if file_size > max_size_bytes:
        _log_upload_audit(
            level=logging.WARNING,
            message="upload rejected: file too large",
            request_id=request_id,
            actor=actor,
            client_ip=client_ip,
            status=400,
            event="admin.upload.rejected",
            filename=original_filename or filename,
            content_type=content_type,
            file_size_bytes=file_size,
            requested_sheet=requested_sheet,
            reason="file_too_large",
        )
        raise HTTPException(
            status_code=400,
            detail=f"파일 용량 제한({config.MAX_UPLOAD_SIZE_MB}MB)을 초과했습니다.",
        )

    allowed_content_types = {
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "application/vnd.ms-excel",
        "application/octet-stream",
    }
    if content_type and content_type not in allowed_content_types:
        _log_upload_audit(
            level=logging.WARNING,
            message="upload rejected: unsupported content type",
            request_id=request_id,
            actor=actor,
            client_ip=client_ip,
            status=400,
            event="admin.upload.rejected",
            filename=original_filename or filename,
            content_type=content_type,
            file_size_bytes=file_size,
            requested_sheet=requested_sheet,
            reason="unsupported_content_type",
        )
        raise HTTPException(status_code=400, detail="지원하지 않는 파일 형식입니다.")

    try:
        _log_upload_audit(
            level=logging.INFO,
            message="upload started",
            request_id=request_id,
            actor=actor,
            client_ip=client_ip,
            status=202,
            event="admin.upload.started",
            filename=original_filename or filename,
            content_type=content_type,
            file_size_bytes=file_size,
            requested_sheet=requested_sheet,
        )
        excel_engine: Literal["xlrd", "openpyxl"] = "xlrd" if filename.endswith(".xls") else "openpyxl"
        excel_book = pd.ExcelFile(file.file, engine=excel_engine)
        if requested_sheet in excel_book.sheet_names:
            df = pd.read_excel(excel_book, sheet_name=requested_sheet)
        else:
            df = pd.read_excel(excel_book, sheet_name=excel_book.sheet_names[0])

        missing = land_validators.validate_required_columns(df)
        if missing:
            _log_upload_audit(
                level=logging.WARNING,
                message="upload rejected: required columns missing",
                request_id=request_id,
                actor=actor,
                client_ip=client_ip,
                status=400,
                event="admin.upload.rejected",
                filename=original_filename or filename,
                content_type=content_type,
                file_size_bytes=file_size,
                requested_sheet=requested_sheet,
                reason="missing_required_columns",
                row_count=len(df),
            )
            raise HTTPException(status_code=400, detail=f"필수 컬럼 누락: {', '.join(missing)}")

        if len(df) > int(config.MAX_UPLOAD_ROWS):
            _log_upload_audit(
                level=logging.WARNING,
                message="upload rejected: row count exceeded",
                request_id=request_id,
                actor=actor,
                client_ip=client_ip,
                status=400,
                event="admin.upload.rejected",
                filename=original_filename or filename,
                content_type=content_type,
                file_size_bytes=file_size,
                requested_sheet=requested_sheet,
                reason="row_count_exceeded",
                row_count=len(df),
            )
            raise HTTPException(
                status_code=400,
                detail=f"최대 업로드 행 수({config.MAX_UPLOAD_ROWS})를 초과했습니다.",
            )

        normalized_rows, errors, total_errors = land_validators.normalize_upload_rows(df)
        if total_errors:
            _log_upload_audit(
                level=logging.WARNING,
                message="upload rejected: row validation failed",
                request_id=request_id,
                actor=actor,
                client_ip=client_ip,
                status=400,
                event="admin.upload.rejected",
                filename=original_filename or filename,
                content_type=content_type,
                file_size_bytes=file_size,
                requested_sheet=requested_sheet,
                reason="row_validation_failed",
                row_count=len(df),
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

        with db_connection() as conn:
            poi_repository.delete_all(conn)

            for row in normalized_rows:
                poi_repository.insert_land(
                    conn,
                    address=row["address"],
                    land_type=row["land_type"],
                    area=row["area"],
                    adm_property=row["adm_property"],
                    gen_property=row["gen_property"],
                    contact=row["contact"],
                )

            conn.commit()

        job_id = enqueue_geom_update_job()
        background_tasks.add_task(run_geom_update_job, job_id, 5)

        _log_upload_audit(
            level=logging.INFO,
            message="upload accepted",
            request_id=request_id,
            actor=actor,
            client_ip=client_ip,
            status=200,
            event="admin.upload.succeeded",
            filename=original_filename or filename,
            content_type=content_type,
            file_size_bytes=file_size,
            requested_sheet=requested_sheet,
            row_count=len(df),
            geom_job_id=job_id,
        )
        return {
            "success": True,
            "total": len(df),
            "message": "엑셀 데이터 입력 완료",
            "geomJobId": job_id,
        }

    except HTTPException:
        raise
    except Exception:
        logger.exception(
            "upload processing failed",
            extra={
                "request_id": request_id,
                "event": "admin.upload.failed",
                "actor": actor,
                "ip": client_ip,
                "status": 500,
                "upload_filename": original_filename or filename,
                "content_type": content_type,
                "file_size_bytes": file_size,
                "requested_sheet": requested_sheet,
                "reason": "unexpected_exception",
            },
        )
        return JSONResponse(
            status_code=500,
            content={"success": False, "message": "업로드 처리 중 오류가 발생했습니다."},
        )
