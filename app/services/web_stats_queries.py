from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from app.db.connection import db_connection
from app.repositories import web_visit_repository
from app.services.web_stats_constants import SEOUL_OFFSET, WEB_STATS_TOP_LIMIT
from app.services.web_stats_types import WebStatsQueryResult, WebStatsWindow


def build_web_stats_window(days: int) -> WebStatsWindow:
    clamped_days = max(1, min(int(days), 365))
    now_utc = datetime.now(UTC)
    now_kst = now_utc + SEOUL_OFFSET
    today_kst_start = now_kst.replace(hour=0, minute=0, second=0, microsecond=0)
    today_kst_end = today_kst_start + timedelta(days=1)
    return WebStatsWindow(
        since_utc=(now_utc - timedelta(days=clamped_days)).strftime("%Y-%m-%d %H:%M:%S"),
        today_utc_start=(today_kst_start - SEOUL_OFFSET).strftime("%Y-%m-%d %H:%M:%S"),
        today_utc_end=(today_kst_end - SEOUL_OFFSET).strftime("%Y-%m-%d %H:%M:%S"),
    )


def fetch_web_stats_query_result(
    stats_window: WebStatsWindow,
    *,
    allowed_paths: tuple[str, ...],
) -> WebStatsQueryResult:
    with db_connection(row_factory=True) as conn:
        return WebStatsQueryResult(
            total_visitors=web_visit_repository.fetch_web_total_visitors(conn, page_paths=allowed_paths),
            daily_visitors=web_visit_repository.fetch_web_daily_visitors(
                conn,
                page_paths=allowed_paths,
                since_utc=stats_window.today_utc_start,
                until_utc=stats_window.today_utc_end,
            ),
            session_rows=rows_to_dicts(
                web_visit_repository.fetch_web_session_durations_seconds(
                    conn,
                    page_paths=allowed_paths,
                    since_utc=stats_window.since_utc,
                )
            ),
            visitor_trend_rows=rows_to_dicts(
                web_visit_repository.fetch_web_daily_unique_visitors_trend(
                    conn,
                    page_paths=allowed_paths,
                    since_utc=stats_window.since_utc,
                )
            ),
            top_referrers=rows_to_dicts(
                web_visit_repository.fetch_top_referrer_domains(
                    conn,
                    since_utc=stats_window.since_utc,
                    limit=WEB_STATS_TOP_LIMIT,
                )
            ),
            top_utm_sources=rows_to_dicts(
                web_visit_repository.fetch_top_utm_sources(
                    conn,
                    since_utc=stats_window.since_utc,
                    limit=WEB_STATS_TOP_LIMIT,
                )
            ),
            top_utm_campaigns=rows_to_dicts(
                web_visit_repository.fetch_top_utm_campaigns(
                    conn,
                    since_utc=stats_window.since_utc,
                    limit=WEB_STATS_TOP_LIMIT,
                )
            ),
            device_breakdown=rows_to_dicts(
                web_visit_repository.fetch_device_breakdown(
                    conn,
                    since_utc=stats_window.since_utc,
                )
            ),
            browser_breakdown=rows_to_dicts(
                web_visit_repository.fetch_browser_breakdown(
                    conn,
                    since_utc=stats_window.since_utc,
                )
            ),
            top_page_paths=rows_to_dicts(
                web_visit_repository.fetch_top_page_paths(
                    conn,
                    since_utc=stats_window.since_utc,
                    limit=WEB_STATS_TOP_LIMIT,
                )
            ),
            channel_breakdown=rows_to_dicts(
                web_visit_repository.fetch_channel_breakdown(
                    conn,
                    since_utc=stats_window.since_utc,
                )
            ),
        )


def rows_to_dicts(rows: list[Any] | Any) -> list[dict[str, Any]]:
    return [dict(row) for row in rows]
