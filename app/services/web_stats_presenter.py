from __future__ import annotations

from typing import Any

from app.services.web_stats_types import SessionSummary, WebStatsQueryResult


def summarize_sessions(session_rows: list[dict[str, Any]]) -> SessionSummary:
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


def build_web_stats_response(
    query_result: WebStatsQueryResult,
    session_summary: SessionSummary,
) -> dict[str, Any]:
    daily_trend = build_daily_trend(
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


def build_daily_trend(
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
