import logging
from fastapi import Request
from fastapi.responses import JSONResponse

from app.logging_utils import RequestIdFilter

logger = logging.getLogger(__name__)
logger.addFilter(RequestIdFilter())


async def http_exception_handler(request: Request, exc):
    request_id = getattr(request.state, "request_id", "-")
    logger.warning(
        "http error: status=%s detail=%s path=%s",
        getattr(exc, "status_code", "-"),
        getattr(exc, "detail", ""),
        request.url.path,
        extra={"request_id": request_id},
    )
    return JSONResponse(
        status_code=getattr(exc, "status_code", 500),
        content={"detail": getattr(exc, "detail", "오류가 발생했습니다."), "request_id": request_id},
    )


async def unhandled_exception_handler(request: Request, exc: Exception):
    request_id = getattr(request.state, "request_id", "-")
    logger.exception(
        "unhandled error on path=%s",
        request.url.path,
        extra={"request_id": request_id},
    )
    return JSONResponse(
        status_code=500,
        content={"detail": "서버 내부 오류가 발생했습니다.", "request_id": request_id},
    )
