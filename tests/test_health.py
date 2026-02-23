import httpx
import pytest
from _pytest.monkeypatch import MonkeyPatch


@pytest.mark.anyio
async def test_health_includes_db_check(async_client: httpx.AsyncClient) -> None:
    res = await async_client.get("/health")
    assert res.status_code == 200
    payload = res.json()
    assert payload["status"] == "ok"
    assert payload["checks"]["db"] == "ok"
    assert "request_id" in payload


@pytest.mark.anyio
async def test_health_deep_includes_vworld_check(
    async_client: httpx.AsyncClient, monkeypatch: MonkeyPatch
) -> None:
    from app.services import health_service

    monkeypatch.setattr(
        health_service.vworld_client,
        "check_geocoder_health",
        lambda *_args, **_kwargs: True,
    )
    res = await async_client.get("/health?deep=1")
    assert res.status_code == 200
    payload = res.json()
    assert payload["checks"]["vworld"] == "ok"
