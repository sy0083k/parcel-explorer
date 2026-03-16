from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any
from urllib.parse import parse_qsl, urlparse

from fastapi import HTTPException, Request

from app.db.connection import db_connection
from app.repositories import web_visit_repository

WEB_EVENT_TYPE_VISIT_START = "visit_start"
WEB_EVENT_TYPE_HEARTBEAT = "heartbeat"
WEB_EVENT_TYPE_VISIT_END = "visit_end"
WEB_EVENT_TYPES = {WEB_EVENT_TYPE_VISIT_START, WEB_EVENT_TYPE_HEARTBEAT, WEB_EVENT_TYPE_VISIT_END}
WEB_TRACKING_PAGE_PATH = "/"
WEB_STATS_DAYS_DEFAULT = 30
WEB_SESSION_TIMEOUT_MINUTES = 30
WEB_STATS_TOP_LIMIT = 10
SEOUL_OFFSET = timedelta(hours=9)
BOT_UA_PATTERNS = (
    "bot",
    "spider",
    "crawler",
    "curl",
    "wget",
    "python-requests",
    "httpclient",
)


@dataclass(frozen=True)
class UserAgentContext:
    user_agent: str | None
    is_bot: bool
    browser_family: str
    device_type: str
    os_family: str


@dataclass(frozen=True)
class NormalizedWebVisitEvent:
    anon_id: str
    session_id: str
    event_type: str
    page_path: str
    page_query: str | None
    occurred_at: str
    client_tz: str | None
    client_lang: str | None
    platform: str | None
    referrer_url: str | None
    referrer_domain: str | None
    utm_source: str | None
    utm_medium: str | None
    utm_campaign: str | None
    utm_term: str | None
    utm_content: str | None
    screen_width: int | None
    screen_height: int | None
    viewport_width: int | None
    viewport_height: int | None
    user_agent: UserAgentContext


@dataclass(frozen=True)
class ClientContext:
    client_tz: str | None
    client_lang: str | None
    platform: str | None
    screen_width: int | None
    screen_height: int | None
    viewport_width: int | None
    viewport_height: int | None


@dataclass(frozen=True)
class MarketingContext:
    referrer_url: str | None
    referrer_domain: str | None
    utm_source: str | None
    utm_medium: str | None
    utm_campaign: str | None
    utm_term: str | None
    utm_content: str | None


@dataclass(frozen=True)
class WebStatsWindow:
    since_utc: str
    today_utc_start: str
    today_utc_end: str


@dataclass(frozen=True)
class WebStatsQueryResult:
    total_visitors: int
    daily_visitors: int
    session_rows: list[dict[str, Any]]
    visitor_trend_rows: list[dict[str, Any]]
    top_referrers: list[dict[str, Any]]
    top_utm_sources: list[dict[str, Any]]
    top_utm_campaigns: list[dict[str, Any]]
    device_breakdown: list[dict[str, Any]]
    browser_breakdown: list[dict[str, Any]]
    top_page_paths: list[dict[str, Any]]
    channel_breakdown: list[dict[str, Any]]


@dataclass(frozen=True)
class SessionSummary:
    session_count: int
    avg_dwell_minutes: float
    sessions_by_date: dict[str, int]
    durations_by_date: dict[str, list[int]]


def record_web_visit_event(payload: dict[str, Any], request: Request) -> None:
    allowed_paths = tuple(str(path) for path in request.app.state.config.ALLOWED_WEB_TRACK_PATHS)
    normalized_event = _normalize_web_visit_event(payload, request, allowed_paths=allowed_paths)
    _persist_web_visit_event(normalized_event)


def get_web_stats(days: int = WEB_STATS_DAYS_DEFAULT, *, allowed_paths: tuple[str, ...] = ("/",)) -> dict[str, Any]:
    stats_window = _build_web_stats_window(days)
    query_result = _fetch_web_stats_query_result(stats_window, allowed_paths=allowed_paths)
    session_summary = _summarize_sessions(query_result.session_rows)
    return _build_web_stats_response(query_result, session_summary)


def _normalize_web_visit_event(
    payload: dict[str, Any],
    request: Request,
    *,
    allowed_paths: tuple[str, ...],
) -> NormalizedWebVisitEvent:
    event_type = _normalize_event_type(payload.get("eventType"))
    anon_id = normalize_required_token(payload.get("anonId"), "anonId")
    session_id = normalize_required_token(payload.get("sessionId"), "sessionId")
    page_path = normalize_page_path(payload.get("pagePath"), allowed_paths=allowed_paths)
    page_query = normalize_query_string(payload.get("pageQuery"), max_length=1024)
    occurred_at = parse_client_ts(payload.get("clientTs"))

    client_context = _normalize_client_context(payload)
    marketing_context = _normalize_marketing_context(payload)
    user_agent_context = _derive_user_agent_context(request)

    return NormalizedWebVisitEvent(
        anon_id=anon_id,
        session_id=session_id,
        event_type=event_type,
        page_path=page_path,
        page_query=page_query,
        occurred_at=occurred_at,
        client_tz=client_context.client_tz,
        client_lang=client_context.client_lang,
        platform=client_context.platform,
        referrer_url=marketing_context.referrer_url,
        referrer_domain=marketing_context.referrer_domain,
        utm_source=marketing_context.utm_source,
        utm_medium=marketing_context.utm_medium,
        utm_campaign=marketing_context.utm_campaign,
        utm_term=marketing_context.utm_term,
        utm_content=marketing_context.utm_content,
        screen_width=client_context.screen_width,
        screen_height=client_context.screen_height,
        viewport_width=client_context.viewport_width,
        viewport_height=client_context.viewport_height,
        user_agent=user_agent_context,
    )


def _normalize_event_type(raw: Any) -> str:
    event_type = str(raw or "").strip()
    if event_type not in WEB_EVENT_TYPES:
        raise HTTPException(status_code=400, detail="Unsupported eventType.")
    return event_type


def _normalize_client_context(payload: dict[str, Any]) -> ClientContext:
    return ClientContext(
        client_tz=normalize_optional_string(payload.get("clientTz"), max_length=64),
        client_lang=normalize_optional_string(payload.get("clientLang"), max_length=64),
        platform=normalize_optional_string(payload.get("platform"), max_length=64),
        screen_width=normalize_optional_int(payload.get("screenWidth"), min_value=0, max_value=20000),
        screen_height=normalize_optional_int(payload.get("screenHeight"), min_value=0, max_value=20000),
        viewport_width=normalize_optional_int(payload.get("viewportWidth"), min_value=0, max_value=20000),
        viewport_height=normalize_optional_int(payload.get("viewportHeight"), min_value=0, max_value=20000),
    )


def _normalize_marketing_context(payload: dict[str, Any]) -> MarketingContext:
    referrer_url = normalize_referrer_url(payload.get("referrerUrl"))
    return MarketingContext(
        referrer_url=referrer_url,
        referrer_domain=normalize_referrer_domain(payload.get("referrerDomain"), referrer_url),
        utm_source=normalize_optional_string(payload.get("utmSource"), max_length=256),
        utm_medium=normalize_optional_string(payload.get("utmMedium"), max_length=256),
        utm_campaign=normalize_optional_string(payload.get("utmCampaign"), max_length=256),
        utm_term=normalize_optional_string(payload.get("utmTerm"), max_length=256),
        utm_content=normalize_optional_string(payload.get("utmContent"), max_length=256),
    )


def _derive_user_agent_context(request: Request) -> UserAgentContext:
    user_agent = request.headers.get("user-agent", "")[:500] or None
    is_bot = is_bot_user_agent(user_agent or "")
    return UserAgentContext(
        user_agent=user_agent,
        is_bot=is_bot,
        browser_family=classify_browser_family(user_agent or ""),
        device_type=classify_device_type(user_agent or "", is_bot=is_bot),
        os_family=classify_os_family(user_agent or ""),
    )


def _persist_web_visit_event(event: NormalizedWebVisitEvent) -> None:
    with db_connection() as conn:
        web_visit_repository.insert_web_visit_event(
            conn,
            anon_id=event.anon_id,
            session_id=event.session_id,
            event_type=event.event_type,
            page_path=event.page_path,
            page_query=event.page_query,
            occurred_at=event.occurred_at,
            client_tz=event.client_tz,
            client_lang=event.client_lang,
            platform=event.platform,
            user_agent=event.user_agent.user_agent,
            is_bot=event.user_agent.is_bot,
            referrer_url=event.referrer_url,
            referrer_domain=event.referrer_domain,
            utm_source=event.utm_source,
            utm_medium=event.utm_medium,
            utm_campaign=event.utm_campaign,
            utm_term=event.utm_term,
            utm_content=event.utm_content,
            screen_width=event.screen_width,
            screen_height=event.screen_height,
            viewport_width=event.viewport_width,
            viewport_height=event.viewport_height,
            browser_family=event.user_agent.browser_family,
            device_type=event.user_agent.device_type,
            os_family=event.user_agent.os_family,
        )
        conn.commit()


def _build_web_stats_window(days: int) -> WebStatsWindow:
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


def _fetch_web_stats_query_result(
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
            session_rows=_rows_to_dicts(
                web_visit_repository.fetch_web_session_durations_seconds(
                    conn,
                    page_paths=allowed_paths,
                    since_utc=stats_window.since_utc,
                )
            ),
            visitor_trend_rows=_rows_to_dicts(
                web_visit_repository.fetch_web_daily_unique_visitors_trend(
                    conn,
                    page_paths=allowed_paths,
                    since_utc=stats_window.since_utc,
                )
            ),
            top_referrers=_rows_to_dicts(
                web_visit_repository.fetch_top_referrer_domains(
                    conn,
                    since_utc=stats_window.since_utc,
                    limit=WEB_STATS_TOP_LIMIT,
                )
            ),
            top_utm_sources=_rows_to_dicts(
                web_visit_repository.fetch_top_utm_sources(
                    conn,
                    since_utc=stats_window.since_utc,
                    limit=WEB_STATS_TOP_LIMIT,
                )
            ),
            top_utm_campaigns=_rows_to_dicts(
                web_visit_repository.fetch_top_utm_campaigns(
                    conn,
                    since_utc=stats_window.since_utc,
                    limit=WEB_STATS_TOP_LIMIT,
                )
            ),
            device_breakdown=_rows_to_dicts(
                web_visit_repository.fetch_device_breakdown(
                    conn,
                    since_utc=stats_window.since_utc,
                )
            ),
            browser_breakdown=_rows_to_dicts(
                web_visit_repository.fetch_browser_breakdown(
                    conn,
                    since_utc=stats_window.since_utc,
                )
            ),
            top_page_paths=_rows_to_dicts(
                web_visit_repository.fetch_top_page_paths(
                    conn,
                    since_utc=stats_window.since_utc,
                    limit=WEB_STATS_TOP_LIMIT,
                )
            ),
            channel_breakdown=_rows_to_dicts(
                web_visit_repository.fetch_channel_breakdown(
                    conn,
                    since_utc=stats_window.since_utc,
                )
            ),
        )


def _rows_to_dicts(rows: list[Any] | Any) -> list[dict[str, Any]]:
    return [dict(row) for row in rows]


def _summarize_sessions(session_rows: list[dict[str, Any]]) -> SessionSummary:
    session_count = 0
    durations_total_seconds = 0
    durations_by_date: dict[str, list[int]] = {}
    sessions_by_date: dict[str, int] = {}

    for row in session_rows:
        duration_seconds = int(row.get("duration_seconds") or 0)
        capped = min(duration_seconds, 8 * 60 * 60)
        date_key = str(row.get("kst_date"))
        session_count += 1
        durations_total_seconds += capped
        durations_by_date.setdefault(date_key, []).append(capped)
        sessions_by_date[date_key] = sessions_by_date.get(date_key, 0) + 1

    avg_dwell_minutes = round((durations_total_seconds / session_count) / 60, 2) if session_count > 0 else 0.0
    return SessionSummary(
        session_count=session_count,
        avg_dwell_minutes=avg_dwell_minutes,
        sessions_by_date=sessions_by_date,
        durations_by_date=durations_by_date,
    )


def _build_web_stats_response(
    query_result: WebStatsQueryResult,
    session_summary: SessionSummary,
) -> dict[str, Any]:
    daily_trend = _build_daily_trend(
        query_result.visitor_trend_rows,
        session_summary.sessions_by_date,
        session_summary.durations_by_date,
    )
    return {
        "summary": {
            "dailyVisitors": query_result.daily_visitors,
            "totalVisitors": query_result.total_visitors,
            "avgDwellMinutes": session_summary.avg_dwell_minutes,
            "sessionCount": session_summary.session_count,
        },
        "dailyTrend": daily_trend,
        "topReferrers": [{"domain": str(row["referrer_domain"]), "count": int(row["count"])} for row in query_result.top_referrers],
        "topUtmSources": [{"source": str(row["utm_source"]), "count": int(row["count"])} for row in query_result.top_utm_sources],
        "topUtmCampaigns": [{"campaign": str(row["utm_campaign"]), "count": int(row["count"])} for row in query_result.top_utm_campaigns],
        "deviceBreakdown": [{"deviceType": str(row["device_type"]), "count": int(row["count"])} for row in query_result.device_breakdown],
        "browserBreakdown": [{"browserFamily": str(row["browser_family"]), "count": int(row["count"])} for row in query_result.browser_breakdown],
        "topPagePaths": [{"pagePath": str(row["page_path"]), "count": int(row["count"])} for row in query_result.top_page_paths],
        "channelBreakdown": [{"channel": str(row["channel"]), "count": int(row["count"])} for row in query_result.channel_breakdown],
    }


def _build_daily_trend(
    visitor_trend_rows: list[dict[str, Any]],
    sessions_by_date: dict[str, int],
    durations_by_date: dict[str, list[int]],
) -> list[dict[str, Any]]:
    visitors_by_date = {str(row["date"]): int(row["visitors"]) for row in visitor_trend_rows}
    all_dates = sorted(set(visitors_by_date.keys()) | set(sessions_by_date.keys()) | set(durations_by_date.keys()))
    daily_trend: list[dict[str, Any]] = []
    for date in all_dates:
        per_day_durations = durations_by_date.get(date, [])
        avg_day_dwell = round((sum(per_day_durations) / len(per_day_durations)) / 60, 2) if per_day_durations else 0.0
        daily_trend.append(
            {
                "date": date,
                "visitors": visitors_by_date.get(date, 0),
                "sessions": sessions_by_date.get(date, 0),
                "avgDwellMinutes": avg_day_dwell,
            }
        )
    return daily_trend


def normalize_required_token(raw: Any, field_name: str) -> str:
    value = str(raw or "").strip()
    if not value:
        raise HTTPException(status_code=400, detail=f"{field_name} is required.")
    return value[:128]


def normalize_optional_string(raw: Any, *, max_length: int) -> str | None:
    if raw is None:
        return None
    value = str(raw).strip()
    if not value:
        return None
    return value[:max_length]


def normalize_optional_int(raw: Any, *, min_value: int, max_value: int) -> int | None:
    if raw in (None, ""):
        return None
    try:
        value = int(raw)
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail="numeric client context fields must be integer.") from exc
    if value < min_value or value > max_value:
        return None
    return value


def normalize_page_path(raw: Any, *, allowed_paths: tuple[str, ...]) -> str:
    value = str(raw or "").strip() or WEB_TRACKING_PAGE_PATH
    if not value.startswith("/"):
        raise HTTPException(status_code=400, detail="pagePath must start with '/'.")
    if len(value) > 256:
        raise HTTPException(status_code=400, detail="pagePath is too long.")
    if value not in allowed_paths:
        raise HTTPException(status_code=400, detail="Unsupported pagePath.")
    return value


def normalize_query_string(raw: Any, *, max_length: int) -> str | None:
    if raw is None:
        return None
    value = str(raw).strip()
    if not value:
        return None
    if value.startswith("?"):
        value = value[1:]
    return value[:max_length]


def normalize_referrer_url(raw: Any) -> str | None:
    text = normalize_optional_string(raw, max_length=2048)
    if text is None:
        return None
    try:
        parsed = urlparse(text)
    except ValueError:
        return None
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return None
    path = parsed.path or "/"
    normalized = f"{parsed.scheme}://{parsed.netloc}{path}"
    return normalized[:1024]


def normalize_referrer_domain(raw_domain: Any, referrer_url: str | None) -> str | None:
    domain = normalize_optional_string(raw_domain, max_length=255)
    if domain:
        return domain.lower()
    if not referrer_url:
        return None
    try:
        parsed = urlparse(referrer_url)
    except ValueError:
        return None
    host = parsed.hostname or ""
    host = host.strip().lower()
    return host or None


def parse_client_ts(raw: Any) -> str:
    if raw in (None, ""):
        return datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S")
    try:
        ts = float(raw)
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail="clientTs must be unix timestamp seconds.") from exc

    event_dt = datetime.fromtimestamp(ts, tz=UTC)
    now = datetime.now(UTC)
    if event_dt > now + timedelta(minutes=5):
        event_dt = now
    if event_dt < now - timedelta(days=7):
        event_dt = now - timedelta(days=7)
    return event_dt.strftime("%Y-%m-%d %H:%M:%S")


def is_bot_user_agent(user_agent: str) -> bool:
    normalized = user_agent.lower()
    return any(pattern in normalized for pattern in BOT_UA_PATTERNS)


def classify_browser_family(user_agent: str) -> str:
    ua = user_agent.lower()
    if "edg/" in ua or "edge/" in ua:
        return "edge"
    if "opr/" in ua or "opera" in ua:
        return "other"
    if "chrome/" in ua and "chromium" not in ua and "edg/" not in ua:
        return "chrome"
    if "safari/" in ua and "chrome/" not in ua and "chromium" not in ua:
        return "safari"
    if "firefox/" in ua:
        return "firefox"
    if "trident/" in ua or "msie" in ua:
        return "ie"
    return "other"


def classify_device_type(user_agent: str, *, is_bot: bool) -> str:
    if is_bot:
        return "bot"
    ua = user_agent.lower()
    if "tablet" in ua or "ipad" in ua:
        return "tablet"
    if "mobile" in ua or "iphone" in ua or "android" in ua:
        return "mobile"
    if not ua:
        return "unknown"
    return "desktop"


def classify_os_family(user_agent: str) -> str:
    ua = user_agent.lower()
    if "windows" in ua:
        return "windows"
    if "mac os" in ua or "macintosh" in ua:
        return "macos"
    if "iphone" in ua or "ipad" in ua or "ios" in ua:
        return "ios"
    if "android" in ua:
        return "android"
    if "linux" in ua:
        return "linux"
    return "other"


def extract_utm_from_query(query_string: str | None) -> dict[str, str | None]:
    if not query_string:
        return {
            "utmSource": None,
            "utmMedium": None,
            "utmCampaign": None,
            "utmTerm": None,
            "utmContent": None,
        }

    parsed_pairs = parse_qsl(query_string, keep_blank_values=False)
    values = {key.lower(): value for key, value in parsed_pairs}
    return {
        "utmSource": values.get("utm_source"),
        "utmMedium": values.get("utm_medium"),
        "utmCampaign": values.get("utm_campaign"),
        "utmTerm": values.get("utm_term"),
        "utmContent": values.get("utm_content"),
    }
