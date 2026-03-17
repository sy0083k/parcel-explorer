import importlib
from collections.abc import AsyncIterator, Callable
from pathlib import Path

import httpx
import pytest
from _pytest.monkeypatch import MonkeyPatch
from fastapi import FastAPI

from tests.helpers import temp_env

TEST_MARKER_BY_FILE: dict[str, str] = {
    "test_access_policy.py": "unit",
    "test_admin_settings_route.py": "integration",
    "test_assets.py": "unit",
    "test_auth_flow.py": "integration",
    "test_clients.py": "unit",
    "test_e2e_smoke.py": "e2e",
    "test_env_contract.py": "unit",
    "test_event_repository_split.py": "unit",
    "test_geo_service.py": "unit",
    "test_health.py": "integration",
    "test_job_repository_split.py": "unit",
    "test_land_repository_split.py": "unit",
    "test_map_event_service.py": "unit",
    "test_map_pagination.py": "integration",
    "test_observability_headers.py": "integration",
    "test_phase1.py": "integration",
    "test_public_download_api.py": "integration",
    "test_raw_query_export_service.py": "unit",
    "test_repositories.py": "unit",
    "test_schemas.py": "unit",
    "test_security_regression.py": "integration",
    "test_services.py": "unit",
    "test_stats_api.py": "integration",
    "test_admin_stats_service.py": "unit",
    "test_upload_service.py": "unit",
    "test_validators.py": "unit",
    "test_web_stats_ingest.py": "unit",
    "test_web_stats_normalizers.py": "unit",
    "test_web_stats_presenter.py": "unit",
    "test_web_stats_queries.py": "unit",
    "test_web_stats_service.py": "unit",
    "test_web_visit_repository_split.py": "unit",
}


@pytest.fixture
def app_env() -> dict[str, str]:
    return {
        "APP_NAME": "관심 필지 지도 (Parcel Explorer)",
        "MAP_CENTER_LON": "126.45",
        "MAP_CENTER_LAT": "36.78",
        "MAP_DEFAULT_ZOOM": "14",
        "VWORLD_WMTS_KEY": "test-key",
        "VWORLD_GEOCODER_KEY": "test-key",
        "ADMIN_ID": "admin",
        "ADMIN_PW_HASH": "$2b$12$MGjgBz6IZSV2boORoUbbQeLqG11Nry5H75zvbYOpJWfMaucKkVSZ6",
        "SECRET_KEY": "test-secret-key",
        "ALLOWED_IPS": "127.0.0.1/32,::1/128",
        "SESSION_HTTPS_ONLY": "false",
        "SESSION_COOKIE_NAME": "session",
        "SESSION_NAMESPACE": "idle-public-property",
        "MAX_UPLOAD_ROWS": "10",
    }


@pytest.fixture
def build_app(app_env: dict[str, str]) -> Callable[[], FastAPI]:
    def _build() -> FastAPI:
        with temp_env(app_env):
            from app.core import config

            config.get_settings.cache_clear()
            app_main = importlib.import_module("app.main")
            app_main = importlib.reload(app_main)
            return app_main.app

    return _build


@pytest.fixture
async def async_client(build_app: Callable[[], FastAPI]) -> AsyncIterator[httpx.AsyncClient]:
    app = build_app()
    transport = httpx.ASGITransport(app=app, client=("127.0.0.1", 50000))
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client


@pytest.fixture
def db_path(tmp_path: Path, monkeypatch: MonkeyPatch) -> Path:
    from app.db import connection

    path = tmp_path / "test.db"

    def _path() -> Path:
        return path

    monkeypatch.setattr(connection, "_database_path", _path)
    return path


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    for item in items:
        filename = item.path.name
        marker_name = TEST_MARKER_BY_FILE.get(filename)
        if not marker_name:
            continue
        item.add_marker(getattr(pytest.mark, marker_name))
