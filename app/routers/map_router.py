from typing import Any

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse

from app.services import land_service, public_download_service, stats_service

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
        key = _rate_limit_key(request, payload)
        allowed, retry_after = request.app.state.event_rate_limiter.allow(
            key=f"events:{key}",
            limit=EVENT_LIMIT_PER_MINUTE,
            window_seconds=RATE_LIMIT_WINDOW_SECONDS,
        )
        if not allowed:
            return _rate_limited_response(retry_after)
        stats_service.record_map_event(payload)
        return {"success": True}

    @router.post("/web-events")
    async def post_web_event(request: Request, payload: dict[str, Any]):
        key = _rate_limit_key(request, payload)
        allowed, retry_after = request.app.state.event_rate_limiter.allow(
            key=f"web-events:{key}",
            limit=WEB_EVENT_LIMIT_PER_MINUTE,
            window_seconds=RATE_LIMIT_WINDOW_SECONDS,
        )
        if not allowed:
            return _rate_limited_response(retry_after)
        stats_service.record_web_visit_event(payload, request)
        return {"success": True}

    @router.get("/public-download")
    async def get_public_download(request: Request):
        allowed, retry_after = request.app.state.event_rate_limiter.allow(
            key=f"public-download:{_client_ip(request)}",
            limit=int(request.app.state.config.PUBLIC_DOWNLOAD_RATE_LIMIT_PER_MINUTE),
            window_seconds=RATE_LIMIT_WINDOW_SECONDS,
        )
        if not allowed:
            return _rate_limited_response(retry_after)
        return public_download_service.get_public_download_file_response(request)

    return router


router = create_router()
