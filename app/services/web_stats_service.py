from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

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

    anon_id = normalize_required_token(payload.get("anonId"), "anonId")
    session_id = normalize_required_token(payload.get("sessionId"), "sessionId")
    page_path = str(payload.get("pagePath", "")).strip() or WEB_TRACKING_PAGE_PATH
    if page_path != WEB_TRACKING_PAGE_PATH:
        raise HTTPException(status_code=400, detail="Unsupported pagePath.")

    client_tz = normalize_optional_string(payload.get("clientTz"), max_length=64)
    occurred_at = parse_client_ts(payload.get("clientTs"))
    user_agent = request.headers.get("user-agent", "")[:500] or None
    is_bot = is_bot_user_agent(user_agent or "")

    with db_connection() as conn:
        web_visit_repository.insert_web_visit_event(
            conn,
            anon_id=anon_id,
            session_id=session_id,
            event_type=event_type,
            page_path=page_path,
            occurred_at=occurred_at,
            client_tz=client_tz,
            user_agent=user_agent,
            is_bot=is_bot,
        )
        conn.commit()


def get_web_stats(days: int = WEB_STATS_DAYS_DEFAULT) -> dict[str, Any]:
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
            conn, page_path=WEB_TRACKING_PAGE_PATH
        )
        daily_visitors = web_visit_repository.fetch_web_daily_visitors(
            conn,
            page_path=WEB_TRACKING_PAGE_PATH,
            since_utc=today_utc_start,
            until_utc=today_utc_end,
        )
        session_rows = web_visit_repository.fetch_web_session_durations_seconds(
            conn,
            page_path=WEB_TRACKING_PAGE_PATH,
            since_utc=since_utc,
        )
        visitor_trend_rows = web_visit_repository.fetch_web_daily_unique_visitors_trend(
            conn,
            page_path=WEB_TRACKING_PAGE_PATH,
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
