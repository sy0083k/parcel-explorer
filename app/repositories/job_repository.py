import sqlite3


def init_job_schema(conn: sqlite3.Connection) -> None:
    cursor = conn.cursor()
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


def create_geom_update_job(conn: sqlite3.Connection) -> int:
    cursor = conn.cursor()
    cursor.execute("INSERT INTO geom_update_jobs (status) VALUES ('pending')")
    lastrowid = cursor.lastrowid
    if lastrowid is None:
        raise RuntimeError("Failed to create geom_update_jobs row.")
    return int(lastrowid)


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


def fetch_geom_job(conn: sqlite3.Connection, job_id: int) -> sqlite3.Row | None:
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT id, status, attempts, updated_count, failed_count, error_message, created_at, updated_at
          FROM geom_update_jobs
         WHERE id = ?
        """,
        (job_id,),
    )
    return cursor.fetchone()


def fetch_latest_active_geom_job(conn: sqlite3.Connection) -> sqlite3.Row | None:
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT id, status, attempts, updated_count, failed_count, error_message, created_at, updated_at
          FROM geom_update_jobs
         WHERE status IN ('pending', 'running')
         ORDER BY id DESC
         LIMIT 1
        """
    )
    return cursor.fetchone()


def mark_stale_geom_jobs_interrupted(conn: sqlite3.Connection) -> int:
    cursor = conn.cursor()
    cursor.execute(
        """
        UPDATE geom_update_jobs
           SET status = 'failed',
               error_message = '서버 재시작으로 인해 중단됨',
               updated_at = CURRENT_TIMESTAMP
         WHERE status IN ('pending', 'running')
        """
    )
    return cursor.rowcount
