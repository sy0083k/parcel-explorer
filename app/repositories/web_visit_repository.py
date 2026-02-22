import sqlite3
from typing import Sequence


def init_web_visit_schema(conn: sqlite3.Connection) -> None:
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
    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_web_visit_page_occurred
            ON web_visit_event (page_path, occurred_at)
        """
    )
    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_web_visit_anon_occurred
            ON web_visit_event (anon_id, occurred_at)
        """
    )
    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_web_visit_session_occurred
            ON web_visit_event (session_id, occurred_at)
        """
    )
    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_web_visit_event_type_occurred
            ON web_visit_event (event_type, occurred_at)
        """
    )


def insert_web_visit_event(
    conn: sqlite3.Connection,
    *,
    anon_id: str,
    session_id: str,
    event_type: str,
    page_path: str,
    occurred_at: str,
    client_tz: str | None,
    user_agent: str | None,
    is_bot: bool,
) -> None:
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO web_visit_event (
            anon_id, session_id, event_type, page_path, occurred_at, client_tz, user_agent, is_bot
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (anon_id, session_id, event_type, page_path, occurred_at, client_tz, user_agent, 1 if is_bot else 0),
    )


def fetch_web_total_visitors(conn: sqlite3.Connection, *, page_path: str) -> int:
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT COUNT(DISTINCT anon_id)
          FROM web_visit_event
         WHERE page_path = ?
           AND is_bot = 0
        """,
        (page_path,),
    )
    row = cursor.fetchone()
    return int(row[0] or 0) if row else 0


def fetch_web_daily_visitors(conn: sqlite3.Connection, *, page_path: str, since_utc: str, until_utc: str) -> int:
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT COUNT(DISTINCT anon_id)
          FROM web_visit_event
         WHERE page_path = ?
           AND is_bot = 0
           AND occurred_at >= ?
           AND occurred_at < ?
        """,
        (page_path, since_utc, until_utc),
    )
    row = cursor.fetchone()
    return int(row[0] or 0) if row else 0


def fetch_web_session_durations_seconds(
    conn: sqlite3.Connection,
    *,
    page_path: str,
    since_utc: str,
) -> Sequence[sqlite3.Row]:
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT
            session_id,
            (MAX(strftime('%s', occurred_at)) - MIN(strftime('%s', occurred_at))) AS duration_seconds,
            DATE(datetime(MAX(occurred_at), '+9 hours')) AS kst_date
          FROM web_visit_event
         WHERE page_path = ?
           AND is_bot = 0
           AND occurred_at >= ?
         GROUP BY session_id
         ORDER BY kst_date ASC
        """,
        (page_path, since_utc),
    )
    return cursor.fetchall()


def fetch_web_daily_unique_visitors_trend(
    conn: sqlite3.Connection,
    *,
    page_path: str,
    since_utc: str,
) -> Sequence[sqlite3.Row]:
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT
            DATE(datetime(occurred_at, '+9 hours')) AS date,
            COUNT(DISTINCT anon_id) AS visitors
          FROM web_visit_event
         WHERE page_path = ?
           AND is_bot = 0
           AND occurred_at >= ?
         GROUP BY DATE(datetime(occurred_at, '+9 hours'))
         ORDER BY DATE(datetime(occurred_at, '+9 hours')) ASC
        """,
        (page_path, since_utc),
    )
    return cursor.fetchall()
