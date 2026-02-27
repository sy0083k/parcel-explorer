from __future__ import annotations

from ipaddress import ip_network
from pathlib import Path

import bcrypt
from fastapi import HTTPException, Request

from app.core import get_settings
from app.dependencies import validate_csrf_token

WHITELIST_KEYS = {
    "APP_NAME",
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
    "TRUST_PROXY_HEADERS",
    "TRUSTED_PROXY_IPS",
    "UPLOAD_SHEET_NAME",
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
        "APP_NAME": settings.app_name,
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
        "TRUST_PROXY_HEADERS": "true" if settings.trust_proxy_headers else "false",
        "TRUSTED_PROXY_IPS": ",".join(str(n) for n in settings.trusted_proxy_networks),
        "UPLOAD_SHEET_NAME": settings.upload_sheet_name,
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
        if key == "TRUSTED_PROXY_IPS":
            for candidate in [item.strip() for item in raw.split(",") if item.strip()]:
                try:
                    ip_network(candidate, strict=False)
                except ValueError as exc:
                    raise ValueError(f"Invalid TRUSTED_PROXY_IPS entry: {candidate}") from exc
        if key in BOOL_KEYS or key == "TRUST_PROXY_HEADERS":
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


def apply_settings_update(
    request: Request,
    *,
    csrf_token: str,
    settings_password: str,
    updates: dict[str, str],
) -> None:
    if not validate_csrf_token(request, csrf_token):
        raise HTTPException(status_code=403, detail="CSRF 토큰 검증에 실패했습니다.")

    if not settings_password:
        raise HTTPException(status_code=400, detail="관리자 비밀번호를 입력해주세요.")

    config = request.app.state.config
    if not bcrypt.checkpw(settings_password.encode("utf-8"), config.ADMIN_PW_HASH.encode("utf-8")):
        raise HTTPException(status_code=401, detail="관리자 비밀번호가 올바르지 않습니다.")

    try:
        cleaned = validate_updates(updates)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    update_env_file(config.BASE_DIR, cleaned)


def apply_password_update(
    request: Request,
    *,
    csrf_token: str,
    current_password: str,
    new_password: str,
    new_password_confirm: str,
) -> None:
    if not validate_csrf_token(request, csrf_token):
        raise HTTPException(status_code=403, detail="CSRF 토큰 검증에 실패했습니다.")

    if not current_password or not new_password:
        raise HTTPException(status_code=400, detail="비밀번호를 입력해주세요.")

    if new_password != new_password_confirm:
        raise HTTPException(status_code=400, detail="새 비밀번호가 일치하지 않습니다.")

    if len(new_password) < 8:
        raise HTTPException(status_code=400, detail="새 비밀번호는 8자 이상이어야 합니다.")

    config = request.app.state.config
    if not bcrypt.checkpw(current_password.encode("utf-8"), config.ADMIN_PW_HASH.encode("utf-8")):
        raise HTTPException(status_code=401, detail="현재 비밀번호가 올바르지 않습니다.")

    new_hash = bcrypt.hashpw(new_password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    update_admin_password_hash(config.BASE_DIR, new_hash)
