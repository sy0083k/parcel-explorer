from __future__ import annotations

import re
from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import HTTPException
from fastapi import Request

from app.db.connection import db_connection
from app.repositories import idle_land_repository

EVENT_TYPE_SEARCH = "search"
EVENT_TYPE_LAND_CLICK = "land_click"
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

MIN_AREA_BUCKETS: list[tuple[float, float, str]] = [
    (0.0, 100.0, "0-99"),
    (100.0, 200.0, "100-199"),
    (200.0, 300.0, "200-299"),
    (300.0, 500.0, "300-499"),
    (500.0, 1000.0, "500-999"),
]
MIN_AREA_BUCKET_OVERFLOW = "1000+"
DIGIT_RE = re.compile(r"\d+")


def record_map_event(payload: dict[str, Any]) -> None:
    event_type = str(payload.get("eventType", "")).strip()
    anon_id = _normalize_anon_id(payload.get("anonId"))

    if event_type == EVENT_TYPE_SEARCH:
        min_area = _parse_min_area(payload.get("minArea"))
        min_area_bucket = _min_area_bucket(min_area)
        region_name = _normalize_search_term(payload.get("searchTerm"))
        normalized_region_name = region_name if region_name else None

        with db_connection() as conn:
            idle_land_repository.insert_map_event(
                conn,
                event_type=EVENT_TYPE_SEARCH,
                anon_id=anon_id,
                region_name=normalized_region_name,
                min_area_value=min_area,
                min_area_bucket=min_area_bucket,
                region_source="user_input",
            )
            conn.commit()
        return

    if event_type == EVENT_TYPE_LAND_CLICK:
        land_address = _normalize_land_address(payload.get("landAddress"))
        if not land_address:
            raise HTTPException(status_code=400, detail="landAddress is required for land_click.")
        with db_connection() as conn:
            idle_land_repository.insert_map_event(
                conn,
                event_type=EVENT_TYPE_LAND_CLICK,
                anon_id=anon_id,
                land_address=land_address,
            )
            conn.commit()
        return

    raise HTTPException(status_code=400, detail="Unsupported eventType.")


def get_admin_stats(limit: int = 10) -> dict[str, Any]:
    clamped_limit = max(1, min(int(limit), 50))

    with db_connection(row_factory=True) as conn:
        summary = idle_land_repository.fetch_event_summary(conn)
        top_regions = idle_land_repository.fetch_top_regions(conn, limit=clamped_limit)
        top_min_area_buckets = idle_land_repository.fetch_top_min_area_buckets(conn, limit=clamped_limit)
        top_clicked_lands = idle_land_repository.fetch_top_clicked_lands(conn, limit=clamped_limit)
        daily_trend = idle_land_repository.fetch_daily_event_counts(conn)

    return {
        "summary": {
            "searchCount": int(summary["search_count"] or 0),
            "clickCount": int(summary["click_count"] or 0),
            "uniqueSessionCount": int(summary["unique_session_count"] or 0),
        },
        "topRegions": [{"region": str(row["region_name"]), "count": int(row["count"])} for row in top_regions],
        "topMinAreaBuckets": [
            {"bucket": str(row["min_area_bucket"]), "count": int(row["count"])} for row in top_min_area_buckets
        ],
        "topClickedLands": [
            {
                "address": str(row["land_address"]),
                "clickCount": int(row["click_count"]),
                "uniqueSessionCount": int(row["unique_session_count"]),
            }
            for row in top_clicked_lands
        ],
        "dailyTrend": [
            {
                "date": str(row["date"]),
                "searchCount": int(row["search_count"]),
                "clickCount": int(row["click_count"]),
            }
            for row in daily_trend
        ],
    }


def record_web_visit_event(payload: dict[str, Any], request: Request) -> None:
    event_type = str(payload.get("eventType", "")).strip()
    if event_type not in WEB_EVENT_TYPES:
        raise HTTPException(status_code=400, detail="Unsupported eventType.")

    anon_id = _normalize_required_token(payload.get("anonId"), "anonId")
    session_id = _normalize_required_token(payload.get("sessionId"), "sessionId")
    page_path = str(payload.get("pagePath", "")).strip() or WEB_TRACKING_PAGE_PATH
    if page_path != WEB_TRACKING_PAGE_PATH:
        raise HTTPException(status_code=400, detail="Unsupported pagePath.")

    client_tz = _normalize_optional_string(payload.get("clientTz"), max_length=64)
    occurred_at = _parse_client_ts(payload.get("clientTs"))
    user_agent = request.headers.get("user-agent", "")[:500] or None
    is_bot = _is_bot_user_agent(user_agent or "")

    with db_connection() as conn:
        idle_land_repository.insert_web_visit_event(
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
        total_visitors = idle_land_repository.fetch_web_total_visitors(
            conn, page_path=WEB_TRACKING_PAGE_PATH
        )
        daily_visitors = idle_land_repository.fetch_web_daily_visitors(
            conn,
            page_path=WEB_TRACKING_PAGE_PATH,
            since_utc=today_utc_start,
            until_utc=today_utc_end,
        )
        session_rows = idle_land_repository.fetch_web_session_durations_seconds(
            conn,
            page_path=WEB_TRACKING_PAGE_PATH,
            since_utc=since_utc,
        )
        visitor_trend_rows = idle_land_repository.fetch_web_daily_unique_visitors_trend(
            conn,
            page_path=WEB_TRACKING_PAGE_PATH,
            since_utc=since_utc,
        )

    session_count = 0
    durations_total_seconds = 0
    durations_by_date: dict[str, list[int]] = {}
    for row in session_rows:
        duration_seconds = int(row["duration_seconds"] or 0)
        # Cap a single session duration to reduce outliers from missing end events.
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


def _normalize_anon_id(raw: Any) -> str | None:
    if raw is None:
        return None
    value = str(raw).strip()
    if not value:
        return None
    return value[:128]


def _normalize_land_address(raw: Any) -> str:
    if raw is None:
        return ""
    return str(raw).strip()[:500]


def _parse_min_area(raw: Any) -> float:
    if raw is None or raw == "":
        return 0.0
    try:
        value = float(raw)
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail="minArea must be a number.") from exc
    if value < 0:
        raise HTTPException(status_code=400, detail="minArea must be >= 0.")
    return value


def _min_area_bucket(min_area: float) -> str:
    for lower, upper, label in MIN_AREA_BUCKETS:
        if lower <= min_area < upper:
            return label
    return MIN_AREA_BUCKET_OVERFLOW


def _normalize_search_term(raw: Any) -> str:
    text = str(raw or "").strip()
    if not text:
        return ""
    without_digits = DIGIT_RE.sub("", text)
    return without_digits.strip()[:200]


def _normalize_required_token(raw: Any, field_name: str) -> str:
    value = str(raw or "").strip()
    if not value:
        raise HTTPException(status_code=400, detail=f"{field_name} is required.")
    return value[:128]


def _normalize_optional_string(raw: Any, *, max_length: int) -> str | None:
    if raw is None:
        return None
    value = str(raw).strip()
    if not value:
        return None
    return value[:max_length]


def _parse_client_ts(raw: Any) -> str:
    if raw in (None, ""):
        now = datetime.now(UTC)
        return now.strftime("%Y-%m-%d %H:%M:%S")
    try:
        ts = float(raw)
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail="clientTs must be unix timestamp seconds.") from exc

    event_dt = datetime.fromtimestamp(ts, tz=UTC)
    now = datetime.now(UTC)
    # Clamp grossly skewed client clock values into a safe window.
    if event_dt > now + timedelta(minutes=5):
        event_dt = now
    if event_dt < now - timedelta(days=7):
        event_dt = now - timedelta(days=7)
    return event_dt.strftime("%Y-%m-%d %H:%M:%S")


def _is_bot_user_agent(user_agent: str) -> bool:
    normalized = user_agent.lower()
    return any(pattern in normalized for pattern in BOT_UA_PATTERNS)
