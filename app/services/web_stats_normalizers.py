from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any
from urllib.parse import parse_qsl, urlparse

from app.services.service_errors import ValidationError
from app.services.web_stats_constants import (
    BOT_UA_PATTERNS,
    WEB_EVENT_TYPES,
    WEB_TRACKING_PAGE_PATH,
)


def normalize_event_type(raw: Any) -> str:
    event_type = str(raw or "").strip()
    if event_type not in WEB_EVENT_TYPES:
        raise ValidationError(status_code=400, message="Unsupported eventType.")
    return event_type


def normalize_required_token(raw: Any, field_name: str) -> str:
    value = str(raw or "").strip()
    if not value:
        raise ValidationError(status_code=400, message=f"{field_name} is required.")
    return value[:128]


def normalize_optional_string(raw: Any, *, max_length: int) -> str | None:
    if raw is None:
        return None
    value = str(raw).strip()
    if not value:
        return None
    return value[:max_length]


def normalize_optional_int(raw: Any, *, min_value: int, max_value: int) -> int | None:
    if raw in (None, ""):
        return None
    try:
        value = int(raw)
    except (TypeError, ValueError) as exc:
        raise ValidationError(status_code=400, message="numeric client context fields must be integer.") from exc
    if value < min_value or value > max_value:
        return None
    return value


def normalize_page_path(raw: Any, *, allowed_paths: tuple[str, ...]) -> str:
    value = str(raw or "").strip() or WEB_TRACKING_PAGE_PATH
    if not value.startswith("/"):
        raise ValidationError(status_code=400, message="pagePath must start with '/'.")
    if len(value) > 256:
        raise ValidationError(status_code=400, message="pagePath is too long.")
    if value not in allowed_paths:
        raise ValidationError(status_code=400, message="Unsupported pagePath.")
    return value


def normalize_query_string(raw: Any, *, max_length: int) -> str | None:
    if raw is None:
        return None
    value = str(raw).strip()
    if not value:
        return None
    if value.startswith("?"):
        value = value[1:]
    return value[:max_length]


def normalize_referrer_url(raw: Any) -> str | None:
    text = normalize_optional_string(raw, max_length=2048)
    if text is None:
        return None
    try:
        parsed = urlparse(text)
    except ValueError:
        return None
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return None
    path = parsed.path or "/"
    normalized = f"{parsed.scheme}://{parsed.netloc}{path}"
    return normalized[:1024]


def normalize_referrer_domain(raw_domain: Any, referrer_url: str | None) -> str | None:
    domain = normalize_optional_string(raw_domain, max_length=255)
    if domain:
        return domain.lower()
    if not referrer_url:
        return None
    try:
        parsed = urlparse(referrer_url)
    except ValueError:
        return None
    host = parsed.hostname or ""
    host = host.strip().lower()
    return host or None


def parse_client_ts(raw: Any) -> str:
    if raw in (None, ""):
        return datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S")
    try:
        ts = float(raw)
    except (TypeError, ValueError) as exc:
        raise ValidationError(status_code=400, message="clientTs must be unix timestamp seconds.") from exc

    event_dt = datetime.fromtimestamp(ts, tz=UTC)
    now = datetime.now(UTC)
    if event_dt > now + timedelta(minutes=5):
        event_dt = now
    if event_dt < now - timedelta(days=7):
        event_dt = now - timedelta(days=7)
    return event_dt.strftime("%Y-%m-%d %H:%M:%S")


def is_bot_user_agent(user_agent: str) -> bool:
    normalized = user_agent.lower()
    return any(pattern in normalized for pattern in BOT_UA_PATTERNS)


def classify_browser_family(user_agent: str) -> str:
    ua = user_agent.lower()
    if "edg/" in ua or "edge/" in ua:
        return "edge"
    if "opr/" in ua or "opera" in ua:
        return "other"
    if "chrome/" in ua and "chromium" not in ua and "edg/" not in ua:
        return "chrome"
    if "safari/" in ua and "chrome/" not in ua and "chromium" not in ua:
        return "safari"
    if "firefox/" in ua:
        return "firefox"
    if "trident/" in ua or "msie" in ua:
        return "ie"
    return "other"


def classify_device_type(user_agent: str, *, is_bot: bool) -> str:
    if is_bot:
        return "bot"
    ua = user_agent.lower()
    if "tablet" in ua or "ipad" in ua:
        return "tablet"
    if "mobile" in ua or "iphone" in ua or "android" in ua:
        return "mobile"
    if not ua:
        return "unknown"
    return "desktop"


def classify_os_family(user_agent: str) -> str:
    ua = user_agent.lower()
    if "windows" in ua:
        return "windows"
    if "mac os" in ua or "macintosh" in ua:
        return "macos"
    if "iphone" in ua or "ipad" in ua or "ios" in ua:
        return "ios"
    if "android" in ua:
        return "android"
    if "linux" in ua:
        return "linux"
    return "other"


def extract_utm_from_query(query_string: str | None) -> dict[str, str | None]:
    if not query_string:
        return {
            "utmSource": None,
            "utmMedium": None,
            "utmCampaign": None,
            "utmTerm": None,
            "utmContent": None,
        }

    parsed_pairs = parse_qsl(query_string, keep_blank_values=False)
    values = {key.lower(): value for key, value in parsed_pairs}
    return {
        "utmSource": values.get("utm_source"),
        "utmMedium": values.get("utm_medium"),
        "utmCampaign": values.get("utm_campaign"),
        "utmTerm": values.get("utm_term"),
        "utmContent": values.get("utm_content"),
    }
