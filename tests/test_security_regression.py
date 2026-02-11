import io

import httpx
import pytest

from tests.helpers import temp_env


@pytest.mark.anyio
async def test_login_rejects_missing_csrf(async_client):
    res = await async_client.post(
        "/login",
        data={"username": "admin", "password": "admin-password", "csrf_token": ""},
    )
    assert res.status_code == 403


@pytest.mark.anyio
async def test_internal_network_rejected(app_env):
    env = dict(app_env)
    env["ALLOWED_IPS"] = "192.168.0.0/24"

    with temp_env(env):
        from app.core import config
        import importlib

        config.get_settings.cache_clear()
        app_main = importlib.import_module("app.main")
        app_main = importlib.reload(app_main)
        transport = httpx.ASGITransport(app=app_main.app, client=("10.0.0.1", 50000))
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            res = await client.get("/admin/login")
            assert res.status_code == 403


@pytest.mark.anyio
async def test_upload_requires_authentication(async_client):
    file_bytes = io.BytesIO(b"not-an-excel")
    files = {"file": ("test.xlsx", file_bytes, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
    res = await async_client.post("/admin/upload", data={"csrf_token": "x"}, files=files)
    assert res.status_code == 401
