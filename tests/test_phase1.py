import importlib
import os
import sys
import unittest
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))


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


class ConfigTests(unittest.TestCase):
    def test_required_env_validation(self) -> None:
        from app.core import config

        config.get_settings.cache_clear()
        with temp_env(
            {
                "SECRET_KEY": "",
                "VWORLD_WMTS_KEY": "key",
                "VWORLD_GEOCODER_KEY": "key",
                "ADMIN_ID": "admin",
                "ADMIN_PW_HASH": "hash",
            }
        ):
            with self.assertRaises(config.SettingsError):
                config.get_settings()

    def test_invalid_admin_hash_rejected(self) -> None:
        from app.core import config

        config.get_settings.cache_clear()
        with temp_env(
            {
                "SECRET_KEY": "secret",
                "VWORLD_WMTS_KEY": "key",
                "VWORLD_GEOCODER_KEY": "key",
                "ADMIN_ID": "admin",
                "ADMIN_PW_HASH": "plaintext-password",
            }
        ):
            with self.assertRaises(config.SettingsError):
                config.get_settings()

    def test_too_many_web_track_paths_rejected(self) -> None:
        from app.core import config

        # 21개 경로 — 상한(20) 초과
        paths = ",".join(f"/{i}" for i in range(21))
        with self.assertRaises(config.SettingsError):
            config._parse_allowed_web_track_paths(paths)


class AppSmokeTests(unittest.TestCase):
    def test_root_and_config_routes(self) -> None:
        env = {
            "APP_NAME": "관심 필지 지도 (Parcel Explorer)",
            "MAP_CENTER_LON": "126.45",
            "MAP_CENTER_LAT": "36.78",
            "MAP_DEFAULT_ZOOM": "14",
            "VWORLD_WMTS_KEY": "test-key",
            "VWORLD_GEOCODER_KEY": "test-key",
            "ADMIN_ID": "admin",
            "ADMIN_PW_HASH": "$2b$12$uYvkCs.waU3zAbFG8sM4xONVkRuA6xk//0A8I1yKTPfUFihhsN0.q",
            "SECRET_KEY": "test-secret-key",
            "ALLOWED_IPS": "127.0.0.1/32,::1/128",
            "SESSION_HTTPS_ONLY": "false",
        }
        with temp_env(env):
            from app.core import config

            config.get_settings.cache_clear()
            app_main = importlib.import_module("app.main")
            app_main = importlib.reload(app_main)

            import anyio
            import httpx

            async def run_flow() -> None:
                transport = httpx.ASGITransport(app=app_main.app, client=("127.0.0.1", 50000))
                async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
                    root = await client.get("/")
                    self.assertEqual(root.status_code, 200)

                    cfg = await client.get("/api/config")
                    self.assertEqual(cfg.status_code, 200)
                    payload = cfg.json()
                    self.assertIn("center", payload)
                self.assertEqual(payload["vworldKey"], "test-key")

            anyio.run(run_flow)


if __name__ == "__main__":
    unittest.main()
