from __future__ import annotations

from typing import Any

from fastapi import Request

from app.db.connection import db_connection
from app.repositories import poi_repository
from app.services import map_event_service, raw_query_export_service, web_stats_service

EVENT_TYPE_SEARCH = map_event_service.EVENT_TYPE_SEARCH
EVENT_TYPE_LAND_CLICK = map_event_service.EVENT_TYPE_LAND_CLICK
WEB_EVENT_TYPE_VISIT_START = web_stats_service.WEB_EVENT_TYPE_VISIT_START
WEB_EVENT_TYPE_HEARTBEAT = web_stats_service.WEB_EVENT_TYPE_HEARTBEAT
WEB_EVENT_TYPE_VISIT_END = web_stats_service.WEB_EVENT_TYPE_VISIT_END
WEB_EVENT_TYPES = web_stats_service.WEB_EVENT_TYPES
WEB_TRACKING_PAGE_PATH = web_stats_service.WEB_TRACKING_PAGE_PATH
WEB_STATS_DAYS_DEFAULT = web_stats_service.WEB_STATS_DAYS_DEFAULT
WEB_SESSION_TIMEOUT_MINUTES = web_stats_service.WEB_SESSION_TIMEOUT_MINUTES
SEOUL_OFFSET = web_stats_service.SEOUL_OFFSET
BOT_UA_PATTERNS = web_stats_service.BOT_UA_PATTERNS
MIN_AREA_BUCKETS = map_event_service.MIN_AREA_BUCKETS
MIN_AREA_BUCKET_OVERFLOW = map_event_service.MIN_AREA_BUCKET_OVERFLOW
DIGIT_RE = map_event_service.DIGIT_RE


def record_map_event(payload: dict[str, Any]) -> None:
    map_event_service.record_map_event(payload)


def get_admin_stats(limit: int = 10) -> dict[str, Any]:
    return map_event_service.get_admin_stats(limit=limit)


def get_land_stats() -> dict[str, int]:
    with db_connection() as conn:
        total_lands = poi_repository.count_all_lands(conn)
        missing_geom_lands = poi_repository.count_missing_geom(conn)
    return {
        "totalLands": total_lands,
        "missingGeomLands": missing_geom_lands,
    }


def record_web_visit_event(payload: dict[str, Any], request: Request) -> None:
    web_stats_service.record_web_visit_event(payload, request)


def get_web_stats(days: int = WEB_STATS_DAYS_DEFAULT) -> dict[str, Any]:
    return web_stats_service.get_web_stats(days=days)


def export_raw_query_csv(
    *,
    event_type: str,
    date_from: str | None,
    date_to: str | None,
    limit: int,
) -> str:
    return raw_query_export_service.export_raw_query_csv(
        event_type=event_type,
        date_from=date_from,
        date_to=date_to,
        limit=limit,
    )


def _normalize_anon_id(raw: Any) -> str | None:
    return map_event_service.normalize_anon_id(raw)


def _normalize_land_address(raw: Any) -> str:
    return map_event_service.normalize_land_address(raw)


def _parse_min_area(raw: Any) -> float:
    return map_event_service.parse_min_area(raw)


def _min_area_bucket(min_area: float) -> str:
    return map_event_service.min_area_bucket_for(min_area)


def _normalize_search_term(raw: Any) -> str:
    return map_event_service.normalize_search_term(raw)


def _normalize_required_token(raw: Any, field_name: str) -> str:
    return web_stats_service.normalize_required_token(raw, field_name)


def _normalize_optional_string(raw: Any, *, max_length: int) -> str | None:
    return web_stats_service.normalize_optional_string(raw, max_length=max_length)


def _parse_client_ts(raw: Any) -> str:
    return web_stats_service.parse_client_ts(raw)


def _is_bot_user_agent(user_agent: str) -> bool:
    return web_stats_service.is_bot_user_agent(user_agent)


def _serialize_raw_payload(payload: dict[str, Any]) -> str:
    return map_event_service.serialize_raw_payload(payload)


def _normalize_raw_text(raw: Any, *, max_length: int) -> str | None:
    return map_event_service.normalize_raw_text(raw, max_length=max_length)


def _parse_date_start(raw: str | None) -> str | None:
    return raw_query_export_service.parse_date_start(raw)


def _parse_date_end_exclusive(raw: str | None) -> str | None:
    return raw_query_export_service.parse_date_end_exclusive(raw)
