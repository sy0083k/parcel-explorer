import re

import httpx
import pytest
from _pytest.monkeypatch import MonkeyPatch

CSRF_PATTERN = r'name="csrf_token" value="([^"]+)"'


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
            "app_name": "IdlePublicProperty",
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
        },
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert response.headers["location"] == "/admin/?updated=1"
    assert captured["TRUST_PROXY_HEADERS"] == "true"
    assert captured["TRUSTED_PROXY_IPS"] == "10.0.0.0/8"
    assert captured["UPLOAD_SHEET_NAME"] == "목록"


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
            "app_name": "IdlePublicProperty",
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
        },
    )

    assert response.status_code == 400
    assert "TRUSTED_PROXY_IPS" in response.text
