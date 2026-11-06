import importlib
import json
import logging
import re
import sqlite3
from pathlib import Path

import httpx
import pytest
from _pytest.monkeypatch import MonkeyPatch

from app import rate_limit
from app.clients import http_client
from app.db.connection import db_connection
from app.repositories import land_repository
from app.services import geo_service, seed_service, upload_service
from tests.db_helpers import init_test_db
from tests.helpers import temp_env

ADMIN_PASSWORD = "admin-password"
GEOM = '{"type":"Point","coordinates":[0,0]}'


def _seed(count: int) -> None:
    with db_connection() as conn:
        land_repository.delete_all(conn)
        for index in range(count):
            land_repository.insert_land(
                conn,
                address=f"addr-{index}",
                land_type="대",
                area=1.0,
                adm_property="Y",
                gen_property="N",
                contact="041",
            )
        conn.commit()


def _fake_client(*, unresolvable: int = 0, on_call=None) -> type:
    class FakeClient:
        def __init__(self, *args: object, **kwargs: object) -> None:
            pass

        def get_parcel_geometry(self, address: str, request_id: str = "-") -> str | None:
            if on_call is not None:
                on_call()
            return None if int(address.split("-")[1]) < unresolvable else GEOM

    return FakeClient


def test_geom_job_covers_every_row_beyond_one_batch(db_path: object, monkeypatch: MonkeyPatch) -> None:
    init_test_db()
    _seed(300)
    monkeypatch.setattr(geo_service, "VWorldClient", _fake_client())
    assert geo_service.update_geoms(max_retries=1) == (300, 0)


def test_geom_job_is_not_blocked_by_unresolvable_head_of_line(
    db_path: object, monkeypatch: MonkeyPatch
) -> None:
    init_test_db()
    _seed(120)
    monkeypatch.setattr(geo_service, "VWorldClient", _fake_client(unresolvable=50))
    monkeypatch.setattr(geo_service.time, "sleep", lambda _seconds: None)
    assert geo_service.update_geoms(max_retries=2) == (70, 50)


def test_geom_job_does_not_hold_write_lock_across_network_calls(
    db_path: Path, monkeypatch: MonkeyPatch
) -> None:
    init_test_db()
    _seed(5)

    def write_from_another_connection() -> None:
        other = sqlite3.connect(db_path, timeout=0.1)
        try:
            other.execute("INSERT INTO geom_update_jobs (status) VALUES ('probe')")
            other.commit()
        finally:
            other.close()

    monkeypatch.setattr(geo_service, "VWorldClient", _fake_client(on_call=write_from_another_connection))
    assert geo_service.update_geoms(max_retries=1) == (5, 0)


def test_reupload_keeps_known_geometry(db_path: object) -> None:
    init_test_db()
    _seed(1)
    with db_connection() as conn:
        land_repository.update_geom(conn, 1, GEOM)
        conn.commit()

    row = {"address": "addr-0", "land_type": "대", "area": 2.0, "adm_property": "", "gen_property": "", "contact": ""}
    upload_service._replace_land_data([row, {**row, "address": "new-parcel"}])

    with db_connection() as conn:
        assert land_repository.fetch_geom_by_address(conn) == {"addr-0": GEOM}
        assert land_repository.count_missing_geom(conn) == 1


def test_http_failure_log_does_not_contain_api_key(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.WARNING), pytest.raises(Exception):  # noqa: B017
        http_client.get_json_with_retry(
            "http://127.0.0.1:1/req?key=SECRET-KEY",
            timeout_s=0.5,
            retries=1,
            backoff_s=0,
        )
    assert caplog.records
    assert "SECRET-KEY" not in caplog.text


def test_rate_limiter_evicts_expired_keys(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setattr(rate_limit, "MAX_TRACKED_KEYS", 3)
    clock = [1000.0]
    monkeypatch.setattr(rate_limit.time, "time", lambda: clock[0])
    limiter = rate_limit.SlidingWindowRateLimiter()
    for index in range(3):
        limiter.allow(key=f"k{index}", limit=1, window_seconds=60)
    clock[0] += 61
    limiter.allow(key="fresh", limit=1, window_seconds=60)
    assert list(limiter._events) == ["fresh"]


def test_seed_loads_once_into_empty_database(db_path: object, tmp_path: Path) -> None:
    init_test_db()
    _seed(0)
    seed = tmp_path / "lands.json"
    row = {"address": "a", "land_type": "대", "area": 1.5, "adm_property": "", "gen_property": "", "contact": "041", "geom": GEOM}
    seed.write_text(json.dumps([row, {**row, "address": "b", "geom": None}]), encoding="utf-8")

    assert seed_service.seed_lands_if_empty(seed) == 2
    assert seed_service.seed_lands_if_empty(seed) == 0
    with db_connection() as conn:
        assert land_repository.count_all_lands(conn) == 2
        assert land_repository.count_missing_geom(conn) == 1


def test_repository_seed_has_only_land_columns() -> None:
    rows = json.loads((Path(__file__).resolve().parents[1] / "seed" / "lands.json").read_text(encoding="utf-8"))
    assert rows
    assert set(rows[0]) == {"address", "land_type", "area", "adm_property", "gen_property", "contact", "geom"}


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("filename", "use_valid_csrf", "expected"),
    [("bad.txt", True, 400), ("ok.xlsx", False, 403)],
)
async def test_upload_service_errors_keep_their_status(
    async_client: httpx.AsyncClient, db_path: object, filename: str, use_valid_csrf: bool, expected: int
) -> None:
    init_test_db()
    page = await async_client.get("/admin/login")
    token = re.search(r'name="csrf_token" value="([^"]+)"', page.text).group(1)
    login = await async_client.post(
        "/login", data={"username": "admin", "password": ADMIN_PASSWORD, "csrf_token": token}
    )
    assert login.status_code == 200
    admin_page = await async_client.get("/admin/")
    token = re.search(r'csrf[-_]token"[^>]*(?:value|content)="([^"]+)"', admin_page.text).group(1)

    res = await async_client.post(
        "/admin/upload",
        data={"csrf_token": token if use_valid_csrf else "wrong"},
        files={"file": (filename, b"PK\x03\x04data", "application/octet-stream")},
    )
    assert res.status_code == expected


@pytest.mark.anyio
async def test_event_body_limit(async_client: httpx.AsyncClient, db_path: object) -> None:
    init_test_db()
    res = await async_client.post(
        "/api/events",
        json={"eventType": "search", "anonId": "a", "searchTerm": "x" * (32 * 1024)},
    )
    assert res.status_code == 413


@pytest.mark.anyio
async def test_invalid_public_inputs_are_client_errors(async_client: httpx.AsyncClient, db_path: object) -> None:
    init_test_db()
    assert (await async_client.get("/api/lands", params={"cursor": "9" * 30})).status_code == 400
    res = await async_client.post(
        "/api/web-events",
        json={"eventType": "visit_start", "anonId": "a", "sessionId": "s", "pagePath": "/", "clientTs": 1e30},
    )
    assert res.status_code == 400


@pytest.mark.anyio
async def test_deep_health_is_not_public(build_app, db_path: object) -> None:
    transport = httpx.ASGITransport(app=build_app(), client=("203.0.113.9", 50000))
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        assert (await client.get("/health")).status_code == 200
        assert (await client.get("/health?deep=1")).status_code == 403


@pytest.mark.anyio
async def test_admin_disabled_closes_every_admin_surface(app_env: dict[str, str], db_path: object) -> None:
    init_test_db()
    env = {**app_env, "ADMIN_ENABLED": "false"}
    with temp_env(env):
        from app.core import config

        config.get_settings.cache_clear()
        app_main = importlib.reload(importlib.import_module("app.main"))
        protected = sorted(
            (method, route.path)
            for route in app_main.app.routes
            if route.path.startswith(("/admin", "/login", "/logout"))
            for method in getattr(route, "methods", None) or ()
            if method != "HEAD"
        )
        assert len(protected) > 10
        transport = httpx.ASGITransport(app=app_main.app, client=("127.0.0.1", 50000))
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            for method, path in protected:
                res = await client.request(method, path.replace("{job_id}", "1"))
                assert res.status_code == 404, (method, path)
            assert (await client.get("/api/config")).status_code == 200
        config.get_settings.cache_clear()
