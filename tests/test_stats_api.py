import re

import httpx
import pytest

from app.db.connection import db_connection
from app.repositories import idle_land_repository


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

    assert len(payload["topRegions"]) >= 1
    assert payload["topRegions"][0]["region"] == "대산읍"
    assert len(payload["topClickedLands"]) >= 1


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
