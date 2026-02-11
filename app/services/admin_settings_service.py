from __future__ import annotations

from pathlib import Path

from app.core import get_settings

WHITELIST_KEYS = {
    "VWORLD_WMTS_KEY",
    "VWORLD_GEOCODER_KEY",
    "ALLOWED_IPS",
    "MAX_UPLOAD_SIZE_MB",
    "MAX_UPLOAD_ROWS",
    "LOGIN_MAX_ATTEMPTS",
    "LOGIN_COOLDOWN_SECONDS",
    "VWORLD_TIMEOUT_S",
    "VWORLD_RETRIES",
    "VWORLD_BACKOFF_S",
    "SESSION_HTTPS_ONLY",
}

INT_KEYS = {
    "MAX_UPLOAD_SIZE_MB",
    "MAX_UPLOAD_ROWS",
    "LOGIN_MAX_ATTEMPTS",
    "LOGIN_COOLDOWN_SECONDS",
    "VWORLD_RETRIES",
}

FLOAT_KEYS = {"VWORLD_TIMEOUT_S", "VWORLD_BACKOFF_S"}

BOOL_KEYS = {"SESSION_HTTPS_ONLY"}


def get_current_settings() -> dict[str, str]:
    settings = get_settings()
    return {
        "VWORLD_WMTS_KEY": settings.vworld_wmts_key,
        "VWORLD_GEOCODER_KEY": settings.vworld_geocoder_key,
        "ALLOWED_IPS": ",".join(str(n) for n in settings.allowed_ip_networks),
        "MAX_UPLOAD_SIZE_MB": str(settings.max_upload_size_mb),
        "MAX_UPLOAD_ROWS": str(settings.max_upload_rows),
        "LOGIN_MAX_ATTEMPTS": str(settings.login_max_attempts),
        "LOGIN_COOLDOWN_SECONDS": str(settings.login_cooldown_seconds),
        "VWORLD_TIMEOUT_S": str(settings.vworld_timeout_s),
        "VWORLD_RETRIES": str(settings.vworld_retries),
        "VWORLD_BACKOFF_S": str(settings.vworld_backoff_s),
        "SESSION_HTTPS_ONLY": "true" if settings.session_https_only else "false",
    }


def validate_updates(updates: dict[str, str]) -> dict[str, str]:
    cleaned: dict[str, str] = {}
    for key, value in updates.items():
        if key not in WHITELIST_KEYS:
            continue
        raw = value.strip()
        if key in INT_KEYS:
            if not raw.isdigit():
                raise ValueError(f"{key} must be an integer.")
        if key in FLOAT_KEYS:
            try:
                float(raw)
            except ValueError as exc:
                raise ValueError(f"{key} must be a float.") from exc
        if key in BOOL_KEYS:
            if raw.lower() not in {"true", "false"}:
                raise ValueError(f"{key} must be true or false.")
            raw = raw.lower()
        cleaned[key] = raw
    return cleaned


def update_env_file(base_dir: str, updates: dict[str, str]) -> None:
    env_path = Path(base_dir) / ".env"
    if env_path.exists():
        lines = env_path.read_text(encoding="utf-8").splitlines()
    else:
        lines = []

    remaining = dict(updates)
    new_lines: list[str] = []
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            new_lines.append(line)
            continue
        key, _value = stripped.split("=", 1)
        if key in remaining:
            new_lines.append(f"{key}={_format_env_value(remaining.pop(key))}")
        else:
            new_lines.append(line)

    for key, value in remaining.items():
        new_lines.append(f"{key}={_format_env_value(value)}")

    env_path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")


def update_admin_password_hash(base_dir: str, password_hash: str) -> None:
    update_env_file(base_dir, {"ADMIN_PW_HASH": password_hash})


def _format_env_value(value: str) -> str:
    if " " in value or "#" in value:
        return f"\"{value}\""
    return value
