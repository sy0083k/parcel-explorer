import pytest

from app.db.connection import db_connection
from app.repositories import web_visit_repository
from app.services import web_stats_service
from app.services.service_models import RequestMetadata, WebVisitEventCommand


def test_web_stats_service_helpers() -> None:
    assert web_stats_service.is_bot_user_agent("Mozilla/5.0 (compatible; Googlebot/2.1)") is True
    assert web_stats_service.is_bot_user_agent("Mozilla/5.0 (Windows NT 10.0; Win64; x64)") is False
    assert web_stats_service.normalize_required_token(" anon-1 ", "anonId") == "anon-1"
    assert web_stats_service.normalize_optional_string(" Asia/Seoul ", max_length=64) == "Asia/Seoul"
    assert web_stats_service.classify_device_type("Mozilla/5.0 (iPhone)", is_bot=False) == "mobile"
    assert web_stats_service.classify_browser_family("Mozilla/5.0 Chrome/130.0.0.0") == "chrome"
    assert web_stats_service.classify_os_family("Mozilla/5.0 (Windows NT 10.0; Win64; x64)") == "windows"


def test_web_stats_service_parse_client_ts_returns_sql_datetime() -> None:
    parsed = web_stats_service.parse_client_ts(1763596800)
    assert len(parsed) == 19
    assert parsed.count(":") == 2


def test_web_stats_service_page_path_and_referrer_normalization() -> None:
    assert web_stats_service.normalize_page_path("/readme", allowed_paths=("/", "/readme")) == "/readme"
    assert web_stats_service.normalize_query_string("?utm_source=google", max_length=1024) == "utm_source=google"
    assert web_stats_service.normalize_referrer_url("https://example.com/path?a=1#x") == "https://example.com/path"
    assert (
        web_stats_service.normalize_referrer_domain(None, "https://Example.COM/path")
        == "example.com"
    )


def test_record_web_visit_event_persists_normalized_and_derived_fields(
    db_path: object,
) -> None:
    with db_connection(row_factory=True) as conn:
        web_visit_repository.init_web_visit_schema(conn)
        conn.commit()

    web_stats_service.record_web_visit_event(
        WebVisitEventCommand(
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
            metadata=RequestMetadata(
                user_agent=(
                    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
                    "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"
                ),
                allowed_web_track_paths=("/",),
            ),
        )
    )

    with db_connection(row_factory=True) as conn:
        row = conn.execute("SELECT * FROM web_visit_event").fetchone()

    assert row is not None
    assert row["anon_id"] == "anon-1"
    assert row["session_id"] == "session-1"
    assert row["page_query"] == "utm_source=google"
    assert row["client_tz"] == "Asia/Seoul"
    assert row["referrer_url"] == "https://Example.com/search"
    assert row["referrer_domain"] == "example.com"
    assert row["browser_family"] == "safari"
    assert row["device_type"] == "mobile"
    assert row["os_family"] == "macos"


@pytest.mark.unit
def test_get_web_stats_formats_response_from_repository_rows(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    stats_window = web_stats_service.WebStatsWindow(
        since_utc="2026-02-19 00:00:00",
        today_utc_start="2026-02-20 00:00:00",
        today_utc_end="2026-02-21 00:00:00",
    )
    query_result = web_stats_service.WebStatsQueryResult(
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
