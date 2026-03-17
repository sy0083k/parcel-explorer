import logging
import time
from dataclasses import dataclass

from app.clients.vworld_client import VWorldClient
from app.core import get_settings
from app.db.connection import db_connection
from app.logging_utils import RequestIdFilter
from app.repositories import event_repository, job_repository, land_repository, web_visit_repository
from app.services.service_errors import AuthError, NotFoundError
from app.services.service_models import RequestContext

logger = logging.getLogger(__name__)
logger.addFilter(RequestIdFilter())


@dataclass(frozen=True)
class GeomRefreshStartCommand:
    context: RequestContext


@dataclass(frozen=True)
class GeomRefreshStartResult:
    success: bool
    job_id: int
    started: bool
    message: str


def init_db() -> None:
    with db_connection() as conn:
        land_repository.init_land_schema(conn)
        job_repository.init_job_schema(conn)
        event_repository.init_event_schema(conn)
        web_visit_repository.init_web_visit_schema(conn)
        conn.commit()


def enqueue_geom_update_job() -> int:
    with db_connection() as conn:
        job_id = job_repository.create_geom_update_job(conn)
        conn.commit()
    return job_id


def recover_interrupted_geom_jobs() -> int | None:
    with db_connection() as conn:
        stale_count = job_repository.mark_stale_geom_jobs_interrupted(conn)
        if stale_count == 0:
            return None
        missing_count = land_repository.count_missing_geom(conn)
        new_job_id: int | None = None
        if missing_count > 0:
            new_job_id = job_repository.create_geom_update_job(conn)
        conn.commit()
    if new_job_id is None:
        logger.info(
            "startup recovery: %d stale job(s) marked failed, no missing geoms",
            stale_count,
            extra={"event": "startup.geom_recovery.skipped", "actor": "system", "status": 200},
        )
        return None
    logger.warning(
        "startup recovery: %d stale job(s) found, %d missing geom(s) — re-enqueuing as job %d",
        stale_count,
        missing_count,
        new_job_id,
        extra={"event": "startup.geom_recovery.enqueued", "actor": "system", "status": 200},
    )
    return new_job_id


def run_geom_update_job(job_id: int, max_retries: int = 5) -> tuple[int, int]:
    with db_connection() as conn:
        job_repository.mark_geom_job_running(conn, job_id)
        conn.commit()

    started = time.perf_counter()
    updated_count = 0
    failed_count = 0
    try:
        updated_count, failed_count = update_geoms(max_retries=max_retries)
        with db_connection() as conn:
            job_repository.mark_geom_job_done(
                conn, job_id, updated_count=updated_count, failed_count=failed_count
            )
            conn.commit()
        logger.info(
            "geom job completed",
            extra={
                "event": "geom.job.completed",
                "actor": "system",
                "status": 200,
                "job_id": job_id,
                "updated_count": updated_count,
                "failed_count": failed_count,
                "duration_ms": round((time.perf_counter() - started) * 1000, 2),
            },
        )
    except Exception as exc:
        with db_connection() as conn:
            job_repository.mark_geom_job_failed(
                conn,
                job_id,
                updated_count=updated_count,
                failed_count=failed_count,
                error_message=str(exc)[:2000],
            )
            conn.commit()
        logger.error(
            "geom job failed",
            extra={
                "event": "geom.job.failed",
                "actor": "system",
                "status": 500,
                "job_id": job_id,
                "updated_count": updated_count,
                "failed_count": failed_count,
                "duration_ms": round((time.perf_counter() - started) * 1000, 2),
            },
        )
        raise
    return updated_count, failed_count


def start_geom_refresh_job(command: GeomRefreshStartCommand) -> GeomRefreshStartResult:
    if not command.context.csrf_valid:
        raise AuthError(status_code=403, message="CSRF 토큰 검증에 실패했습니다.")
    with db_connection(row_factory=True) as conn:
        active_job = job_repository.fetch_latest_active_geom_job(conn)

    if active_job is not None:
        job_id = int(active_job["id"])
        return GeomRefreshStartResult(
            success=True,
            job_id=job_id,
            started=False,
            message="이미 실행 중인 경계선 수집 작업이 있습니다.",
        )

    job_id = enqueue_geom_update_job()
    return GeomRefreshStartResult(
        success=True,
        job_id=job_id,
        started=True,
        message="경계선 정보 수집 작업을 시작했습니다.",
    )


def get_geom_refresh_job_status(job_id: int) -> dict[str, object]:
    with db_connection(row_factory=True) as conn:
        row = job_repository.fetch_geom_job(conn, job_id)

    if row is None:
        raise NotFoundError(status_code=404, message="작업을 찾을 수 없습니다.")

    return {
        "id": int(row["id"]),
        "status": str(row["status"]),
        "attempts": int(row["attempts"] or 0),
        "updatedCount": int(row["updated_count"] or 0),
        "failedCount": int(row["failed_count"] or 0),
        "errorMessage": str(row["error_message"] or ""),
        "createdAt": str(row["created_at"]),
        "updatedAt": str(row["updated_at"]),
    }


def update_geoms(max_retries: int = 5) -> tuple[int, int]:
    settings = get_settings()
    client = VWorldClient(
        api_key=settings.vworld_geocoder_key,
        timeout_s=settings.vworld_timeout_s,
        retries=settings.vworld_retries,
        backoff_s=settings.vworld_backoff_s,
    )
    with db_connection() as conn:
        updated_count = 0
        batch_size = 50
        for attempt in range(1, max_retries + 1):
            failed_items = land_repository.fetch_missing_geom(conn, limit=batch_size)

            if not failed_items:
                break

            updated_in_batch = 0
            for item_id, address in failed_items:
                geom_data = client.get_parcel_geometry(address)
                if geom_data:
                    land_repository.update_geom(conn, item_id, geom_data)
                    updated_count += 1
                    updated_in_batch += 1
                else:
                    logger.warning("경계선 획득 실패 (%s)", address)
                    time.sleep(settings.vworld_backoff_s * attempt)

            if updated_in_batch:
                conn.commit()

        failed = land_repository.count_missing_geom(conn)
    return updated_count, failed
