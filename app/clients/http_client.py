import logging
import time
from typing import Any

import requests

from app.logging_utils import RequestIdFilter

logger = logging.getLogger(__name__)
logger.addFilter(RequestIdFilter())


class NonRetryableHTTPError(RuntimeError):
    """Raised when retrying will not fix the HTTP error."""


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
            if 400 <= response.status_code < 500 and response.status_code != 429:
                raise NonRetryableHTTPError(f"non-retryable status: {response.status_code}")
            response.raise_for_status()
            return response.json()
        except NonRetryableHTTPError:
            raise
        except Exception as exc:
            last_error = exc
            logger.warning(
                # The URL carries the API key and requests embeds it in str(exc): log the type only.
                "http get failed (attempt=%s/%s): %s",
                attempt,
                retries,
                type(exc).__name__,
                extra={"request_id": request_id},
            )
            if attempt < retries:
                time.sleep(backoff_s * attempt)

    if last_error:
        raise last_error
    raise RuntimeError("HTTP request failed without explicit exception")
