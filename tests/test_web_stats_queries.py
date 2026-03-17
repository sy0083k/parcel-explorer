from app.services import web_stats_queries
from app.services.web_stats_types import WebStatsWindow


def test_web_stats_queries_rows_to_dicts() -> None:
    rows = [{"date": "2026-02-20", "visitors": 2}]
    assert web_stats_queries.rows_to_dicts(rows) == rows


def test_web_stats_queries_builds_time_window() -> None:
    window = web_stats_queries.build_web_stats_window(30)
    assert isinstance(window, WebStatsWindow)
    assert len(window.since_utc) == 19
    assert len(window.today_utc_start) == 19
    assert len(window.today_utc_end) == 19
