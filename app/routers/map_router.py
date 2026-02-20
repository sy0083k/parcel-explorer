from fastapi import APIRouter, HTTPException, Request
from typing import Any

from app.services import land_service, stats_service

DEFAULT_LANDS_PAGE_LIMIT = 500
MAX_LANDS_PAGE_LIMIT = 2000


def _parse_cursor(raw_cursor: str | None) -> int | None:
    if raw_cursor is None or raw_cursor.strip() == "":
        return None
    cursor = int(raw_cursor)
    if cursor < 0:
        raise ValueError("cursor must be >= 0")
    return cursor


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
    async def post_map_event(payload: dict[str, Any]) -> dict[str, bool]:
        stats_service.record_map_event(payload)
        return {"success": True}

    @router.post("/web-events")
    async def post_web_event(request: Request, payload: dict[str, Any]) -> dict[str, bool]:
        stats_service.record_web_visit_event(payload, request)
        return {"success": True}

    return router


router = create_router()
