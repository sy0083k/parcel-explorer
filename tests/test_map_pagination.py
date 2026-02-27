import httpx
import pytest

from app.db.connection import db_connection
from app.repositories import poi_repository


def _seed_lands(count: int) -> None:
    with db_connection() as conn:
        poi_repository.init_db(conn)
        poi_repository.delete_all(conn)
        for idx in range(count):
            poi_repository.insert_land(
                conn,
                address=f"addr-{idx}",
                land_type="type",
                area=1.0 + idx,
                adm_property="adm",
                gen_property="gen",
                contact="010",
            )
        conn.commit()

        missing = poi_repository.fetch_missing_geom(conn)
        for item_id, _ in missing:
            poi_repository.update_geom(conn, item_id, '{"type":"Point","coordinates":[0,0]}')
        conn.commit()


@pytest.mark.anyio
async def test_lands_pagination_cursor(async_client: httpx.AsyncClient, db_path: object) -> None:
    _seed_lands(3)

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
    _seed_lands(1)

    v0 = await async_client.get("/api/lands?limit=5")
    v1 = await async_client.get("/api/v1/lands?limit=5")

    assert v0.status_code == 200
    assert v1.status_code == 200
    assert v0.json() == v1.json()


@pytest.mark.anyio
async def test_lands_invalid_cursor_returns_400(async_client: httpx.AsyncClient) -> None:
    res = await async_client.get("/api/lands?cursor=bad")
    assert res.status_code == 400
