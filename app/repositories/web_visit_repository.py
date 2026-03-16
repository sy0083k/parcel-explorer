import sqlite3
from collections.abc import Sequence

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

CHANNEL_CASE_SQL = """
CASE
    WHEN utm_medium IS NOT NULL AND utm_medium != '' THEN
        CASE
            WHEN lower(utm_medium) LIKE '%email%' OR lower(utm_medium) LIKE '%newsletter%' THEN 'email'
            WHEN lower(utm_medium) LIKE '%social%' THEN 'social'
            WHEN lower(utm_medium) LIKE '%affiliate%' THEN 'affiliate'
            WHEN lower(utm_medium) LIKE '%display%' OR lower(utm_medium) LIKE '%cpc%'
                 OR lower(utm_medium) LIKE '%ppc%' OR lower(utm_medium) LIKE '%paid%'
                 OR lower(utm_medium) LIKE '%ads%' THEN 'paid'
            ELSE 'campaign'
        END
    WHEN referrer_domain IS NULL OR referrer_domain = '' THEN 'direct'
    WHEN lower(referrer_domain) LIKE '%google.%' OR lower(referrer_domain) LIKE '%bing.%'
         OR lower(referrer_domain) LIKE '%naver.%' OR lower(referrer_domain) LIKE '%daum.%'
         OR lower(referrer_domain) LIKE '%yahoo.%' THEN 'organic_search'
    ELSE 'referral'
END
"""


def _placeholders(values: Sequence[str]) -> str:
    if not values:
        raise ValueError("values must not be empty")
    return ",".join("?" for _ in values)


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


def insert_web_visit_event(
    conn: sqlite3.Connection,
    *,
    anon_id: str,
    session_id: str,
    event_type: str,
    page_path: str,
    occurred_at: str,
    is_bot: bool,
    page_query: str | None = None,
    client_tz: str | None = None,
    client_lang: str | None = None,
    platform: str | None = None,
    user_agent: str | None = None,
    referrer_url: str | None = None,
    referrer_domain: str | None = None,
    utm_source: str | None = None,
    utm_medium: str | None = None,
    utm_campaign: str | None = None,
    utm_term: str | None = None,
    utm_content: str | None = None,
    screen_width: int | None = None,
    screen_height: int | None = None,
    viewport_width: int | None = None,
    viewport_height: int | None = None,
    browser_family: str = "other",
    device_type: str = "unknown",
    os_family: str = "other",
) -> None:
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO web_visit_event (
            anon_id,
            session_id,
            event_type,
            page_path,
            page_query,
            occurred_at,
            client_tz,
            client_lang,
            platform,
            user_agent,
            is_bot,
            referrer_url,
            referrer_domain,
            utm_source,
            utm_medium,
            utm_campaign,
            utm_term,
            utm_content,
            screen_width,
            screen_height,
            viewport_width,
            viewport_height,
            browser_family,
            device_type,
            os_family
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            anon_id,
            session_id,
            event_type,
            page_path,
            page_query,
            occurred_at,
            client_tz,
            client_lang,
            platform,
            user_agent,
            1 if is_bot else 0,
            referrer_url,
            referrer_domain,
            utm_source,
            utm_medium,
            utm_campaign,
            utm_term,
            utm_content,
            screen_width,
            screen_height,
            viewport_width,
            viewport_height,
            browser_family,
            device_type,
            os_family,
        ),
    )


def _fetch_scalar(
    conn: sqlite3.Connection,
    query: str,
    params: Sequence[object],
) -> int:
    cursor = conn.cursor()
    cursor.execute(query, tuple(params))
    row = cursor.fetchone()
    return int(row[0] or 0) if row else 0


def _fetch_rows(
    conn: sqlite3.Connection,
    query: str,
    params: Sequence[object],
) -> Sequence[sqlite3.Row]:
    cursor = conn.cursor()
    cursor.execute(query, tuple(params))
    return cursor.fetchall()


def _page_path_filter_clause(page_paths: Sequence[str]) -> tuple[str, tuple[object, ...]]:
    placeholders = _placeholders(page_paths)
    return f"page_path IN ({placeholders})", tuple(page_paths)


def fetch_web_total_visitors(conn: sqlite3.Connection, *, page_paths: Sequence[str]) -> int:
    page_filter, page_params = _page_path_filter_clause(page_paths)
    return _fetch_scalar(
        conn,
        f"""
        SELECT COUNT(DISTINCT anon_id)
          FROM web_visit_event
         WHERE {page_filter}
           AND is_bot = 0
        """,
        page_params,
    )


def fetch_web_daily_visitors(
    conn: sqlite3.Connection,
    *,
    page_paths: Sequence[str],
    since_utc: str,
    until_utc: str,
) -> int:
    page_filter, page_params = _page_path_filter_clause(page_paths)
    return _fetch_scalar(
        conn,
        f"""
        SELECT COUNT(DISTINCT anon_id)
          FROM web_visit_event
         WHERE {page_filter}
           AND is_bot = 0
           AND occurred_at >= ?
           AND occurred_at < ?
        """,
        (*page_params, since_utc, until_utc),
    )


def fetch_web_session_durations_seconds(
    conn: sqlite3.Connection,
    *,
    page_paths: Sequence[str],
    since_utc: str,
) -> Sequence[sqlite3.Row]:
    page_filter, page_params = _page_path_filter_clause(page_paths)
    return _fetch_rows(
        conn,
        f"""
        SELECT
            session_id,
            (MAX(strftime('%s', occurred_at)) - MIN(strftime('%s', occurred_at))) AS duration_seconds,
            DATE(datetime(MAX(occurred_at), '+9 hours')) AS kst_date
          FROM web_visit_event
         WHERE {page_filter}
           AND is_bot = 0
           AND occurred_at >= ?
         GROUP BY session_id
         ORDER BY kst_date ASC
        """,
        (*page_params, since_utc),
    )


def fetch_web_daily_unique_visitors_trend(
    conn: sqlite3.Connection,
    *,
    page_paths: Sequence[str],
    since_utc: str,
) -> Sequence[sqlite3.Row]:
    page_filter, page_params = _page_path_filter_clause(page_paths)
    return _fetch_rows(
        conn,
        f"""
        SELECT
            DATE(datetime(occurred_at, '+9 hours')) AS date,
            COUNT(DISTINCT anon_id) AS visitors
          FROM web_visit_event
         WHERE {page_filter}
           AND is_bot = 0
           AND occurred_at >= ?
         GROUP BY DATE(datetime(occurred_at, '+9 hours'))
         ORDER BY DATE(datetime(occurred_at, '+9 hours')) ASC
        """,
        (*page_params, since_utc),
    )


def _fetch_grouped_breakdown(
    conn: sqlite3.Connection,
    *,
    key_column: str,
    since_utc: str,
    limit: int | None = None,
) -> Sequence[sqlite3.Row]:
    limit_clause = "LIMIT ?" if limit is not None else ""
    params: list[object] = [since_utc]
    if limit is not None:
        params.append(limit)
    return _fetch_rows(
        conn,
        f"""
        SELECT {key_column}, COUNT(*) AS count
          FROM web_visit_event
         WHERE is_bot = 0
           AND occurred_at >= ?
           AND {key_column} IS NOT NULL
           AND {key_column} != ''
         GROUP BY {key_column}
         ORDER BY count DESC, {key_column} ASC
         {limit_clause}
        """,
        params,
    )


def fetch_top_referrer_domains(
    conn: sqlite3.Connection,
    *,
    since_utc: str,
    limit: int,
) -> Sequence[sqlite3.Row]:
    return _fetch_grouped_breakdown(conn, key_column="referrer_domain", since_utc=since_utc, limit=limit)


def fetch_top_utm_sources(
    conn: sqlite3.Connection,
    *,
    since_utc: str,
    limit: int,
) -> Sequence[sqlite3.Row]:
    return _fetch_grouped_breakdown(conn, key_column="utm_source", since_utc=since_utc, limit=limit)


def fetch_top_utm_campaigns(
    conn: sqlite3.Connection,
    *,
    since_utc: str,
    limit: int,
) -> Sequence[sqlite3.Row]:
    return _fetch_grouped_breakdown(conn, key_column="utm_campaign", since_utc=since_utc, limit=limit)


def fetch_device_breakdown(
    conn: sqlite3.Connection,
    *,
    since_utc: str,
) -> Sequence[sqlite3.Row]:
    return _fetch_grouped_breakdown(conn, key_column="device_type", since_utc=since_utc)


def fetch_browser_breakdown(
    conn: sqlite3.Connection,
    *,
    since_utc: str,
) -> Sequence[sqlite3.Row]:
    return _fetch_grouped_breakdown(conn, key_column="browser_family", since_utc=since_utc)


def fetch_top_page_paths(
    conn: sqlite3.Connection,
    *,
    since_utc: str,
    limit: int,
) -> Sequence[sqlite3.Row]:
    return _fetch_rows(
        conn,
        """
        SELECT page_path, COUNT(*) AS count
          FROM web_visit_event
         WHERE is_bot = 0
           AND occurred_at >= ?
         GROUP BY page_path
         ORDER BY count DESC, page_path ASC
         LIMIT ?
        """,
        (since_utc, limit),
    )


def fetch_channel_breakdown(
    conn: sqlite3.Connection,
    *,
    since_utc: str,
) -> Sequence[sqlite3.Row]:
    return _fetch_rows(
        conn,
        f"""
        SELECT
            {CHANNEL_CASE_SQL} AS channel,
            COUNT(*) AS count
          FROM web_visit_event
         WHERE is_bot = 0
           AND occurred_at >= ?
         GROUP BY channel
         ORDER BY count DESC, channel ASC
        """,
        (since_utc,),
    )
