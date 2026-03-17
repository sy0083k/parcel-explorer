from app.db.connection import db_connection
from app.repositories import land_repository, poi_repository
from app.services import admin_stats_service


def test_admin_stats_service_get_web_stats(db_path: object) -> None:
    with db_connection() as conn:
        poi_repository.init_db(conn)
        poi_repository.insert_web_visit_event(
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
        poi_repository.insert_web_visit_event(
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
        poi_repository.insert_web_visit_event(
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

    result = admin_stats_service.get_web_stats(days=30)
    assert "summary" in result
    assert result["summary"]["totalVisitors"] >= 2
    assert result["summary"]["sessionCount"] >= 2


def test_admin_stats_service_get_dashboard_stats_includes_land_summary(db_path: object) -> None:
    with db_connection() as conn:
        poi_repository.init_db(conn)
        land_repository.delete_all(conn)
        land_repository.insert_land(
            conn,
            address="addr-1",
            land_type="답",
            area=11.0,
            adm_property="Y",
            gen_property="N",
            contact="010",
        )
        land_repository.insert_land(
            conn,
            address="addr-2",
            land_type="전",
            area=15.0,
            adm_property="Y",
            gen_property="N",
            contact="010",
        )
        missing = list(land_repository.fetch_missing_geom(conn))
        assert len(missing) == 2
        first_id, _ = missing[0]
        land_repository.update_geom(conn, first_id, '{"type":"Point","coordinates":[127,36]}')
        conn.commit()

    payload = admin_stats_service.get_dashboard_stats()
    assert payload["landSummary"]["totalLands"] == 2
    assert payload["landSummary"]["missingGeomLands"] == 1
