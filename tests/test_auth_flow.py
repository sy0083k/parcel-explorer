import importlib
import os
import re
import sys
import unittest
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from fastapi import FastAPI

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))
ADMIN_PASSWORD = "admin-password"
ADMIN_PASSWORD_HASH = "$2b$12$MGjgBz6IZSV2boORoUbbQeLqG11Nry5H75zvbYOpJWfMaucKkVSZ6"


@contextmanager
def temp_env(values: dict[str, str]) -> Iterator[None]:
    original = {k: os.environ.get(k) for k in values}
    os.environ.update(values)
    try:
        yield
    finally:
        for key, value in original.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


def build_test_app() -> FastAPI:
    from app.core import config

    config.get_settings.cache_clear()
    app_main = importlib.import_module("app.main")
    app_main = importlib.reload(app_main)
    return app_main.app


class AuthFlowTests(unittest.TestCase):
    def test_login_success_and_rate_limit(self) -> None:
        env = {
            "VWORLD_WMTS_KEY": "test-key",
            "VWORLD_GEOCODER_KEY": "test-key",
            "ADMIN_ID": "admin",
            "ADMIN_PW_HASH": ADMIN_PASSWORD_HASH,
            "SECRET_KEY": "test-secret-key",
            "ALLOWED_IPS": "127.0.0.1/32",
            "SESSION_HTTPS_ONLY": "false",
            "LOGIN_MAX_ATTEMPTS": "2",
            "LOGIN_COOLDOWN_SECONDS": "60",
        }

        with temp_env(env):
            import anyio
            import httpx

            async def run_flow() -> None:
                app = build_test_app()
                transport = httpx.ASGITransport(app=app, client=("127.0.0.1", 50000))
                async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
                    login_page = await client.get("/admin/login")
                    self.assertEqual(login_page.status_code, 200)
                    match = re.search(r'name="csrf_token" value="([^"]+)"', login_page.text)
                    self.assertIsNotNone(match)
                    csrf_token = match.group(1)

                    success = await client.post(
                        "/login",
                        data={"username": "admin", "password": ADMIN_PASSWORD, "csrf_token": csrf_token},
                    )
                    self.assertEqual(success.status_code, 200)
                    self.assertEqual(success.json().get("success"), True)

                    bad_page = await client.get("/admin/login")
                    bad_csrf = re.search(r'name="csrf_token" value="([^"]+)"', bad_page.text).group(1)
                    bad1 = await client.post(
                        "/login",
                        data={"username": "admin", "password": "wrong", "csrf_token": bad_csrf},
                    )
                    self.assertEqual(bad1.status_code, 401)

                    bad2 = await client.post(
                        "/login",
                        data={"username": "admin", "password": "wrong", "csrf_token": bad_csrf},
                    )
                    self.assertEqual(bad2.status_code, 401)

                    blocked = await client.post(
                        "/login",
                        data={"username": "admin", "password": "wrong", "csrf_token": bad_csrf},
                    )
                    self.assertEqual(blocked.status_code, 429)

            anyio.run(run_flow)

    def test_login_rejects_bad_csrf(self) -> None:
        env = {
            "VWORLD_WMTS_KEY": "test-key",
            "VWORLD_GEOCODER_KEY": "test-key",
            "ADMIN_ID": "admin",
            "ADMIN_PW_HASH": ADMIN_PASSWORD_HASH,
            "SECRET_KEY": "test-secret-key",
            "ALLOWED_IPS": "127.0.0.1/32",
            "SESSION_HTTPS_ONLY": "false",
        }
        with temp_env(env):
            import anyio
            import httpx

            async def run_flow() -> None:
                app = build_test_app()
                transport = httpx.ASGITransport(app=app, client=("127.0.0.1", 50000))
                async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
                    await client.get("/admin/login")
                    res = await client.post(
                        "/login",
                        data={"username": "admin", "password": ADMIN_PASSWORD, "csrf_token": "invalid"},
                    )
                    self.assertEqual(res.status_code, 403)

            anyio.run(run_flow)


if __name__ == "__main__":
    unittest.main()
