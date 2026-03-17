from app.repositories.web_visit_query_repository import (
    fetch_browser_breakdown,
    fetch_channel_breakdown,
    fetch_device_breakdown,
    fetch_top_page_paths,
    fetch_top_referrer_domains,
    fetch_top_utm_campaigns,
    fetch_top_utm_sources,
    fetch_web_daily_unique_visitors_trend,
    fetch_web_daily_visitors,
    fetch_web_session_durations_seconds,
    fetch_web_total_visitors,
)
from app.repositories.web_visit_schema_repository import init_web_visit_schema
from app.repositories.web_visit_write_repository import insert_web_visit_event

__all__ = [
    "fetch_browser_breakdown",
    "fetch_channel_breakdown",
    "fetch_device_breakdown",
    "fetch_top_page_paths",
    "fetch_top_referrer_domains",
    "fetch_top_utm_campaigns",
    "fetch_top_utm_sources",
    "fetch_web_daily_unique_visitors_trend",
    "fetch_web_daily_visitors",
    "fetch_web_session_durations_seconds",
    "fetch_web_total_visitors",
    "init_web_visit_schema",
    "insert_web_visit_event",
]
