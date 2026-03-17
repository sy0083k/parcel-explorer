from app.services import web_stats_service
from app.services.service_models import WebVisitContext, WebVisitEventCommand
from app.services.web_stats_types import WebStatsQueryResult, WebStatsWindow


def test_record_web_visit_event_delegates_to_ingest(monkeypatch) -> None:
    recorded: list[WebVisitEventCommand] = []

    monkeypatch.setattr(web_stats_service.ingest, "record_web_visit_event", recorded.append)

    command = WebVisitEventCommand(
        event_type="visit_start",
        anon_id=" anon-1 ",
        session_id=" session-1 ",
        page_path="/",
        page_query="?utm_source=google",
        client_ts=1763596800,
        client_tz=" Asia/Seoul ",
        client_lang=" ko-KR ",
        platform=" iPhone ",
        referrer_url="https://Example.com/search?q=test",
        screen_width=1170,
        screen_height=2532,
        viewport_width=430,
        viewport_height=932,
        context=WebVisitContext(
            user_agent=(
                "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
                "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"
            ),
            allowed_web_track_paths=("/",),
        ),
    )

    web_stats_service.record_web_visit_event(command)

    assert recorded == [command]


def test_get_web_stats_formats_response_from_repository_rows(
    monkeypatch,
) -> None:
    stats_window = WebStatsWindow(
        since_utc="2026-02-19 00:00:00",
        today_utc_start="2026-02-20 00:00:00",
        today_utc_end="2026-02-21 00:00:00",
    )
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

    monkeypatch.setattr(web_stats_service, "_build_web_stats_window", lambda _days: stats_window)
    monkeypatch.setattr(
        web_stats_service,
        "_fetch_web_stats_query_result",
        lambda _window, *, allowed_paths: query_result,
    )

    payload = web_stats_service.get_web_stats(days=30, allowed_paths=("/",))

    assert payload["summary"] == {
        "dailyVisitors": 2,
        "totalVisitors": 3,
        "avgDwellMinutes": 6.0,
        "sessionCount": 2,
    }
    assert payload["dailyTrend"] == [
        {"date": "2026-02-20", "visitors": 2, "sessions": 2, "avgDwellMinutes": 6.0}
    ]
    assert payload["topReferrers"] == [{"domain": "google.com", "count": 2}]
    assert payload["channelBreakdown"] == [{"channel": "social", "count": 1}]
