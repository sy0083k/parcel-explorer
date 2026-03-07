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

        assert web_visit_repository.fetch_web_total_visitors(conn, page_paths=("/",)) == 1
        sessions = web_visit_repository.fetch_web_session_durations_seconds(
            conn,
            page_paths=("/",),
            since_utc="2026-02-19 00:00:00",
        )
        assert len(sessions) == 1
        assert int(sessions[0]["duration_seconds"]) == 600


def test_web_visit_repository_schema_upgrade_is_idempotent(db_path: object) -> None:
    with db_connection(row_factory=True) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS web_visit_event (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                anon_id TEXT NOT NULL,
                session_id TEXT NOT NULL,
                event_type TEXT NOT NULL,
                page_path TEXT NOT NULL,
                occurred_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                client_tz TEXT,
                user_agent TEXT,
                is_bot INTEGER NOT NULL DEFAULT 0
            )
            """
        )
        conn.commit()

        web_visit_repository.init_web_visit_schema(conn)
        web_visit_repository.init_web_visit_schema(conn)
        conn.commit()

        columns = {row["name"] for row in cursor.execute("PRAGMA table_info(web_visit_event)").fetchall()}
        assert "referrer_domain" in columns
        assert "utm_source" in columns
        assert "page_query" in columns
        assert "browser_family" in columns
