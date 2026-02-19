import logging
import os

import pandas as pd
from fastapi import BackgroundTasks, HTTPException, Request, UploadFile
from fastapi.responses import JSONResponse

from app.db.connection import db_connection
from app.dependencies import validate_csrf_token
from app.logging_utils import RequestIdFilter
from app.repositories import idle_land_repository
from app.services.geo_service import enqueue_geom_update_job, run_geom_update_job
from app.validators import land_validators

logger = logging.getLogger(__name__)
logger.addFilter(RequestIdFilter())


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

    if not validate_csrf_token(request, csrf_token):
        raise HTTPException(status_code=403, detail="CSRF 토큰 검증에 실패했습니다.")

    filename = (file.filename or "").lower()
    content_type = (file.content_type or "").lower()
    if not filename.endswith((".xlsx", ".xls")):
        logger.warning("upload rejected: invalid extension", extra={"request_id": request_id})
        raise HTTPException(status_code=400, detail="엑셀 파일(.xlsx, .xls)만 업로드 가능합니다.")

    file.file.seek(0, os.SEEK_END)
    file_size = file.file.tell()
    file.file.seek(0)
    max_size_bytes = int(config.MAX_UPLOAD_SIZE_MB) * 1024 * 1024
    if file_size > max_size_bytes:
        logger.warning("upload rejected: file too large (%s bytes)", file_size, extra={"request_id": request_id})
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
        raise HTTPException(status_code=400, detail="지원하지 않는 파일 형식입니다.")

    try:
        logger.info(
            "upload started",
            extra={
                "request_id": request_id,
                "event": "admin.upload.started",
                "actor": actor,
                "ip": client_ip,
                "status": 202,
            },
        )
        requested_sheet = config.UPLOAD_SHEET_NAME
        excel_engine = "xlrd" if filename.endswith(".xls") else "openpyxl"
        excel_book = pd.ExcelFile(file.file, engine=excel_engine)
        if requested_sheet in excel_book.sheet_names:
            df = pd.read_excel(excel_book, sheet_name=requested_sheet)
        else:
            df = pd.read_excel(excel_book, sheet_name=excel_book.sheet_names[0])

        missing = land_validators.validate_required_columns(df)
        if missing:
            logger.warning("upload rejected: required columns missing", extra={"request_id": request_id})
            raise HTTPException(status_code=400, detail=f"필수 컬럼 누락: {', '.join(missing)}")

        if len(df) > int(config.MAX_UPLOAD_ROWS):
            logger.warning("upload rejected: row count exceeded (%s)", len(df), extra={"request_id": request_id})
            raise HTTPException(
                status_code=400,
                detail=f"최대 업로드 행 수({config.MAX_UPLOAD_ROWS})를 초과했습니다.",
            )

        normalized_rows, errors, total_errors = land_validators.normalize_upload_rows(df)
        if total_errors:
            logger.warning("upload rejected: row validation failed", extra={"request_id": request_id})
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
            idle_land_repository.delete_all(conn)

            for row in normalized_rows:
                idle_land_repository.insert_land(
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

        logger.info(
            "upload accepted: %s rows",
            len(df),
            extra={
                "request_id": request_id,
                "event": "admin.upload.succeeded",
                "actor": actor,
                "ip": client_ip,
                "status": 200,
            },
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
            },
        )
        return JSONResponse(
            status_code=500,
            content={"success": False, "message": "업로드 처리 중 오류가 발생했습니다."},
        )
