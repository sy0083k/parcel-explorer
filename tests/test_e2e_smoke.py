
import os
import subprocess
import sys
import textwrap

import pytest


def test_login_upload_and_lands_flow() -> None:
    if os.getenv("RUN_HTTP_E2E") != "1":
        pytest.skip("Set RUN_HTTP_E2E=1 to run HTTP E2E smoke test.")
    script = textwrap.dedent(
        """
        import io
        import re
        import pandas as pd
        import anyio
        import httpx
        import importlib
        from tests.helpers import temp_env

        env = {
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
            "MAX_UPLOAD_ROWS": "10",
        }

        async def main():
            with temp_env(env):
                from app.core import config
                config.get_settings.cache_clear()
                app_main = importlib.import_module("app.main")
                app_main = importlib.reload(app_main)

                from app.services import upload_service
                def _noop_run_geom_update_job(*_args, **_kwargs):
                    return (0, 0)
                upload_service.run_geom_update_job = _noop_run_geom_update_job

                transport = httpx.ASGITransport(app=app_main.app, client=("127.0.0.1", 50000))
                async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
                    login_page = await client.get("/admin/login", timeout=5.0)
                    assert login_page.status_code == 200
                    csrf = re.search(r'name="csrf_token" value="([^"]+)"', login_page.text).group(1)
                    login = await client.post(
                        "/login",
                        data={"username": "admin", "password": "admin-password", "csrf_token": csrf},
                        timeout=5.0,
                    )
                    assert login.status_code == 200
                    admin_page = await client.get("/admin/", timeout=5.0)
                    csrf2 = re.search(r'id="csrfToken" value="([^"]+)"', admin_page.text).group(1)

                    df = pd.DataFrame(
                        {
                            "소재지(지번)": ["addr"],
                            "(공부상)지목": ["답"],
                            "(공부상)면적(㎡)": [12.5],
                            "행정재산": ["Y"],
                            "일반재산": ["N"],
                            "담당자연락처": ["010"],
                        }
                    )
                    buffer = io.BytesIO()
                    df.to_excel(buffer, sheet_name="목록", index=False)
                    payload = buffer.getvalue()
                    files = {
                        "file": (
                            "upload.xlsx",
                            payload,
                            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        )
                    }
                    upload = await client.post(
                        "/admin/upload",
                        data={"csrf_token": csrf2},
                        files=files,
                        timeout=10.0,
                    )
                    assert upload.status_code == 200

                    from app.db.connection import db_connection
                    from app.repositories import poi_repository
                    with db_connection() as conn:
                        missing = poi_repository.fetch_missing_geom(conn)
                        if missing:
                            item_id, _ = missing[0]
                            poi_repository.update_geom(
                                conn, item_id, '{"type":"Point","coordinates":[1,2]}'
                            )
                            conn.commit()

                    lands = await client.get("/api/lands", timeout=5.0)
                    assert lands.status_code == 200
                    payload = lands.json()
                    assert payload.get("type") == "FeatureCollection"
                    assert len(payload.get("features", [])) == 1

        anyio.run(main)
        """
    )
    result = subprocess.run([sys.executable, "-c", script], check=False, timeout=20)
    assert result.returncode == 0
