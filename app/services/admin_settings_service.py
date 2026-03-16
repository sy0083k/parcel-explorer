from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from ipaddress import ip_network
from pathlib import Path
from typing import Any, Literal

import bcrypt
from fastapi import HTTPException, Request
from starlette.datastructures import FormData

from app.core.config import get_settings
from app.core.runtime_config import rebuild_runtime_state
from app.dependencies import validate_csrf_token

FieldKind = Literal["str", "int", "float", "bool", "network_list"]


@dataclass(frozen=True)
class AdminSettingField:
    env_key: str
    form_field: str
    settings_attr: str
    kind: FieldKind


ADMIN_SETTINGS_FIELDS: tuple[AdminSettingField, ...] = (
    AdminSettingField("APP_NAME", "app_name", "app_name", "str"),
    AdminSettingField("VWORLD_WMTS_KEY", "vworld_wmts_key", "vworld_wmts_key", "str"),
    AdminSettingField("VWORLD_GEOCODER_KEY", "vworld_geocoder_key", "vworld_geocoder_key", "str"),
    AdminSettingField("ALLOWED_IPS", "allowed_ips", "allowed_ip_networks", "network_list"),
    AdminSettingField("MAX_UPLOAD_SIZE_MB", "max_upload_size_mb", "max_upload_size_mb", "int"),
    AdminSettingField("MAX_UPLOAD_ROWS", "max_upload_rows", "max_upload_rows", "int"),
    AdminSettingField("LOGIN_MAX_ATTEMPTS", "login_max_attempts", "login_max_attempts", "int"),
    AdminSettingField("LOGIN_COOLDOWN_SECONDS", "login_cooldown_seconds", "login_cooldown_seconds", "int"),
    AdminSettingField("VWORLD_TIMEOUT_S", "vworld_timeout_s", "vworld_timeout_s", "float"),
    AdminSettingField("VWORLD_RETRIES", "vworld_retries", "vworld_retries", "int"),
    AdminSettingField("VWORLD_BACKOFF_S", "vworld_backoff_s", "vworld_backoff_s", "float"),
    AdminSettingField("SESSION_HTTPS_ONLY", "session_https_only", "session_https_only", "bool"),
    AdminSettingField("TRUST_PROXY_HEADERS", "trust_proxy_headers", "trust_proxy_headers", "bool"),
    AdminSettingField("TRUSTED_PROXY_IPS", "trusted_proxy_ips", "trusted_proxy_networks", "network_list"),
    AdminSettingField("UPLOAD_SHEET_NAME", "upload_sheet_name", "upload_sheet_name", "str"),
    AdminSettingField(
        "PUBLIC_DOWNLOAD_RATE_LIMIT_PER_MINUTE",
        "public_download_rate_limit_per_minute",
        "public_download_rate_limit_per_minute",
        "int",
    ),
)

ADMIN_SETTINGS_FIELD_BY_KEY = {field.env_key: field for field in ADMIN_SETTINGS_FIELDS}
def get_current_settings() -> dict[str, str]:
    settings = get_settings()
    return {
        field.env_key: _serialize_setting_value(field, getattr(settings, field.settings_attr))
        for field in ADMIN_SETTINGS_FIELDS
    }


def collect_settings_updates(form_data: Mapping[str, Any] | FormData) -> dict[str, str]:
    updates: dict[str, str] = {}
    for field in ADMIN_SETTINGS_FIELDS:
        value = form_data.get(field.form_field, "")
        updates[field.env_key] = value if isinstance(value, str) else str(value)
    return updates


def validate_updates(updates: dict[str, str]) -> dict[str, str]:
    cleaned: dict[str, str] = {}
    for key, value in updates.items():
        field = ADMIN_SETTINGS_FIELD_BY_KEY.get(key)
        if field is None:
            continue
        cleaned[key] = _normalize_update_value(field, value)
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


def _serialize_setting_value(field: AdminSettingField, value: Any) -> str:
    if field.kind == "bool":
        return "true" if value else "false"
    if field.kind in {"int", "float"}:
        return str(value)
    if field.kind == "network_list":
        return ",".join(str(item) for item in value)
    return str(value)


def _normalize_update_value(field: AdminSettingField, value: str) -> str:
    raw = value.strip()
    if field.kind == "int":
        if not raw.isdigit():
            raise ValueError(f"{field.env_key} must be an integer.")
        return raw
    if field.kind == "float":
        try:
            float(raw)
        except ValueError as exc:
            raise ValueError(f"{field.env_key} must be a float.") from exc
        return raw
    if field.kind == "bool":
        if raw.lower() not in {"true", "false"}:
            raise ValueError(f"{field.env_key} must be true or false.")
        return raw.lower()
    if field.kind == "network_list":
        for candidate in [item.strip() for item in raw.split(",") if item.strip()]:
            try:
                ip_network(candidate, strict=False)
            except ValueError as exc:
                raise ValueError(f"Invalid {field.env_key} entry: {candidate}") from exc
        return raw
    return raw


def get_admin_settings_fields() -> tuple[AdminSettingField, ...]:
    return ADMIN_SETTINGS_FIELDS


def get_admin_settings_form_names() -> tuple[str, ...]:
    return tuple(field.form_field for field in ADMIN_SETTINGS_FIELDS)


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
    os.environ.update(cleaned)
    get_settings.cache_clear()
    rebuild_runtime_state(request.app, get_settings())


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
    os.environ["ADMIN_PW_HASH"] = new_hash
    get_settings.cache_clear()
    rebuild_runtime_state(request.app, get_settings())
