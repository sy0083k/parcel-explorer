from app.services import stats_service
from app.db.connection import db_connection
from app.repositories import idle_land_repository


def test_stats_service_bucket_helpers() -> None:
    assert stats_service._min_area_bucket(0) == "0-99"
    assert stats_service._min_area_bucket(100) == "100-199"
    assert stats_service._min_area_bucket(550) == "500-999"
    assert stats_service._min_area_bucket(1000) == "1000+"


def test_stats_service_normalize_search_term() -> None:
    assert stats_service._normalize_search_term("  성연면123  ") == "성연면"
    assert stats_service._normalize_search_term("12345") == ""
    assert stats_service._normalize_search_term(" 성연면 2지구 ") == "성연면 지구"


def test_stats_service_web_bot_detection() -> None:
    assert stats_service._is_bot_user_agent("Mozilla/5.0 (compatible; Googlebot/2.1)") is True
    assert stats_service._is_bot_user_agent("Mozilla/5.0 (Windows NT 10.0; Win64; x64)") is False


def test_stats_service_get_web_stats(db_path: object) -> None:
    with db_connection() as conn:
        idle_land_repository.init_db(conn)
        idle_land_repository.insert_web_visit_event(
            conn,
            anon_id="anon-a",
            session_id="session-a",
            event_type="visit_start",
            page_path="/",
            occurred_at="2026-02-20 00:00:00",
            client_tz="Asia/Seoul",
            user_agent="Mozilla/5.0",
            is_bot=False,
        )
        idle_land_repository.insert_web_visit_event(
            conn,
            anon_id="anon-a",
            session_id="session-a",
            event_type="heartbeat",
            page_path="/",
            occurred_at="2026-02-20 00:05:00",
            client_tz="Asia/Seoul",
            user_agent="Mozilla/5.0",
            is_bot=False,
        )
        idle_land_repository.insert_web_visit_event(
            conn,
            anon_id="anon-b",
            session_id="session-b",
            event_type="visit_start",
            page_path="/",
            occurred_at="2026-02-20 01:00:00",
            client_tz="Asia/Seoul",
            user_agent="Mozilla/5.0",
            is_bot=False,
        )
        conn.commit()

    result = stats_service.get_web_stats(days=30)
    assert "summary" in result
    assert result["summary"]["totalVisitors"] >= 2
    assert result["summary"]["sessionCount"] >= 2
