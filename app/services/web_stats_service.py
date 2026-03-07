from __future__ import annotations

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


def record_web_visit_event(payload: dict[str, Any], request: Request) -> None:
    event_type = str(payload.get("eventType", "")).strip()
    if event_type not in WEB_EVENT_TYPES:
        raise HTTPException(status_code=400, detail="Unsupported eventType.")

    config = request.app.state.config
    allowed_paths = tuple(str(path) for path in config.ALLOWED_WEB_TRACK_PATHS)

    anon_id = normalize_required_token(payload.get("anonId"), "anonId")
    session_id = normalize_required_token(payload.get("sessionId"), "sessionId")
    page_path = normalize_page_path(payload.get("pagePath"), allowed_paths=allowed_paths)
    page_query = normalize_query_string(payload.get("pageQuery"), max_length=1024)

    client_tz = normalize_optional_string(payload.get("clientTz"), max_length=64)
    client_lang = normalize_optional_string(payload.get("clientLang"), max_length=64)
    platform = normalize_optional_string(payload.get("platform"), max_length=64)
    occurred_at = parse_client_ts(payload.get("clientTs"))

    referrer_url = normalize_referrer_url(payload.get("referrerUrl"))
    referrer_domain = normalize_referrer_domain(payload.get("referrerDomain"), referrer_url)

    utm_source = normalize_optional_string(payload.get("utmSource"), max_length=256)
    utm_medium = normalize_optional_string(payload.get("utmMedium"), max_length=256)
    utm_campaign = normalize_optional_string(payload.get("utmCampaign"), max_length=256)
    utm_term = normalize_optional_string(payload.get("utmTerm"), max_length=256)
    utm_content = normalize_optional_string(payload.get("utmContent"), max_length=256)

    user_agent = request.headers.get("user-agent", "")[:500] or None
    is_bot = is_bot_user_agent(user_agent or "")
    browser_family = classify_browser_family(user_agent or "")
    device_type = classify_device_type(user_agent or "", is_bot=is_bot)
    os_family = classify_os_family(user_agent or "")

    screen_width = normalize_optional_int(payload.get("screenWidth"), min_value=0, max_value=20000)
    screen_height = normalize_optional_int(payload.get("screenHeight"), min_value=0, max_value=20000)
    viewport_width = normalize_optional_int(payload.get("viewportWidth"), min_value=0, max_value=20000)
    viewport_height = normalize_optional_int(payload.get("viewportHeight"), min_value=0, max_value=20000)

    with db_connection() as conn:
        web_visit_repository.insert_web_visit_event(
            conn,
            anon_id=anon_id,
            session_id=session_id,
            event_type=event_type,
            page_path=page_path,
            page_query=page_query,
            occurred_at=occurred_at,
            client_tz=client_tz,
            client_lang=client_lang,
            platform=platform,
            user_agent=user_agent,
            is_bot=is_bot,
            referrer_url=referrer_url,
            referrer_domain=referrer_domain,
            utm_source=utm_source,
            utm_medium=utm_medium,
            utm_campaign=utm_campaign,
            utm_term=utm_term,
            utm_content=utm_content,
            screen_width=screen_width,
            screen_height=screen_height,
            viewport_width=viewport_width,
            viewport_height=viewport_height,
            browser_family=browser_family,
            device_type=device_type,
            os_family=os_family,
        )
        conn.commit()


def get_web_stats(days: int = WEB_STATS_DAYS_DEFAULT, *, allowed_paths: tuple[str, ...] = ("/",)) -> dict[str, Any]:
    clamped_days = max(1, min(int(days), 365))
    now_utc = datetime.now(UTC)
    now_kst = now_utc + SEOUL_OFFSET
    today_kst_start = now_kst.replace(hour=0, minute=0, second=0, microsecond=0)
    today_kst_end = today_kst_start + timedelta(days=1)
    today_utc_start = (today_kst_start - SEOUL_OFFSET).strftime("%Y-%m-%d %H:%M:%S")
    today_utc_end = (today_kst_end - SEOUL_OFFSET).strftime("%Y-%m-%d %H:%M:%S")
    since_utc = (now_utc - timedelta(days=clamped_days)).strftime("%Y-%m-%d %H:%M:%S")

    with db_connection(row_factory=True) as conn:
        total_visitors = web_visit_repository.fetch_web_total_visitors(
            conn, page_paths=allowed_paths
        )
        daily_visitors = web_visit_repository.fetch_web_daily_visitors(
            conn,
            page_paths=allowed_paths,
            since_utc=today_utc_start,
            until_utc=today_utc_end,
        )
        session_rows = web_visit_repository.fetch_web_session_durations_seconds(
            conn,
            page_paths=allowed_paths,
            since_utc=since_utc,
        )
        visitor_trend_rows = web_visit_repository.fetch_web_daily_unique_visitors_trend(
            conn,
            page_paths=allowed_paths,
            since_utc=since_utc,
        )
        top_referrers = web_visit_repository.fetch_top_referrer_domains(
            conn,
            since_utc=since_utc,
            limit=WEB_STATS_TOP_LIMIT,
        )
        top_utm_sources = web_visit_repository.fetch_top_utm_sources(
            conn,
            since_utc=since_utc,
            limit=WEB_STATS_TOP_LIMIT,
        )
        top_utm_campaigns = web_visit_repository.fetch_top_utm_campaigns(
            conn,
            since_utc=since_utc,
            limit=WEB_STATS_TOP_LIMIT,
        )
        device_breakdown = web_visit_repository.fetch_device_breakdown(
            conn,
            since_utc=since_utc,
        )
        browser_breakdown = web_visit_repository.fetch_browser_breakdown(
            conn,
            since_utc=since_utc,
        )
        top_page_paths = web_visit_repository.fetch_top_page_paths(
            conn,
            since_utc=since_utc,
            limit=WEB_STATS_TOP_LIMIT,
        )
        channel_breakdown = web_visit_repository.fetch_channel_breakdown(
            conn,
            since_utc=since_utc,
        )

    session_count = 0
    durations_total_seconds = 0
    durations_by_date: dict[str, list[int]] = {}
    for row in session_rows:
        duration_seconds = int(row["duration_seconds"] or 0)
        capped = min(duration_seconds, 8 * 60 * 60)
        session_count += 1
        durations_total_seconds += capped
        date_key = str(row["kst_date"])
        durations_by_date.setdefault(date_key, []).append(capped)

    avg_dwell_minutes = round((durations_total_seconds / session_count) / 60, 2) if session_count > 0 else 0.0

    sessions_by_date: dict[str, int] = {}
    for row in session_rows:
        date_key = str(row["kst_date"])
        sessions_by_date[date_key] = sessions_by_date.get(date_key, 0) + 1

    visitors_by_date = {str(row["date"]): int(row["visitors"]) for row in visitor_trend_rows}

    all_dates = sorted(set(visitors_by_date.keys()) | set(sessions_by_date.keys()) | set(durations_by_date.keys()))
    daily_trend = []
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

    return {
        "summary": {
            "dailyVisitors": daily_visitors,
            "totalVisitors": total_visitors,
            "avgDwellMinutes": avg_dwell_minutes,
            "sessionCount": session_count,
        },
        "dailyTrend": daily_trend,
        "topReferrers": [{"domain": str(row["referrer_domain"]), "count": int(row["count"])} for row in top_referrers],
        "topUtmSources": [{"source": str(row["utm_source"]), "count": int(row["count"])} for row in top_utm_sources],
        "topUtmCampaigns": [
            {"campaign": str(row["utm_campaign"]), "count": int(row["count"])}
            for row in top_utm_campaigns
        ],
        "deviceBreakdown": [{"deviceType": str(row["device_type"]), "count": int(row["count"])} for row in device_breakdown],
        "browserBreakdown": [
            {"browserFamily": str(row["browser_family"]), "count": int(row["count"])}
            for row in browser_breakdown
        ],
        "topPagePaths": [{"pagePath": str(row["page_path"]), "count": int(row["count"])} for row in top_page_paths],
        "channelBreakdown": [{"channel": str(row["channel"]), "count": int(row["count"])} for row in channel_breakdown],
    }


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
    if len(value) > max_length:
        return value[:max_length]
    return value


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
        now = datetime.now(UTC)
        return now.strftime("%Y-%m-%d %H:%M:%S")
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
