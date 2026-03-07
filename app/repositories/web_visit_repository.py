import sqlite3
from collections.abc import Sequence


def _placeholders(values: Sequence[str]) -> str:
    if not values:
        raise ValueError("values must not be empty")
    return ",".join("?" for _ in values)


def _ensure_web_visit_columns(conn: sqlite3.Connection) -> None:
    cursor = conn.cursor()
    columns = {row[1] for row in cursor.execute("PRAGMA table_info(web_visit_event)").fetchall()}

    add_columns: list[tuple[str, str]] = [
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
    ]

    for name, spec in add_columns:
        if name in columns:
            continue
        cursor.execute(f"ALTER TABLE web_visit_event ADD COLUMN {name} {spec}")


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
    _ensure_web_visit_columns(conn)
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
    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_web_visit_referrer_occurred
            ON web_visit_event (referrer_domain, occurred_at)
        """
    )
    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_web_visit_device_browser_occurred
            ON web_visit_event (device_type, browser_family, occurred_at)
        """
    )
    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_web_visit_utm_source_occurred
            ON web_visit_event (utm_source, occurred_at)
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


def fetch_web_total_visitors(conn: sqlite3.Connection, *, page_paths: Sequence[str]) -> int:
    cursor = conn.cursor()
    placeholders = _placeholders(page_paths)
    cursor.execute(
        f"""
        SELECT COUNT(DISTINCT anon_id)
          FROM web_visit_event
         WHERE page_path IN ({placeholders})
           AND is_bot = 0
        """,
        tuple(page_paths),
    )
    row = cursor.fetchone()
    return int(row[0] or 0) if row else 0


def fetch_web_daily_visitors(
    conn: sqlite3.Connection,
    *,
    page_paths: Sequence[str],
    since_utc: str,
    until_utc: str,
) -> int:
    cursor = conn.cursor()
    placeholders = _placeholders(page_paths)
    params = [*page_paths, since_utc, until_utc]
    cursor.execute(
        f"""
        SELECT COUNT(DISTINCT anon_id)
          FROM web_visit_event
         WHERE page_path IN ({placeholders})
           AND is_bot = 0
           AND occurred_at >= ?
           AND occurred_at < ?
        """,
        tuple(params),
    )
    row = cursor.fetchone()
    return int(row[0] or 0) if row else 0


def fetch_web_session_durations_seconds(
    conn: sqlite3.Connection,
    *,
    page_paths: Sequence[str],
    since_utc: str,
) -> Sequence[sqlite3.Row]:
    cursor = conn.cursor()
    placeholders = _placeholders(page_paths)
    params = [*page_paths, since_utc]
    cursor.execute(
        f"""
        SELECT
            session_id,
            (MAX(strftime('%s', occurred_at)) - MIN(strftime('%s', occurred_at))) AS duration_seconds,
            DATE(datetime(MAX(occurred_at), '+9 hours')) AS kst_date
          FROM web_visit_event
         WHERE page_path IN ({placeholders})
           AND is_bot = 0
           AND occurred_at >= ?
         GROUP BY session_id
         ORDER BY kst_date ASC
        """,
        tuple(params),
    )
    return cursor.fetchall()


def fetch_web_daily_unique_visitors_trend(
    conn: sqlite3.Connection,
    *,
    page_paths: Sequence[str],
    since_utc: str,
) -> Sequence[sqlite3.Row]:
    cursor = conn.cursor()
    placeholders = _placeholders(page_paths)
    params = [*page_paths, since_utc]
    cursor.execute(
        f"""
        SELECT
            DATE(datetime(occurred_at, '+9 hours')) AS date,
            COUNT(DISTINCT anon_id) AS visitors
          FROM web_visit_event
         WHERE page_path IN ({placeholders})
           AND is_bot = 0
           AND occurred_at >= ?
         GROUP BY DATE(datetime(occurred_at, '+9 hours'))
         ORDER BY DATE(datetime(occurred_at, '+9 hours')) ASC
        """,
        tuple(params),
    )
    return cursor.fetchall()


def fetch_top_referrer_domains(
    conn: sqlite3.Connection,
    *,
    since_utc: str,
    limit: int,
) -> Sequence[sqlite3.Row]:
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT referrer_domain, COUNT(*) AS count
          FROM web_visit_event
         WHERE is_bot = 0
           AND occurred_at >= ?
           AND referrer_domain IS NOT NULL
           AND referrer_domain != ''
         GROUP BY referrer_domain
         ORDER BY count DESC, referrer_domain ASC
         LIMIT ?
        """,
        (since_utc, limit),
    )
    return cursor.fetchall()


def fetch_top_utm_sources(
    conn: sqlite3.Connection,
    *,
    since_utc: str,
    limit: int,
) -> Sequence[sqlite3.Row]:
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT utm_source, COUNT(*) AS count
          FROM web_visit_event
         WHERE is_bot = 0
           AND occurred_at >= ?
           AND utm_source IS NOT NULL
           AND utm_source != ''
         GROUP BY utm_source
         ORDER BY count DESC, utm_source ASC
         LIMIT ?
        """,
        (since_utc, limit),
    )
    return cursor.fetchall()


def fetch_top_utm_campaigns(
    conn: sqlite3.Connection,
    *,
    since_utc: str,
    limit: int,
) -> Sequence[sqlite3.Row]:
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT utm_campaign, COUNT(*) AS count
          FROM web_visit_event
         WHERE is_bot = 0
           AND occurred_at >= ?
           AND utm_campaign IS NOT NULL
           AND utm_campaign != ''
         GROUP BY utm_campaign
         ORDER BY count DESC, utm_campaign ASC
         LIMIT ?
        """,
        (since_utc, limit),
    )
    return cursor.fetchall()


def fetch_device_breakdown(
    conn: sqlite3.Connection,
    *,
    since_utc: str,
) -> Sequence[sqlite3.Row]:
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT device_type, COUNT(*) AS count
          FROM web_visit_event
         WHERE is_bot = 0
           AND occurred_at >= ?
           AND device_type IS NOT NULL
           AND device_type != ''
         GROUP BY device_type
         ORDER BY count DESC, device_type ASC
        """,
        (since_utc,),
    )
    return cursor.fetchall()


def fetch_browser_breakdown(
    conn: sqlite3.Connection,
    *,
    since_utc: str,
) -> Sequence[sqlite3.Row]:
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT browser_family, COUNT(*) AS count
          FROM web_visit_event
         WHERE is_bot = 0
           AND occurred_at >= ?
           AND browser_family IS NOT NULL
           AND browser_family != ''
         GROUP BY browser_family
         ORDER BY count DESC, browser_family ASC
        """,
        (since_utc,),
    )
    return cursor.fetchall()


def fetch_top_page_paths(
    conn: sqlite3.Connection,
    *,
    since_utc: str,
    limit: int,
) -> Sequence[sqlite3.Row]:
    cursor = conn.cursor()
    cursor.execute(
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
    return cursor.fetchall()


def fetch_channel_breakdown(
    conn: sqlite3.Connection,
    *,
    since_utc: str,
) -> Sequence[sqlite3.Row]:
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT
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
            END AS channel,
            COUNT(*) AS count
          FROM web_visit_event
         WHERE is_bot = 0
           AND occurred_at >= ?
         GROUP BY channel
         ORDER BY count DESC, channel ASC
        """,
        (since_utc,),
    )
    return cursor.fetchall()
