from app.db.connection import db_connection
from app.repositories import web_visit_repository


def test_web_visit_repository_aggregates(db_path: object) -> None:
    with db_connection(row_factory=True) as conn:
        web_visit_repository.init_web_visit_schema(conn)
        web_visit_repository.insert_web_visit_event(
            conn,
            anon_id="anon-1",
            session_id="s-1",
            event_type="visit_start",
            page_path="/",
            occurred_at="2026-02-20 00:00:00",
            client_tz="Asia/Seoul",
            user_agent="Mozilla/5.0",
            is_bot=False,
        )
        web_visit_repository.insert_web_visit_event(
            conn,
            anon_id="anon-1",
            session_id="s-1",
            event_type="visit_end",
            page_path="/",
            occurred_at="2026-02-20 00:10:00",
            client_tz="Asia/Seoul",
            user_agent="Mozilla/5.0",
            is_bot=False,
        )
        conn.commit()

        assert web_visit_repository.fetch_web_total_visitors(conn, page_path="/") == 1
        sessions = web_visit_repository.fetch_web_session_durations_seconds(
            conn,
            page_path="/",
            since_utc="2026-02-19 00:00:00",
        )
        assert len(sessions) == 1
        assert int(sessions[0]["duration_seconds"]) == 600
