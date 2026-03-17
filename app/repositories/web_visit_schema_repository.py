import sqlite3

SCHEMA_COLUMNS: tuple[tuple[str, str], ...] = (
    ("referrer_url", "TEXT"),
    ("referrer_domain", "TEXT"),
    ("utm_source", "TEXT"),
    ("utm_medium", "TEXT"),
    ("utm_campaign", "TEXT"),
    ("utm_term", "TEXT"),
    ("utm_content", "TEXT"),
    ("page_query", "TEXT"),
    ("client_lang", "TEXT"),
    ("platform", "TEXT"),
    ("screen_width", "INTEGER"),
    ("screen_height", "INTEGER"),
    ("viewport_width", "INTEGER"),
    ("viewport_height", "INTEGER"),
    ("browser_family", "TEXT"),
    ("device_type", "TEXT"),
    ("os_family", "TEXT"),
)

INDEX_STATEMENTS: tuple[str, ...] = (
    """
    CREATE INDEX IF NOT EXISTS idx_web_visit_page_occurred
        ON web_visit_event (page_path, occurred_at)
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_web_visit_anon_occurred
        ON web_visit_event (anon_id, occurred_at)
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_web_visit_session_occurred
        ON web_visit_event (session_id, occurred_at)
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_web_visit_event_type_occurred
        ON web_visit_event (event_type, occurred_at)
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_web_visit_referrer_occurred
        ON web_visit_event (referrer_domain, occurred_at)
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_web_visit_device_browser_occurred
        ON web_visit_event (device_type, browser_family, occurred_at)
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_web_visit_utm_source_occurred
        ON web_visit_event (utm_source, occurred_at)
    """,
)


def _get_columns(conn: sqlite3.Connection) -> set[str]:
    cursor = conn.cursor()
    return {row[1] for row in cursor.execute("PRAGMA table_info(web_visit_event)").fetchall()}


def _ensure_web_visit_columns(conn: sqlite3.Connection) -> None:
    existing_columns = _get_columns(conn)
    cursor = conn.cursor()
    for name, spec in SCHEMA_COLUMNS:
        if name in existing_columns:
            continue
        cursor.execute(f"ALTER TABLE web_visit_event ADD COLUMN {name} {spec}")


def _create_web_visit_table(conn: sqlite3.Connection) -> None:
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS web_visit_event (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            anon_id TEXT NOT NULL,
            session_id TEXT NOT NULL,
            event_type TEXT NOT NULL,
            page_path TEXT NOT NULL,
            page_query TEXT,
            occurred_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            client_tz TEXT,
            client_lang TEXT,
            platform TEXT,
            user_agent TEXT,
            is_bot INTEGER NOT NULL DEFAULT 0,
            referrer_url TEXT,
            referrer_domain TEXT,
            utm_source TEXT,
            utm_medium TEXT,
            utm_campaign TEXT,
            utm_term TEXT,
            utm_content TEXT,
            screen_width INTEGER,
            screen_height INTEGER,
            viewport_width INTEGER,
            viewport_height INTEGER,
            browser_family TEXT,
            device_type TEXT,
            os_family TEXT
        )
        """
    )


def _ensure_web_visit_indexes(conn: sqlite3.Connection) -> None:
    cursor = conn.cursor()
    for statement in INDEX_STATEMENTS:
        cursor.execute(statement)


def init_web_visit_schema(conn: sqlite3.Connection) -> None:
    _create_web_visit_table(conn)
    _ensure_web_visit_columns(conn)
    _ensure_web_visit_indexes(conn)
