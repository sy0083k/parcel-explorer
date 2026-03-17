import importlib
import os
import socket
import subprocess
import threading
import time
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from shutil import which

import pytest
import uvicorn

from tests.helpers import temp_env


def _build_env() -> dict[str, str]:
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
        "ALLOWED_WEB_TRACK_PATHS": "/",
    }


def _pick_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        sock.listen(1)
        return int(sock.getsockname()[1])


def _seed_browser_e2e_data() -> None:
    from app.db.connection import db_connection
    from app.repositories import poi_repository

    with db_connection() as conn:
        poi_repository.init_db(conn)
        poi_repository.delete_all(conn)
        poi_repository.insert_land(
            conn,
            address="충남 서산시 예천동 100-1",
            land_type="답",
            area=150.0,
            adm_property="O",
            gen_property="대부 가능",
            contact="010-1111-1111",
        )
        poi_repository.insert_land(
            conn,
            address="충남 서산시 예천동 100-2",
            land_type="전",
            area=80.0,
            adm_property="O",
            gen_property="대부 가능",
            contact="010-2222-2222",
        )
        poi_repository.insert_land(
            conn,
            address="충남 서산시 읍내동 55-1",
            land_type="대",
            area=220.0,
            adm_property="N",
            gen_property="매각",
            contact="010-3333-3333",
        )
        conn.commit()

        for item_id, _ in poi_repository.fetch_missing_geom(conn):
            poi_repository.update_geom(conn, item_id, '{"type":"Point","coordinates":[126.45,36.78]}')
        conn.commit()


def _validate_browser_executable(raw_path: str | None) -> str:
    if not raw_path:
        pytest.fail(
            "PLAYWRIGHT_EXECUTABLE_PATH is required for browser E2E. "
            "Install a system Chromium/Chrome and set its absolute executable path."
        )

    resolved = Path(raw_path.strip())
    if not raw_path.strip():
        pytest.fail("PLAYWRIGHT_EXECUTABLE_PATH must not be empty.")
    if not resolved.is_absolute():
        candidate = which(raw_path.strip())
        hint = f" Resolved candidate: {candidate}." if candidate else ""
        pytest.fail(
            "PLAYWRIGHT_EXECUTABLE_PATH must be an absolute path to a system browser executable."
            f"{hint}"
        )
    if not resolved.exists():
        pytest.fail(f"PLAYWRIGHT_EXECUTABLE_PATH does not exist: {resolved}")
    if not os.access(resolved, os.X_OK):
        pytest.fail(f"PLAYWRIGHT_EXECUTABLE_PATH is not executable: {resolved}")

    version = subprocess.run(
        [str(resolved), "--version"],
        check=False,
        capture_output=True,
        text=True,
    )
    if version.returncode != 0:
        details = (version.stdout + version.stderr).strip()
        pytest.fail(
            f"System browser preflight failed for {resolved}. "
            f"`--version` exited with {version.returncode}. {details}"
        )

    return str(resolved)


@contextmanager
def _run_browser_e2e_server(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> Iterator[str]:
    with temp_env(_build_env()):
        from app.core import config
        from app.db import connection
        from app.services import geo_service

        db_path = tmp_path / "browser-e2e.db"

        def _database_path() -> Path:
            return db_path

        monkeypatch.setattr(connection, "_database_path", _database_path)
        monkeypatch.setattr(geo_service, "run_geom_update_job", lambda *_args, **_kwargs: (0, 0))

        config.get_settings.cache_clear()
        app_main = importlib.import_module("app.main")
        app_main = importlib.reload(app_main)

        _seed_browser_e2e_data()

        port = _pick_free_port()
        server = uvicorn.Server(
            uvicorn.Config(
                app_main.app,
                host="127.0.0.1",
                port=port,
                log_level="warning",
            )
        )
        thread = threading.Thread(target=server.run, daemon=True)
        thread.start()

        deadline = time.time() + 10
        while not server.started:
            if not thread.is_alive():
                raise RuntimeError("Browser E2E test server exited before startup.")
            if time.time() >= deadline:
                raise RuntimeError("Timed out waiting for browser E2E test server startup.")
            time.sleep(0.05)

        try:
            yield f"http://127.0.0.1:{port}"
        finally:
            server.should_exit = True
            thread.join(timeout=10)
            config.get_settings.cache_clear()


def test_map_admin_browser_e2e(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    if os.getenv("RUN_BROWSER_E2E") != "1":
        pytest.skip("Set RUN_BROWSER_E2E=1 to run Playwright browser E2E tests.")

    frontend_dir = Path(__file__).resolve().parents[1] / "frontend"
    executable_path = _validate_browser_executable(os.getenv("PLAYWRIGHT_EXECUTABLE_PATH"))

    build = subprocess.run(
        ["npm", "run", "build"],
        cwd=frontend_dir,
        check=False,
        capture_output=True,
        text=True,
    )
    assert build.returncode == 0, build.stdout + build.stderr

    with _run_browser_e2e_server(monkeypatch, tmp_path) as base_url:
        result = subprocess.run(
            ["npx", "playwright", "test", "tests/e2e/map-admin.spec.ts", "--config=playwright.config.ts"],
            cwd=frontend_dir,
            check=False,
            capture_output=True,
            text=True,
            env={
                **os.environ,
                "PLAYWRIGHT_BASE_URL": base_url,
                "PLAYWRIGHT_EXECUTABLE_PATH": executable_path,
            },
        )

    assert result.returncode == 0, result.stdout + result.stderr
