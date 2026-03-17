from __future__ import annotations

from typing import Any

from app.services import web_stats_constants as constants
from app.services import web_stats_ingest as ingest
from app.services import web_stats_normalizers as normalizers
from app.services import web_stats_presenter as presenter
from app.services import web_stats_queries as queries
from app.services import web_stats_types as types
from app.services.service_models import WebVisitEventCommand

WEB_EVENT_TYPE_VISIT_START = constants.WEB_EVENT_TYPE_VISIT_START
WEB_EVENT_TYPE_HEARTBEAT = constants.WEB_EVENT_TYPE_HEARTBEAT
WEB_EVENT_TYPE_VISIT_END = constants.WEB_EVENT_TYPE_VISIT_END
WEB_EVENT_TYPES = constants.WEB_EVENT_TYPES
WEB_TRACKING_PAGE_PATH = constants.WEB_TRACKING_PAGE_PATH
WEB_STATS_DAYS_DEFAULT = constants.WEB_STATS_DAYS_DEFAULT
WEB_SESSION_TIMEOUT_MINUTES = constants.WEB_SESSION_TIMEOUT_MINUTES
SEOUL_OFFSET = constants.SEOUL_OFFSET
BOT_UA_PATTERNS = constants.BOT_UA_PATTERNS

UserAgentContext = types.UserAgentContext
NormalizedWebVisitEvent = types.NormalizedWebVisitEvent
ClientContext = types.ClientContext
MarketingContext = types.MarketingContext
WebStatsWindow = types.WebStatsWindow
WebStatsQueryResult = types.WebStatsQueryResult
SessionSummary = types.SessionSummary

normalize_required_token = normalizers.normalize_required_token
normalize_optional_string = normalizers.normalize_optional_string
normalize_optional_int = normalizers.normalize_optional_int
normalize_page_path = normalizers.normalize_page_path
normalize_query_string = normalizers.normalize_query_string
normalize_referrer_url = normalizers.normalize_referrer_url
normalize_referrer_domain = normalizers.normalize_referrer_domain
parse_client_ts = normalizers.parse_client_ts
is_bot_user_agent = normalizers.is_bot_user_agent
classify_browser_family = normalizers.classify_browser_family
classify_device_type = normalizers.classify_device_type
classify_os_family = normalizers.classify_os_family
extract_utm_from_query = normalizers.extract_utm_from_query

_normalize_event_type = normalizers.normalize_event_type
_normalize_web_visit_event = ingest.normalize_web_visit_event
_normalize_client_context = ingest.normalize_client_context
_normalize_marketing_context = ingest.normalize_marketing_context
_derive_user_agent_context = ingest.derive_user_agent_context
_persist_web_visit_event = ingest.persist_web_visit_event
_build_web_stats_window = queries.build_web_stats_window
_fetch_web_stats_query_result = queries.fetch_web_stats_query_result
_rows_to_dicts = queries.rows_to_dicts
_summarize_sessions = presenter.summarize_sessions
_build_web_stats_response = presenter.build_web_stats_response
_build_daily_trend = presenter.build_daily_trend


def record_web_visit_event(command: WebVisitEventCommand) -> None:
    ingest.record_web_visit_event(command)


def get_web_stats(days: int = WEB_STATS_DAYS_DEFAULT, *, allowed_paths: tuple[str, ...] = ("/",)) -> dict[str, Any]:
    stats_window = _build_web_stats_window(days)
    query_result = _fetch_web_stats_query_result(stats_window, allowed_paths=allowed_paths)
    session_summary = _summarize_sessions(query_result.session_rows)
    return _build_web_stats_response(query_result, session_summary)
