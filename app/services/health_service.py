from app.clients import vworld_client
from app.core import get_settings
from app.db.connection import db_connection
from app.repositories import health_repository


def evaluate_health_checks(*, deep: int, request_id: str) -> dict[str, str]:
    checks: dict[str, str] = {}

    with db_connection() as conn:
        health_repository.ping(conn)
    checks["db"] = "ok"

    if deep == 1:
        settings = get_settings()
        try:
            is_ok = vworld_client.check_geocoder_health(
                api_key=settings.vworld_geocoder_key,
                timeout_s=settings.vworld_timeout_s,
                retries=1,
                backoff_s=settings.vworld_backoff_s,
                request_id=request_id,
            )
            checks["vworld"] = "ok" if is_ok else "degraded"
        except Exception:
            checks["vworld"] = "degraded"

    return checks
