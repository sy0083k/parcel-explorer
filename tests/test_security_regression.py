import io

import httpx
import pytest

from tests.helpers import temp_env


@pytest.mark.anyio
async def test_login_rejects_missing_csrf(async_client: httpx.AsyncClient) -> None:
    res = await async_client.post(
        "/login",
        data={"username": "admin", "password": "admin-password", "csrf_token": ""},
    )
    assert res.status_code == 403


@pytest.mark.anyio
async def test_internal_network_rejected(app_env: dict[str, str]) -> None:
    env = dict(app_env)
    env["ALLOWED_IPS"] = "192.168.0.0/24"

    with temp_env(env):
        import importlib

        from app.core import config

        config.get_settings.cache_clear()
        app_main = importlib.import_module("app.main")
        app_main = importlib.reload(app_main)
        transport = httpx.ASGITransport(app=app_main.app, client=("10.0.0.1", 50000))
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            res = await client.get("/admin/login")
            assert res.status_code == 403


@pytest.mark.anyio
async def test_upload_requires_authentication(async_client: httpx.AsyncClient) -> None:
    file_bytes = io.BytesIO(b"not-an-excel")
    files = {"file": ("test.xlsx", file_bytes, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
    res = await async_client.post("/admin/upload", data={"csrf_token": "x"}, files=files)
    assert res.status_code == 401


@pytest.mark.anyio
async def test_internal_network_accepts_trusted_proxy_forwarded_for(app_env: dict[str, str]) -> None:
    env = dict(app_env)
    env["ALLOWED_IPS"] = "192.168.0.0/24"
    env["TRUST_PROXY_HEADERS"] = "true"
    env["TRUSTED_PROXY_IPS"] = "10.0.0.0/8"

    with temp_env(env):
        import importlib

        from app.core import config

        config.get_settings.cache_clear()
        app_main = importlib.import_module("app.main")
        app_main = importlib.reload(app_main)
        transport = httpx.ASGITransport(app=app_main.app, client=("10.1.2.3", 50000))
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            res = await client.get("/admin/login", headers={"x-forwarded-for": "192.168.0.10"})
            assert res.status_code == 200


@pytest.mark.anyio
async def test_internal_network_rejects_untrusted_proxy_forwarded_for(app_env: dict[str, str]) -> None:
    env = dict(app_env)
    env["ALLOWED_IPS"] = "192.168.0.0/24"
    env["TRUST_PROXY_HEADERS"] = "true"
    env["TRUSTED_PROXY_IPS"] = "10.0.0.0/8"

    with temp_env(env):
        import importlib

        from app.core import config

        config.get_settings.cache_clear()
        app_main = importlib.import_module("app.main")
        app_main = importlib.reload(app_main)
        transport = httpx.ASGITransport(app=app_main.app, client=("172.16.0.10", 50000))
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            res = await client.get("/admin/login", headers={"x-forwarded-for": "192.168.0.10"})
            assert res.status_code == 403


@pytest.mark.anyio
async def test_logout_cookie_secure_matches_session_https_setting(app_env: dict[str, str]) -> None:
    env = dict(app_env)
    env["SESSION_HTTPS_ONLY"] = "false"

    with temp_env(env):
        import importlib

        from app.core import config

        config.get_settings.cache_clear()
        app_main = importlib.import_module("app.main")
        app_main = importlib.reload(app_main)
        transport = httpx.ASGITransport(app=app_main.app, client=("127.0.0.1", 50000))
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            res = await client.get("/logout")
            cookie_header = res.headers.get("set-cookie", "")
            assert "Secure" not in cookie_header
