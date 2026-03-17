from typing import Any, NoReturn
from urllib.parse import quote

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse

from app.services import land_service, map_event_service, public_download_service, web_stats_service
from app.services.service_errors import ServiceError
from app.services.service_models import (
    LandClickMapEventCommand,
    MapEventCommand,
    RequestMetadata,
    SearchMapEventCommand,
    UnknownMapEventCommand,
    WebVisitEventCommand,
)

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


def _build_map_event_command(payload: dict[str, Any]) -> MapEventCommand:
    event_type = str(payload.get("eventType", "")).strip()
    if event_type == map_event_service.EVENT_TYPE_SEARCH:
        return SearchMapEventCommand(
            anon_id=payload.get("anonId"),
            min_area=payload.get("minArea"),
            search_term=payload.get("searchTerm"),
            raw_search_term=payload.get("rawSearchTerm"),
            raw_min_area_input=payload.get("rawMinAreaInput"),
            raw_max_area_input=payload.get("rawMaxAreaInput"),
            raw_rent_only=payload.get("rawRentOnly"),
        )
    if event_type == map_event_service.EVENT_TYPE_LAND_CLICK:
        return LandClickMapEventCommand(
            anon_id=payload.get("anonId"),
            land_address=payload.get("landAddress"),
            land_id=payload.get("landId"),
            click_source=payload.get("clickSource"),
        )
    return UnknownMapEventCommand(
        event_type=event_type,
        anon_id=payload.get("anonId"),
    )


def _build_web_visit_event_command(request: Request, payload: dict[str, Any]) -> WebVisitEventCommand:
    metadata = RequestMetadata(
        user_agent=request.headers.get("user-agent"),
        allowed_web_track_paths=tuple(str(path) for path in request.app.state.config.ALLOWED_WEB_TRACK_PATHS),
    )
    return WebVisitEventCommand(
        event_type=payload.get("eventType"),
        anon_id=payload.get("anonId"),
        session_id=payload.get("sessionId"),
        page_path=payload.get("pagePath"),
        page_query=payload.get("pageQuery"),
        client_ts=payload.get("clientTs"),
        client_tz=payload.get("clientTz"),
        client_lang=payload.get("clientLang"),
        platform=payload.get("platform"),
        referrer_url=payload.get("referrerUrl"),
        referrer_domain=payload.get("referrerDomain"),
        utm_source=payload.get("utmSource"),
        utm_medium=payload.get("utmMedium"),
        utm_campaign=payload.get("utmCampaign"),
        utm_term=payload.get("utmTerm"),
        utm_content=payload.get("utmContent"),
        screen_width=payload.get("screenWidth"),
        screen_height=payload.get("screenHeight"),
        viewport_width=payload.get("viewportWidth"),
        viewport_height=payload.get("viewportHeight"),
        metadata=metadata,
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
        blocked = _allow_rate_limited_event(
            request,
            payload=payload,
            prefix="events",
            limit=EVENT_LIMIT_PER_MINUTE,
        )
        if blocked is not None:
            return blocked
        try:
            map_event_service.record_map_event(_build_map_event_command(payload))
        except ServiceError as exc:
            _raise_http_from_service_error(exc)
        return _success_response()

    @router.post("/web-events")
    async def post_web_event(request: Request, payload: dict[str, Any]):
        blocked = _allow_rate_limited_event(
            request,
            payload=payload,
            prefix="web-events",
            limit=WEB_EVENT_LIMIT_PER_MINUTE,
        )
        if blocked is not None:
            return blocked
        try:
            web_stats_service.record_web_visit_event(_build_web_visit_event_command(request, payload))
        except ServiceError as exc:
            _raise_http_from_service_error(exc)
        return _success_response()

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
