from collections.abc import Callable
from typing import Any, NoReturn
from urllib.parse import quote

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse

from app.services import (
    land_service,
    map_event_service,
    public_download_service,
    web_stats_service,
)
from app.services.public_event_commands import (
    build_map_event_command,
    build_web_visit_event_command,
)
from app.services.service_errors import ServiceError
from app.services.service_models import WebVisitContext

DEFAULT_LANDS_PAGE_LIMIT = 500
MAX_LANDS_PAGE_LIMIT = 2000
EVENT_LIMIT_PER_MINUTE = 60
WEB_EVENT_LIMIT_PER_MINUTE = 120
RATE_LIMIT_WINDOW_SECONDS = 60


def _client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


def _parse_cursor(raw_cursor: str | None) -> int | None:
    if raw_cursor is None or raw_cursor.strip() == "":
        return None
    cursor = int(raw_cursor)
    if cursor < 0:
        raise ValueError("cursor must be >= 0")
    return cursor


def _rate_limit_key(request: Request, payload: dict[str, Any]) -> str:
    client_ip = _client_ip(request)
    anon_id = str(payload.get("anonId", "")).strip()
    if anon_id:
        return f"{client_ip}:{anon_id}"
    return client_ip


def _rate_limited_response(retry_after: int) -> JSONResponse:
    return JSONResponse(
        status_code=429,
        content={"success": False, "message": "요청이 너무 많습니다. 잠시 후 다시 시도해주세요."},
        headers={"Retry-After": str(retry_after)},
    )


def _success_response() -> dict[str, bool]:
    return {"success": True}


def _raise_http_from_service_error(exc: ServiceError) -> NoReturn:
    raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc


def _allow_rate_limited_event(
    request: Request,
    *,
    payload: dict[str, Any],
    prefix: str,
    limit: int,
) -> JSONResponse | None:
    key = _rate_limit_key(request, payload)
    allowed, retry_after = request.app.state.event_rate_limiter.allow(
        key=f"{prefix}:{key}",
        limit=limit,
        window_seconds=RATE_LIMIT_WINDOW_SECONDS,
    )
    if allowed:
        return None
    return _rate_limited_response(retry_after)


def _build_web_visit_context(request: Request) -> WebVisitContext:
    return WebVisitContext(
        user_agent=request.headers.get("user-agent"),
        allowed_web_track_paths=tuple(str(path) for path in request.app.state.config.ALLOWED_WEB_TRACK_PATHS),
    )


def _handle_rate_limited_event(
    request: Request,
    *,
    payload: dict[str, Any],
    prefix: str,
    limit: int,
    on_allowed: Callable[[], None],
) -> JSONResponse | dict[str, bool]:
    blocked = _allow_rate_limited_event(
        request,
        payload=payload,
        prefix=prefix,
        limit=limit,
    )
    if blocked is not None:
        return blocked
    try:
        on_allowed()
    except ServiceError as exc:
        _raise_http_from_service_error(exc)
    return _success_response()


def create_router() -> APIRouter:
    router = APIRouter()

    @router.get("/config")
    async def get_config(request: Request) -> dict[str, Any]:
        config = request.app.state.config
        return {
            "vworldKey": config.VWORLD_WMTS_KEY,
            "center": [config.CENTER_LON, config.CENTER_LAT],
            "zoom": config.DEFAULT_ZOOM,
        }

    @router.get("/lands")
    async def get_lands(
        limit: int = DEFAULT_LANDS_PAGE_LIMIT,
        cursor: str | None = None,
    ) -> dict[str, Any]:
        clamped_limit = max(1, min(limit, MAX_LANDS_PAGE_LIMIT))
        try:
            parsed_cursor = _parse_cursor(cursor)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return land_service.get_public_land_features_page(cursor=parsed_cursor, limit=clamped_limit)

    @router.post("/events")
    async def post_map_event(request: Request, payload: dict[str, Any]):
        return _handle_rate_limited_event(
            request,
            payload=payload,
            prefix="events",
            limit=EVENT_LIMIT_PER_MINUTE,
            on_allowed=lambda: map_event_service.record_map_event(build_map_event_command(payload)),
        )

    @router.post("/web-events")
    async def post_web_event(request: Request, payload: dict[str, Any]):
        context = _build_web_visit_context(request)
        return _handle_rate_limited_event(
            request,
            payload=payload,
            prefix="web-events",
            limit=WEB_EVENT_LIMIT_PER_MINUTE,
            on_allowed=lambda: web_stats_service.record_web_visit_event(
                build_web_visit_event_command(payload, context=context)
            ),
        )

    @router.get("/public-download")
    async def get_public_download(request: Request):
        allowed, retry_after = request.app.state.event_rate_limiter.allow(
            key=f"public-download:{_client_ip(request)}",
            limit=int(request.app.state.config.PUBLIC_DOWNLOAD_RATE_LIMIT_PER_MINUTE),
            window_seconds=RATE_LIMIT_WINDOW_SECONDS,
        )
        if not allowed:
            return _rate_limited_response(retry_after)
        config = request.app.state.config
        try:
            result = public_download_service.get_public_download_file(
                public_download_service.PublicDownloadConfig(
                    base_dir=config.BASE_DIR,
                    public_download_dir=config.PUBLIC_DOWNLOAD_DIR,
                    allowed_exts=tuple(config.PUBLIC_DOWNLOAD_ALLOWED_EXTS),
                    max_size_mb=int(config.PUBLIC_DOWNLOAD_MAX_SIZE_MB),
                )
            )
        except ServiceError as exc:
            _raise_http_from_service_error(exc)
        quoted = quote(result.download_filename)
        return FileResponse(
            path=result.path,
            media_type=result.media_type,
            headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quoted}"},
        )

    return router


router = create_router()
