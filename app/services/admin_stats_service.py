from __future__ import annotations

from typing import Any

from app.core import get_settings
from app.db.connection import db_connection
from app.repositories import land_repository
from app.services import map_event_service, raw_query_export_service, web_stats_service
from app.services.service_models import RawQueryExportCommand


def get_dashboard_stats(limit: int = 10) -> dict[str, Any]:
    payload = map_event_service.get_admin_stats(limit=limit)
    payload["landSummary"] = _get_land_stats()
    return payload


def get_web_stats(days: int = web_stats_service.WEB_STATS_DAYS_DEFAULT) -> dict[str, Any]:
    settings = get_settings()
    return web_stats_service.get_web_stats(days=days, allowed_paths=settings.allowed_web_track_paths)


def export_raw_query_csv(
    *,
    event_type: str,
    date_from: str | None,
    date_to: str | None,
    limit: int,
) -> raw_query_export_service.RawQueryCsvExportResult:
    settings = get_settings()
    return raw_query_export_service.export_raw_query_csv(
        RawQueryExportCommand(
            event_type=event_type,
            date_from=date_from,
            date_to=date_to,
            limit=limit,
            max_rows=settings.raw_query_export_max_rows,
            timeout_s=settings.raw_query_export_timeout_s,
        )
    )


def _get_land_stats() -> dict[str, int]:
    with db_connection() as conn:
        total_lands = land_repository.count_all_lands(conn)
        missing_geom_lands = land_repository.count_missing_geom(conn)
    return {
        "totalLands": total_lands,
        "missingGeomLands": missing_geom_lands,
    }
