import httpx
import pytest

from tests.db_helpers import seed_lands


@pytest.mark.anyio
async def test_lands_pagination_cursor(async_client: httpx.AsyncClient, db_path: object) -> None:
    seed_lands(count=3)

    first = await async_client.get("/api/lands?limit=2")
    assert first.status_code == 200
    payload1 = first.json()
    assert payload1["type"] == "FeatureCollection"
    assert len(payload1["features"]) == 2
    assert payload1["nextCursor"] is not None

    second = await async_client.get(f"/api/lands?limit=2&cursor={payload1['nextCursor']}")
    assert second.status_code == 200
    payload2 = second.json()
    assert len(payload2["features"]) == 1
    assert payload2["nextCursor"] is None


@pytest.mark.anyio
async def test_map_v1_router_matches_map_router(async_client: httpx.AsyncClient, db_path: object) -> None:
    seed_lands(count=1)

    v0 = await async_client.get("/api/lands?limit=5")
    v1 = await async_client.get("/api/v1/lands?limit=5")

    assert v0.status_code == 200
    assert v1.status_code == 200
    assert v0.json() == v1.json()


@pytest.mark.anyio
async def test_lands_invalid_cursor_returns_400(async_client: httpx.AsyncClient) -> None:
    res = await async_client.get("/api/lands?cursor=bad")
    assert res.status_code == 400
