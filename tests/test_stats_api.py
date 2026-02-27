import re

import httpx
import pytest

from app.db.connection import db_connection
from app.repositories import idle_land_repository
from app.routers import map_router

CSRF_PATTERN = r'name="csrf_token" value="([^"]+)"'


async def _login_as_admin(client: httpx.AsyncClient) -> None:
    login_page = await client.get("/admin/login")
    match = re.search(CSRF_PATTERN, login_page.text)
    assert match is not None

    response = await client.post(
        "/login",
        data={
            "username": "admin",
            "password": "admin-password",
            "csrf_token": match.group(1),
        },
    )
    assert response.status_code == 200
    assert response.json()["success"] is True


async def _get_admin_csrf(client: httpx.AsyncClient) -> str:
    admin_page = await client.get("/admin/")
    assert admin_page.status_code == 200
    match = re.search(r'id="csrfToken" value="([^"]+)"', admin_page.text)
    assert match is not None
    return match.group(1)


@pytest.mark.anyio
async def test_map_event_and_admin_stats_flow(async_client: httpx.AsyncClient, db_path: object) -> None:
    with db_connection() as conn:
        idle_land_repository.init_db(conn)

    event_search = await async_client.post(
        "/api/events",
        json={
            "eventType": "search",
            "anonId": "anon-1",
            "minArea": 120,
            "searchTerm": "대산읍12",
        },
    )
    assert event_search.status_code == 200
    assert event_search.json()["success"] is True

    event_click = await async_client.post(
        "/api/events",
        json={
            "eventType": "land_click",
            "anonId": "anon-1",
            "landAddress": "충남 서산시 대산읍 독곶리 1-1",
        },
    )
    assert event_click.status_code == 200

    # Not authenticated.
    unauthorized = await async_client.get("/admin/stats")
    assert unauthorized.status_code == 401

    await _login_as_admin(async_client)
    stats_response = await async_client.get("/admin/stats?limit=10")
    assert stats_response.status_code == 200
    payload = stats_response.json()

    assert payload["summary"]["searchCount"] >= 1
    assert payload["summary"]["clickCount"] >= 1
    assert payload["summary"]["uniqueSessionCount"] >= 1
    assert payload["landSummary"]["totalLands"] >= 0
    assert payload["landSummary"]["missingGeomLands"] >= 0

    assert len(payload["topRegions"]) >= 1
    assert payload["topRegions"][0]["region"] == "대산읍"
    assert len(payload["topClickedLands"]) >= 1


@pytest.mark.anyio
async def test_admin_geom_refresh_routes(
    async_client: httpx.AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.services import geo_service

    def _fake_start_job(
        request: object,
        background_tasks: object,
        *,
        csrf_token: str,
    ) -> dict[str, object]:
        assert csrf_token
        return {"success": True, "jobId": 101, "started": True, "message": "started"}

    def _fake_status(job_id: int) -> dict[str, object]:
        assert job_id == 101
        return {
            "id": 101,
            "status": "done",
            "attempts": 1,
            "updatedCount": 3,
            "failedCount": 0,
            "errorMessage": "",
            "createdAt": "2026-02-25 00:00:00",
            "updatedAt": "2026-02-25 00:00:01",
        }

    monkeypatch.setattr(geo_service, "start_geom_refresh_job", _fake_start_job)
    monkeypatch.setattr(geo_service, "get_geom_refresh_job_status", _fake_status)

    await _login_as_admin(async_client)
    csrf_token = await _get_admin_csrf(async_client)

    start = await async_client.post("/admin/lands/geom-refresh", data={"csrf_token": csrf_token})
    assert start.status_code == 200
    start_payload = start.json()
    assert start_payload["success"] is True
    assert int(start_payload["jobId"]) == 101
    assert start_payload["started"] is True

    status_response = await async_client.get("/admin/lands/geom-refresh/101")
    assert status_response.status_code == 200
    status_payload = status_response.json()
    assert status_payload["success"] is True
    assert status_payload["job"]["status"] == "done"


@pytest.mark.anyio
async def test_search_empty_region_is_excluded_from_top_regions_but_min_area_counted(
    async_client: httpx.AsyncClient, db_path: object
) -> None:
    with db_connection() as conn:
        idle_land_repository.init_db(conn)

    response = await async_client.post(
        "/api/events",
        json={
            "eventType": "search",
            "anonId": "anon-empty",
            "minArea": 250,
            "searchTerm": "12345",
        },
    )
    assert response.status_code == 200

    await _login_as_admin(async_client)
    stats_response = await async_client.get("/admin/stats?limit=10")
    assert stats_response.status_code == 200
    payload = stats_response.json()

    top_regions = payload["topRegions"]
    assert all(item["region"] != "" for item in top_regions)
    assert all(item["region"] is not None for item in top_regions)
    assert any(item["bucket"] == "200-299" for item in payload["topMinAreaBuckets"])


@pytest.mark.anyio
async def test_map_event_rejects_invalid_payload(async_client: httpx.AsyncClient, db_path: object) -> None:
    response = await async_client.post(
        "/api/events",
        json={"eventType": "land_click", "anonId": "anon-1"},
    )
    assert response.status_code == 400


@pytest.mark.anyio
async def test_web_event_and_web_stats_flow(async_client: httpx.AsyncClient, db_path: object) -> None:
    with db_connection() as conn:
        idle_land_repository.init_db(conn)

    event_start = await async_client.post(
        "/api/web-events",
        json={
            "eventType": "visit_start",
            "anonId": "anon-web-1",
            "sessionId": "session-web-1",
            "pagePath": "/",
            "clientTs": 1763596800,
            "clientTz": "Asia/Seoul",
        },
    )
    assert event_start.status_code == 200
    assert event_start.json()["success"] is True

    event_end = await async_client.post(
        "/api/web-events",
        json={
            "eventType": "visit_end",
            "anonId": "anon-web-1",
            "sessionId": "session-web-1",
            "pagePath": "/",
            "clientTs": 1763596860,
            "clientTz": "Asia/Seoul",
        },
    )
    assert event_end.status_code == 200
    assert event_end.json()["success"] is True

    await _login_as_admin(async_client)
    web_stats_response = await async_client.get("/admin/stats/web?days=30")
    assert web_stats_response.status_code == 200
    payload = web_stats_response.json()
    assert payload["summary"]["totalVisitors"] >= 1
    assert "dailyTrend" in payload


@pytest.mark.anyio
async def test_web_event_rejects_invalid_page_path(async_client: httpx.AsyncClient, db_path: object) -> None:
    response = await async_client.post(
        "/api/web-events",
        json={
            "eventType": "visit_start",
            "anonId": "anon-web-1",
            "sessionId": "session-web-1",
            "pagePath": "/admin",
            "clientTs": 1763596800,
            "clientTz": "Asia/Seoul",
        },
    )
    assert response.status_code == 400


@pytest.mark.anyio
async def test_admin_can_export_raw_query_csv(async_client: httpx.AsyncClient, db_path: object) -> None:
    with db_connection() as conn:
        idle_land_repository.init_db(conn)

    search_response = await async_client.post(
        "/api/events",
        json={
            "eventType": "search",
            "anonId": "anon-export-1",
            "minArea": 120,
            "searchTerm": "예천동",
            "rawSearchTerm": "  예천동  ",
            "rawMinAreaInput": " 120 ",
            "rawMaxAreaInput": " 500 ",
            "rawRentOnly": "true",
        },
    )
    assert search_response.status_code == 200

    click_response = await async_client.post(
        "/api/events",
        json={
            "eventType": "land_click",
            "anonId": "anon-export-2",
            "landAddress": "충남 서산시 대산읍 독곶리 1-1",
            "landId": "99",
            "clickSource": "map_click",
        },
    )
    assert click_response.status_code == 200

    await _login_as_admin(async_client)

    export_search = await async_client.get("/admin/raw-queries/export?event_type=search&limit=100")
    assert export_search.status_code == 200
    assert export_search.headers["content-type"].startswith("text/csv")
    assert "attachment; filename=" in export_search.headers.get("content-disposition", "")
    assert "raw_region_query" in export_search.text
    assert "  예천동  " in export_search.text
    assert " 120 " in export_search.text
    assert "충남 서산시 대산읍 독곶리 1-1" not in export_search.text

    export_all = await async_client.get("/admin/raw-queries/export?event_type=all&limit=100")
    assert export_all.status_code == 200
    assert "충남 서산시 대산읍 독곶리 1-1" in export_all.text
    assert "99" in export_all.text
    assert "map_click" in export_all.text


@pytest.mark.anyio
async def test_map_events_rate_limit_blocks_and_separates_by_anon_id(
    async_client: httpx.AsyncClient, db_path: object, monkeypatch: pytest.MonkeyPatch
) -> None:
    with db_connection() as conn:
        idle_land_repository.init_db(conn)

    monkeypatch.setattr(map_router, "EVENT_LIMIT_PER_MINUTE", 2)

    payload = {
        "eventType": "search",
        "anonId": "anon-rate-1",
        "minArea": 120,
        "searchTerm": "대산읍",
    }
    response_1 = await async_client.post("/api/events", json=payload)
    response_2 = await async_client.post("/api/events", json=payload)
    response_3 = await async_client.post("/api/events", json=payload)

    assert response_1.status_code == 200
    assert response_2.status_code == 200
    assert response_3.status_code == 429
    assert response_3.json()["success"] is False
    assert int(response_3.headers.get("retry-after", "0")) >= 1

    different_anon = await async_client.post(
        "/api/events",
        json={
            "eventType": "search",
            "anonId": "anon-rate-2",
            "minArea": 100,
            "searchTerm": "예천동",
        },
    )
    assert different_anon.status_code == 200


@pytest.mark.anyio
async def test_map_events_rate_limit_falls_back_to_ip_when_anon_id_missing(
    async_client: httpx.AsyncClient, db_path: object, monkeypatch: pytest.MonkeyPatch
) -> None:
    with db_connection() as conn:
        idle_land_repository.init_db(conn)

    monkeypatch.setattr(map_router, "EVENT_LIMIT_PER_MINUTE", 1)

    first = await async_client.post(
        "/api/events",
        json={
            "eventType": "search",
            "minArea": 120,
            "searchTerm": "대산읍",
        },
    )
    second = await async_client.post(
        "/api/events",
        json={
            "eventType": "search",
            "minArea": 130,
            "searchTerm": "예천동",
        },
    )

    assert first.status_code == 200
    assert second.status_code == 429
    assert int(second.headers.get("retry-after", "0")) >= 1


@pytest.mark.anyio
async def test_web_events_rate_limit_applies_on_v1_route(
    async_client: httpx.AsyncClient, db_path: object, monkeypatch: pytest.MonkeyPatch
) -> None:
    with db_connection() as conn:
        idle_land_repository.init_db(conn)

    monkeypatch.setattr(map_router, "WEB_EVENT_LIMIT_PER_MINUTE", 2)

    payload = {
        "eventType": "heartbeat",
        "anonId": "anon-web-rate-1",
        "sessionId": "session-web-rate-1",
        "pagePath": "/",
        "clientTs": 1763596800,
        "clientTz": "Asia/Seoul",
    }
    response_1 = await async_client.post("/api/v1/web-events", json=payload)
    response_2 = await async_client.post("/api/v1/web-events", json=payload)
    response_3 = await async_client.post("/api/v1/web-events", json=payload)

    assert response_1.status_code == 200
    assert response_2.status_code == 200
    assert response_3.status_code == 429
    assert int(response_3.headers.get("retry-after", "0")) >= 1
