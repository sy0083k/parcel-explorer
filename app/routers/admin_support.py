from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from fastapi import HTTPException, Request, UploadFile
from fastapi.responses import Response

from app.dependencies import validate_csrf_token
from app.services import public_download_service, raw_query_export_service
from app.services.service_errors import ServiceError
from app.services.service_models import RequestContext, UploadedFileInput


def build_request_context(request: Request, *, csrf_token: str = "") -> RequestContext:
    return RequestContext(
        request_id=getattr(request.state, "request_id", "-"),
        actor=request.session.get("user", "anonymous"),
        client_ip=request.client.host if request.client else "unknown",
        csrf_valid=validate_csrf_token(request, csrf_token),
    )


def build_request_log_context(request: Request) -> dict[str, object]:
    return {
        "request_id": getattr(request.state, "request_id", "-"),
        "actor": request.session.get("user", "anonymous"),
        "ip": request.client.host if request.client else "unknown",
    }


def raise_http_exception(exc: ServiceError) -> None:
    raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc


def build_uploaded_file_input(file: UploadFile) -> UploadedFileInput:
    return UploadedFileInput(
        filename=file.filename or "",
        content_type=file.content_type or "",
        file=file.file,
    )


def build_public_download_config(runtime_config: Any) -> public_download_service.PublicDownloadConfig:
    return public_download_service.PublicDownloadConfig(
        base_dir=runtime_config.BASE_DIR,
        public_download_dir=runtime_config.PUBLIC_DOWNLOAD_DIR,
        allowed_exts=tuple(runtime_config.PUBLIC_DOWNLOAD_ALLOWED_EXTS),
        max_size_mb=int(runtime_config.PUBLIC_DOWNLOAD_MAX_SIZE_MB),
    )


def build_raw_query_export_filename(now: datetime | None = None) -> str:
    current = now or datetime.now()
    return f"raw-queries-{current.strftime('%Y%m%d')}.csv"


def build_raw_query_export_log_context(
    request: Request,
    *,
    event_type: str,
    date_from: str | None,
    date_to: str | None,
    limit: int,
    filename: str,
) -> dict[str, object]:
    return {
        **build_request_log_context(request),
        "event_type_filter": event_type,
        "date_from": date_from or "-",
        "date_to": date_to or "-",
        "requested_limit": limit,
        "export_filename": filename,
    }


def log_raw_query_export_rejected(
    logger: logging.Logger,
    *,
    request: Request,
    event_type: str,
    date_from: str | None,
    date_to: str | None,
    limit: int,
    filename: str,
    exc: ServiceError,
) -> None:
    logger.warning(
        "raw query export rejected",
        extra={
            **build_raw_query_export_log_context(
                request,
                event_type=event_type,
                date_from=date_from,
                date_to=date_to,
                limit=limit,
                filename=filename,
            ),
            "event": "admin.raw_queries_export.rejected",
            "status": exc.status_code,
            "effective_limit": "-",
            "exported_row_count": "-",
            "reason": exc.message or "invalid_request",
        },
    )


def log_raw_query_export_failed(
    logger: logging.Logger,
    *,
    request: Request,
    event_type: str,
    date_from: str | None,
    date_to: str | None,
    limit: int,
    filename: str,
) -> None:
    logger.exception(
        "raw query export failed",
        extra={
            **build_raw_query_export_log_context(
                request,
                event_type=event_type,
                date_from=date_from,
                date_to=date_to,
                limit=limit,
                filename=filename,
            ),
            "event": "admin.raw_queries_export.failed",
            "status": 500,
            "effective_limit": "-",
            "exported_row_count": "-",
            "reason": "unexpected_exception",
        },
    )


def log_raw_query_export_succeeded(
    logger: logging.Logger,
    *,
    request: Request,
    event_type: str,
    date_from: str | None,
    date_to: str | None,
    limit: int,
    filename: str,
    effective_limit: int,
    row_count: int,
) -> None:
    logger.info(
        "raw query export succeeded",
        extra={
            **build_raw_query_export_log_context(
                request,
                event_type=event_type,
                date_from=date_from,
                date_to=date_to,
                limit=limit,
                filename=filename,
            ),
            "event": "admin.raw_queries_export.succeeded",
            "status": 200,
            "effective_limit": effective_limit,
            "exported_row_count": row_count,
        },
    )


def build_raw_query_export_response(
    result: raw_query_export_service.RawQueryCsvExportResult,
    filename: str,
) -> Response:
    headers = {"Content-Disposition": f'attachment; filename="{filename}"'}
    return Response(content=result.csv_text, media_type="text/csv; charset=utf-8", headers=headers)
