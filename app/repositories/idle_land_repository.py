import sqlite3
from typing import Iterable, Sequence


def init_db(conn: sqlite3.Connection) -> None:
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS idle_land (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            address TEXT,
            land_type TEXT,
            area REAL,
            adm_property TEXT,
            gen_property TEXT,
            contact TEXT,
            geom TEXT
        )
        """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS geom_update_jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            status TEXT NOT NULL DEFAULT 'pending',
            attempts INTEGER NOT NULL DEFAULT 0,
            updated_count INTEGER NOT NULL DEFAULT 0,
            failed_count INTEGER NOT NULL DEFAULT 0,
            error_message TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS map_event_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_type TEXT NOT NULL,
            anon_id TEXT,
            land_address TEXT,
            region_name TEXT,
            min_area_value REAL,
            min_area_bucket TEXT,
            region_source TEXT NOT NULL DEFAULT 'derived_address',
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    _ensure_map_event_log_columns(conn)
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
        CREATE INDEX IF NOT EXISTS idx_map_event_type_created
            ON map_event_log (event_type, created_at)
        """
    )
    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_map_event_region
            ON map_event_log (event_type, region_name)
        """
    )
    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_map_event_min_area_bucket
            ON map_event_log (event_type, min_area_bucket)
        """
    )
    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_map_event_land_address
            ON map_event_log (event_type, land_address)
        """
    )
    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_map_event_land_anon
            ON map_event_log (event_type, land_address, anon_id)
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
    conn.commit()


def fetch_lands_with_geom(conn: sqlite3.Connection) -> Sequence[sqlite3.Row]:
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM idle_land WHERE geom IS NOT NULL")
    return cursor.fetchall()


def fetch_lands_with_geom_page(
    conn: sqlite3.Connection,
    *,
    after_id: int | None,
    limit: int,
) -> Sequence[sqlite3.Row]:
    cursor = conn.cursor()
    if after_id is None:
        cursor.execute("SELECT * FROM idle_land WHERE geom IS NOT NULL ORDER BY id LIMIT ?", (limit,))
    else:
        cursor.execute(
            "SELECT * FROM idle_land WHERE geom IS NOT NULL AND id > ? ORDER BY id LIMIT ?",
            (after_id, limit),
        )
    return cursor.fetchall()


def delete_all(conn: sqlite3.Connection) -> None:
    cursor = conn.cursor()
    cursor.execute("DELETE FROM idle_land")


def insert_land(
    conn: sqlite3.Connection,
    *,
    address: str,
    land_type: str,
    area: float,
    adm_property: str,
    gen_property: str,
    contact: str,
) -> None:
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO idle_land (address, land_type, area, adm_property, gen_property, contact, geom)
        VALUES (?,?,?,?,?,?,NULL)
        """,
        (
            address,
            land_type,
            area,
            adm_property,
            gen_property,
            contact,
        ),
    )


def fetch_missing_geom(conn: sqlite3.Connection, *, limit: int | None = None) -> Iterable[tuple[int, str]]:
    cursor = conn.cursor()
    if limit is None:
        cursor.execute("SELECT id, address FROM idle_land WHERE geom IS NULL ORDER BY id")
    else:
        cursor.execute("SELECT id, address FROM idle_land WHERE geom IS NULL ORDER BY id LIMIT ?", (limit,))
    return cursor.fetchall()


def update_geom(conn: sqlite3.Connection, item_id: int, geom: str) -> None:
    cursor = conn.cursor()
    cursor.execute("UPDATE idle_land SET geom = ? WHERE id = ?", (geom, item_id))


def count_missing_geom(conn: sqlite3.Connection) -> int:
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM idle_land WHERE geom IS NULL")
    row = cursor.fetchone()
    return int(row[0]) if row else 0


def create_geom_update_job(conn: sqlite3.Connection) -> int:
    cursor = conn.cursor()
    cursor.execute("INSERT INTO geom_update_jobs (status) VALUES ('pending')")
    return int(cursor.lastrowid)


def mark_geom_job_running(conn: sqlite3.Connection, job_id: int) -> None:
    cursor = conn.cursor()
    cursor.execute(
        """
        UPDATE geom_update_jobs
           SET status = 'running',
               attempts = attempts + 1,
               updated_at = CURRENT_TIMESTAMP
         WHERE id = ?
        """,
        (job_id,),
    )


def mark_geom_job_done(conn: sqlite3.Connection, job_id: int, *, updated_count: int, failed_count: int) -> None:
    cursor = conn.cursor()
    cursor.execute(
        """
        UPDATE geom_update_jobs
           SET status = 'done',
               updated_count = ?,
               failed_count = ?,
               error_message = NULL,
               updated_at = CURRENT_TIMESTAMP
         WHERE id = ?
        """,
        (updated_count, failed_count, job_id),
    )


def mark_geom_job_failed(
    conn: sqlite3.Connection,
    job_id: int,
    *,
    updated_count: int,
    failed_count: int,
    error_message: str,
) -> None:
    cursor = conn.cursor()
    cursor.execute(
        """
        UPDATE geom_update_jobs
           SET status = 'failed',
               updated_count = ?,
               failed_count = ?,
               error_message = ?,
               updated_at = CURRENT_TIMESTAMP
         WHERE id = ?
        """,
        (updated_count, failed_count, error_message, job_id),
    )


def insert_map_event(
    conn: sqlite3.Connection,
    *,
    event_type: str,
    anon_id: str | None,
    land_address: str | None = None,
    region_name: str | None = None,
    min_area_value: float | None = None,
    min_area_bucket: str | None = None,
    region_source: str = "derived_address",
) -> None:
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO map_event_log (
            event_type, anon_id, land_address, region_name, min_area_value, min_area_bucket, region_source
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (event_type, anon_id, land_address, region_name, min_area_value, min_area_bucket, region_source),
    )


def fetch_event_summary(conn: sqlite3.Connection) -> sqlite3.Row:
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT
            SUM(CASE WHEN event_type = 'search' THEN 1 ELSE 0 END) AS search_count,
            SUM(CASE WHEN event_type = 'land_click' THEN 1 ELSE 0 END) AS click_count,
            COUNT(DISTINCT CASE WHEN anon_id IS NOT NULL AND anon_id != '' THEN anon_id END) AS unique_session_count
        FROM map_event_log
        """
    )
    return cursor.fetchone()


def fetch_top_regions(conn: sqlite3.Connection, *, limit: int) -> Sequence[sqlite3.Row]:
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT region_name, COUNT(*) AS count
          FROM map_event_log
         WHERE event_type = 'search'
           AND region_source = 'user_input'
           AND region_name IS NOT NULL
           AND region_name != ''
         GROUP BY region_name
         ORDER BY count DESC, region_name ASC
         LIMIT ?
        """,
        (limit,),
    )
    return cursor.fetchall()


def _ensure_map_event_log_columns(conn: sqlite3.Connection) -> None:
    cursor = conn.cursor()
    columns = cursor.execute("PRAGMA table_info(map_event_log)").fetchall()
    column_names = {str(row[1]) for row in columns}
    if "region_source" not in column_names:
        cursor.execute(
            "ALTER TABLE map_event_log ADD COLUMN region_source TEXT NOT NULL DEFAULT 'derived_address'"
        )


def fetch_top_min_area_buckets(conn: sqlite3.Connection, *, limit: int) -> Sequence[sqlite3.Row]:
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT min_area_bucket, COUNT(*) AS count
          FROM map_event_log
         WHERE event_type = 'search'
           AND min_area_bucket IS NOT NULL
           AND min_area_bucket != ''
         GROUP BY min_area_bucket
         ORDER BY count DESC, min_area_bucket ASC
         LIMIT ?
        """,
        (limit,),
    )
    return cursor.fetchall()


def fetch_top_clicked_lands(conn: sqlite3.Connection, *, limit: int) -> Sequence[sqlite3.Row]:
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT
            land_address,
            COUNT(*) AS click_count,
            COUNT(DISTINCT CASE WHEN anon_id IS NOT NULL AND anon_id != '' THEN anon_id END) AS unique_session_count
          FROM map_event_log
         WHERE event_type = 'land_click'
           AND land_address IS NOT NULL
           AND land_address != ''
         GROUP BY land_address
         ORDER BY click_count DESC, land_address ASC
         LIMIT ?
        """,
        (limit,),
    )
    return cursor.fetchall()


def fetch_daily_event_counts(conn: sqlite3.Connection) -> Sequence[sqlite3.Row]:
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT
            DATE(created_at) AS date,
            SUM(CASE WHEN event_type = 'search' THEN 1 ELSE 0 END) AS search_count,
            SUM(CASE WHEN event_type = 'land_click' THEN 1 ELSE 0 END) AS click_count
          FROM map_event_log
         GROUP BY DATE(created_at)
         ORDER BY DATE(created_at) ASC
        """
    )
    return cursor.fetchall()


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
