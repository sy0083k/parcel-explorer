import importlib

import httpx
import pytest

from tests.helpers import temp_env


@pytest.fixture
def app_env():
    return {
        "APP_NAME": "IdlePublicProperty",
        "MAP_CENTER_LON": "126.45",
        "MAP_CENTER_LAT": "36.78",
        "MAP_DEFAULT_ZOOM": "14",
        "VWORLD_KEY": "test-key",
        "ADMIN_ID": "admin",
        "ADMIN_PW_HASH": "$2b$12$MGjgBz6IZSV2boORoUbbQeLqG11Nry5H75zvbYOpJWfMaucKkVSZ6",
        "SECRET_KEY": "test-secret-key",
        "ALLOWED_IPS": "127.0.0.1/32,::1/128",
        "SESSION_HTTPS_ONLY": "false",
        "MAX_UPLOAD_ROWS": "10",
    }


@pytest.fixture
def build_app(app_env):
    def _build():
        with temp_env(app_env):
            from app.core import config

            config.get_settings.cache_clear()
            app_main = importlib.import_module("app.main")
            app_main = importlib.reload(app_main)
            return app_main.app

    return _build


@pytest.fixture
async def async_client(build_app):
    app = build_app()
    transport = httpx.ASGITransport(app=app, client=("127.0.0.1", 50000))
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client


@pytest.fixture
def db_path(tmp_path, monkeypatch):
    from app.db import connection

    path = tmp_path / "test.db"

    def _path():
        return path

    monkeypatch.setattr(connection, "_database_path", _path)
    return path
