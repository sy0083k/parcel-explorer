import io
import json
import re
from base64 import b64encode

import httpx
import pytest
from itsdangerous import TimestampSigner

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


@pytest.mark.anyio
async def test_logout_uses_configured_session_cookie_name(app_env: dict[str, str]) -> None:
    env = dict(app_env)
    env["SESSION_COOKIE_NAME"] = "custom_session_cookie"

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
            assert cookie_header.startswith("custom_session_cookie=")


async def _login_and_get_session_cookie(env: dict[str, str]) -> tuple[str, str]:
    with temp_env(env):
        import importlib

        from app.core import config

        config.get_settings.cache_clear()
        app_main = importlib.import_module("app.main")
        app_main = importlib.reload(app_main)
        transport = httpx.ASGITransport(app=app_main.app, client=("127.0.0.1", 50000))
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            login_page = await client.get("/admin/login")
            assert login_page.status_code == 200
            match = re.search(r'name="csrf_token" value="([^"]+)"', login_page.text)
            assert match is not None
            res = await client.post(
                "/login",
                data={"username": "admin", "password": "admin-password", "csrf_token": match.group(1)},
            )
            assert res.status_code == 200
            cookie_name = env.get("SESSION_COOKIE_NAME", "session")
            cookie_value = client.cookies.get(cookie_name)
            assert cookie_value is not None
            return cookie_name, cookie_value


async def _access_admin_with_cookie(env: dict[str, str], cookie_name: str, cookie_value: str) -> httpx.Response:
    with temp_env(env):
        import importlib

        from app.core import config

        config.get_settings.cache_clear()
        app_main = importlib.import_module("app.main")
        app_main = importlib.reload(app_main)
        transport = httpx.ASGITransport(app=app_main.app, client=("127.0.0.1", 50000))
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            client.cookies.set(cookie_name, cookie_value, domain="testserver", path="/")
            return await client.get("/admin/", follow_redirects=False)


@pytest.mark.anyio
async def test_cross_app_cookie_name_isolation(app_env: dict[str, str]) -> None:
    env_a = dict(app_env)
    env_a["SESSION_COOKIE_NAME"] = "session_app_a"
    env_a["SESSION_NAMESPACE"] = "app-a"
    env_a["SECRET_KEY"] = "shared-secret"
    cookie_name, cookie_value = await _login_and_get_session_cookie(env_a)

    env_b = dict(app_env)
    env_b["SESSION_COOKIE_NAME"] = "session_app_b"
    env_b["SESSION_NAMESPACE"] = "app-b"
    env_b["SECRET_KEY"] = "shared-secret"
    res = await _access_admin_with_cookie(env_b, cookie_name, cookie_value)

    assert res.status_code == 303
    assert res.headers.get("location") == "/admin/login"


@pytest.mark.anyio
async def test_session_namespace_mismatch_is_rejected(app_env: dict[str, str]) -> None:
    env_a = dict(app_env)
    env_a["SESSION_COOKIE_NAME"] = "session_shared"
    env_a["SESSION_NAMESPACE"] = "app-a"
    env_a["SECRET_KEY"] = "shared-secret"
    cookie_name, cookie_value = await _login_and_get_session_cookie(env_a)

    env_b = dict(app_env)
    env_b["SESSION_COOKIE_NAME"] = "session_shared"
    env_b["SESSION_NAMESPACE"] = "app-b"
    env_b["SECRET_KEY"] = "shared-secret"
    res = await _access_admin_with_cookie(env_b, cookie_name, cookie_value)

    assert res.status_code == 303
    assert res.headers.get("location") == "/admin/login"


@pytest.mark.anyio
async def test_session_namespace_missing_is_rejected(app_env: dict[str, str]) -> None:
    env = dict(app_env)
    env["SESSION_COOKIE_NAME"] = "session_shared"
    env["SESSION_NAMESPACE"] = "app-a"
    env["SECRET_KEY"] = "shared-secret"

    legacy_payload = {"user": "admin", "csrf_token": "legacy-csrf"}
    unsigned = b64encode(json.dumps(legacy_payload).encode("utf-8"))
    legacy_cookie_value = TimestampSigner(env["SECRET_KEY"]).sign(unsigned).decode("utf-8")
    res = await _access_admin_with_cookie(env, env["SESSION_COOKIE_NAME"], legacy_cookie_value)

    assert res.status_code == 303
    assert res.headers.get("location") == "/admin/login"
