from app.services import web_stats_presenter
from app.services.web_stats_types import WebStatsQueryResult


def test_web_stats_presenter_summarizes_sessions() -> None:
    summary = web_stats_presenter.summarize_sessions(
        [
            {"session_id": "s-1", "duration_seconds": 600, "kst_date": "2026-02-20"},
            {"session_id": "s-2", "duration_seconds": 120, "kst_date": "2026-02-20"},
        ]
    )
    assert summary.session_count == 2
    assert summary.avg_dwell_minutes == 6.0


def test_web_stats_presenter_builds_response() -> None:
    query_result = WebStatsQueryResult(
        total_visitors=3,
        daily_visitors=2,
        session_rows=[
            {"session_id": "s-1", "duration_seconds": 600, "kst_date": "2026-02-20"},
            {"session_id": "s-2", "duration_seconds": 120, "kst_date": "2026-02-20"},
        ],
        visitor_trend_rows=[{"date": "2026-02-20", "visitors": 2}],
        top_referrers=[{"referrer_domain": "google.com", "count": 2}],
        top_utm_sources=[{"utm_source": "newsletter", "count": 1}],
        top_utm_campaigns=[{"utm_campaign": "spring", "count": 1}],
        device_breakdown=[{"device_type": "mobile", "count": 2}],
        browser_breakdown=[{"browser_family": "chrome", "count": 1}],
        top_page_paths=[{"page_path": "/", "count": 2}],
        channel_breakdown=[{"channel": "social", "count": 1}],
    )
    summary = web_stats_presenter.summarize_sessions(query_result.session_rows)
    payload = web_stats_presenter.build_web_stats_response(query_result, summary)
    assert payload["summary"] == {
        "dailyVisitors": 2,
        "totalVisitors": 3,
        "avgDwellMinutes": 6.0,
        "sessionCount": 2,
    }
    assert payload["dailyTrend"] == [
        {"date": "2026-02-20", "visitors": 2, "sessions": 2, "avgDwellMinutes": 6.0}
    ]
