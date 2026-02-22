from app.db.connection import db_connection
from app.repositories import job_repository


def test_job_repository_lifecycle(db_path: object) -> None:
    with db_connection(row_factory=True) as conn:
        job_repository.init_job_schema(conn)
        job_id = job_repository.create_geom_update_job(conn)
        job_repository.mark_geom_job_running(conn, job_id)
        job_repository.mark_geom_job_done(conn, job_id, updated_count=3, failed_count=1)
        conn.commit()

        row = conn.execute(
            "SELECT status, updated_count, failed_count FROM geom_update_jobs WHERE id = ?",
            (job_id,),
        ).fetchone()
        assert row is not None
        assert str(row["status"]) == "done"
        assert int(row["updated_count"]) == 3
        assert int(row["failed_count"]) == 1
