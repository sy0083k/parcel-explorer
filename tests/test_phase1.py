import importlib
import os
import unittest
from contextlib import contextmanager


@contextmanager
def temp_env(values: dict[str, str]):
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
    def test_required_env_validation(self):
        from app.core import config

        config.get_settings.cache_clear()
        with temp_env(
            {
                "SECRET_KEY": "",
                "VWORLD_KEY": "key",
                "ADMIN_ID": "admin",
                "ADMIN_PW_HASH": "hash",
            }
        ):
            with self.assertRaises(config.SettingsError):
                config.get_settings()


class AppSmokeTests(unittest.TestCase):
    def test_root_and_config_routes(self):
        env = {
            "APP_NAME": "IdlePublicProperty",
            "MAP_CENTER_LON": "126.45",
            "MAP_CENTER_LAT": "36.78",
            "MAP_DEFAULT_ZOOM": "14",
            "VWORLD_KEY": "test-key",
            "ADMIN_ID": "admin",
            "ADMIN_PW_HASH": "$2b$12$uYvkCs.waU3zAbFG8sM4xONVkRuA6xk//0A8I1yKTPfUFihhsN0.q",
            "SECRET_KEY": "test-secret-key",
            "ALLOWED_IPS": "127.0.0.1",
        }
        with temp_env(env):
            from app.core import config

            config.get_settings.cache_clear()
            app_main = importlib.import_module("app.main")
            app_main = importlib.reload(app_main)

            from fastapi.testclient import TestClient

            with TestClient(app_main.app) as client:
                root = client.get("/")
                self.assertEqual(root.status_code, 200)

                cfg = client.get("/api/config")
                self.assertEqual(cfg.status_code, 200)
                payload = cfg.json()
                self.assertIn("center", payload)
                self.assertEqual(payload["vworldKey"], "test-key")


if __name__ == "__main__":
    unittest.main()
