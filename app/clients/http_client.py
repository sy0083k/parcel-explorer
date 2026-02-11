import logging
import time
from typing import Any

import requests

from app.logging_utils import RequestIdFilter

logger = logging.getLogger(__name__)
logger.addFilter(RequestIdFilter())


def get_json_with_retry(
    url: str,
    *,
    timeout_s: float,
    retries: int,
    backoff_s: float,
    request_id: str = "-",
) -> dict[str, Any]:
    """GET JSON with timeout/retry/backoff policy."""
    last_error: Exception | None = None

    for attempt in range(1, retries + 1):
        try:
            response = requests.get(url, timeout=timeout_s)
            response.raise_for_status()
            return response.json()
        except Exception as exc:
            last_error = exc
            logger.warning(
                "http get failed (attempt=%s/%s): %s",
                attempt,
                retries,
                str(exc),
                extra={"request_id": request_id},
            )
            if attempt < retries:
                time.sleep(backoff_s * attempt)

    if last_error:
        raise last_error
    raise RuntimeError("HTTP request failed without explicit exception")
