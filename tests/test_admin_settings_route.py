import re
from collections.abc import AsyncIterator, Callable

import bcrypt
import httpx
import pytest
from _pytest.monkeypatch import MonkeyPatch
from fastapi import FastAPI
from starlette.datastructures import FormData

from app.services import admin_settings_service

CSRF_PATTERN = r'name="csrf_token" value="([^"]+)"'


@pytest.fixture
async def client_and_app(
    build_app: Callable[[], FastAPI],
) -> AsyncIterator[tuple[httpx.AsyncClient, FastAPI]]:
    app = build_app()
    transport = httpx.ASGITransport(app=app, client=("127.0.0.1", 50000))
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client, app


async def _login_as_admin(client: httpx.AsyncClient) -> None:
    login_page = await client.get("/admin/login")
    match = re.search(CSRF_PATTERN, login_page.text)
    assert match is not None

    response = await client.post(
        "/login",
        data={
            "username": "admin",
            "password": "admin-password",
            "csrf_token": match.group(1),
        },
    )
    assert response.status_code == 200
    assert response.json()["success"] is True


async def _get_admin_csrf(client: httpx.AsyncClient) -> str:
    admin_page = await client.get("/admin/")
    assert admin_page.status_code == 200
    match = re.search(CSRF_PATTERN, admin_page.text)
    assert match is not None
    return match.group(1)


def test_admin_settings_metadata_matches_current_settings_keys() -> None:
    fields = admin_settings_service.get_admin_settings_fields()
    current_settings = admin_settings_service.get_current_settings()

    assert tuple(field.env_key for field in fields) == tuple(current_settings.keys())


def test_admin_settings_collects_updates_from_form_data() -> None:
    updates = admin_settings_service.collect_settings_updates(
        FormData(
            {
                "app_name": "Parcel Explorer",
                "vworld_wmts_key": "wmts-key",
                "vworld_geocoder_key": "geocoder-key",
                "allowed_ips": "127.0.0.1/32",
                "max_upload_size_mb": "10",
                "max_upload_rows": "100",
                "login_max_attempts": "5",
                "login_cooldown_seconds": "300",
                "vworld_timeout_s": "5.0",
                "vworld_retries": "3",
                "vworld_backoff_s": "0.5",
                "session_https_only": "true",
                "trust_proxy_headers": "false",
                "trusted_proxy_ips": "10.0.0.0/8",
                "upload_sheet_name": "목록",
                "public_download_rate_limit_per_minute": "7",
                "unexpected_field": "ignored",
            }
        )
    )

    assert tuple(updates.keys()) == tuple(
        field.env_key for field in admin_settings_service.get_admin_settings_fields()
    )
    assert updates["APP_NAME"] == "Parcel Explorer"
    assert updates["TRUSTED_PROXY_IPS"] == "10.0.0.0/8"
    assert "unexpected_field" not in updates


def test_admin_settings_form_names_match_expected_contract() -> None:
    assert admin_settings_service.get_admin_settings_form_names() == (
        "app_name",
        "vworld_wmts_key",
        "vworld_geocoder_key",
        "allowed_ips",
        "max_upload_size_mb",
        "max_upload_rows",
        "login_max_attempts",
        "login_cooldown_seconds",
        "vworld_timeout_s",
        "vworld_retries",
        "vworld_backoff_s",
        "session_https_only",
        "trust_proxy_headers",
        "trusted_proxy_ips",
        "upload_sheet_name",
        "public_download_rate_limit_per_minute",
    )


@pytest.mark.anyio
async def test_admin_settings_accepts_proxy_and_sheet_fields(
    async_client: httpx.AsyncClient,
    monkeypatch: MonkeyPatch,
) -> None:
    captured: dict[str, str] = {}

    def _capture_env_update(_base_dir: str, updates: dict[str, str]) -> None:
        captured.update(updates)

    monkeypatch.setattr("app.services.admin_settings_service.update_env_file", _capture_env_update)

    await _login_as_admin(async_client)
    csrf_token = await _get_admin_csrf(async_client)

    response = await async_client.post(
        "/admin/settings",
        data={
            "csrf_token": csrf_token,
            "settings_password": "admin-password",
            "app_name": "관심 필지 지도 (Parcel Explorer)",
            "vworld_wmts_key": "test-key",
            "vworld_geocoder_key": "test-key",
            "allowed_ips": "127.0.0.1/32,::1/128",
            "max_upload_size_mb": "10",
            "max_upload_rows": "10",
            "login_max_attempts": "5",
            "login_cooldown_seconds": "300",
            "vworld_timeout_s": "5.0",
            "vworld_retries": "3",
            "vworld_backoff_s": "0.5",
            "session_https_only": "false",
            "trust_proxy_headers": "true",
            "trusted_proxy_ips": "10.0.0.0/8",
            "upload_sheet_name": "목록",
            "public_download_rate_limit_per_minute": "10",
        },
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert response.headers["location"] == "/admin/?updated=1"
    assert captured["TRUST_PROXY_HEADERS"] == "true"
    assert captured["TRUSTED_PROXY_IPS"] == "10.0.0.0/8"
    assert captured["UPLOAD_SHEET_NAME"] == "목록"
    assert captured["PUBLIC_DOWNLOAD_RATE_LIMIT_PER_MINUTE"] == "10"


@pytest.mark.anyio
async def test_admin_settings_rejects_invalid_trusted_proxy_ips(
    async_client: httpx.AsyncClient,
) -> None:
    await _login_as_admin(async_client)
    csrf_token = await _get_admin_csrf(async_client)

    response = await async_client.post(
        "/admin/settings",
        data={
            "csrf_token": csrf_token,
            "settings_password": "admin-password",
            "app_name": "관심 필지 지도 (Parcel Explorer)",
            "vworld_wmts_key": "test-key",
            "vworld_geocoder_key": "test-key",
            "allowed_ips": "127.0.0.1/32,::1/128",
            "max_upload_size_mb": "10",
            "max_upload_rows": "10",
            "login_max_attempts": "5",
            "login_cooldown_seconds": "300",
            "vworld_timeout_s": "5.0",
            "vworld_retries": "3",
            "vworld_backoff_s": "0.5",
            "session_https_only": "false",
            "trust_proxy_headers": "true",
            "trusted_proxy_ips": "invalid-network",
            "upload_sheet_name": "목록",
            "public_download_rate_limit_per_minute": "10",
        },
    )

    assert response.status_code == 400
    assert "TRUSTED_PROXY_IPS" in response.text


@pytest.mark.anyio
async def test_admin_settings_updates_runtime_config(
    client_and_app: tuple[httpx.AsyncClient, object],
    monkeypatch: MonkeyPatch,
) -> None:
    client, app = client_and_app
    monkeypatch.setattr("app.services.admin_settings_service.update_env_file", lambda *a, **kw: None)

    await _login_as_admin(client)
    csrf_token = await _get_admin_csrf(client)

    response = await client.post(
        "/admin/settings",
        data={
            "csrf_token": csrf_token,
            "settings_password": "admin-password",
            "app_name": "Hot Reload Test",
            "vworld_wmts_key": "test-key",
            "vworld_geocoder_key": "test-key",
            "allowed_ips": "127.0.0.1/32,::1/128",
            "max_upload_size_mb": "10",
            "max_upload_rows": "10",
            "login_max_attempts": "5",
            "login_cooldown_seconds": "300",
            "vworld_timeout_s": "5.0",
            "vworld_retries": "3",
            "vworld_backoff_s": "0.5",
            "session_https_only": "false",
            "trust_proxy_headers": "false",
            "trusted_proxy_ips": "",
            "upload_sheet_name": "목록",
            "public_download_rate_limit_per_minute": "7",
        },
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert app.state.config.APP_NAME == "Hot Reload Test"
    assert app.state.config.PUBLIC_DOWNLOAD_RATE_LIMIT_PER_MINUTE == 7


@pytest.mark.anyio
async def test_admin_password_update_reflects_in_runtime_config(
    client_and_app: tuple[httpx.AsyncClient, object],
    monkeypatch: MonkeyPatch,
) -> None:
    client, app = client_and_app
    monkeypatch.setattr(
        "app.services.admin_settings_service.update_admin_password_hash",
        lambda *a, **kw: None,
    )

    await _login_as_admin(client)
    csrf_token = await _get_admin_csrf(client)
    original_hash = app.state.config.ADMIN_PW_HASH

    response = await client.post(
        "/admin/password",
        data={
            "csrf_token": csrf_token,
            "current_password": "admin-password",
            "new_password": "new-password-123",
            "new_password_confirm": "new-password-123",
        },
        follow_redirects=False,
    )

    assert response.status_code == 303
    new_hash = app.state.config.ADMIN_PW_HASH
    assert new_hash != original_hash
    assert bcrypt.checkpw(b"new-password-123", new_hash.encode("utf-8"))
