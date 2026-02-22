import httpx
import pytest


@pytest.mark.anyio
async def test_public_api_responses_include_request_id(async_client: httpx.AsyncClient) -> None:
    config_res = await async_client.get("/api/config")
    assert config_res.status_code == 200
    assert "x-request-id" in config_res.headers

    lands_res = await async_client.get("/api/lands?limit=1")
    assert lands_res.status_code == 200
    assert "x-request-id" in lands_res.headers


@pytest.mark.anyio
async def test_error_response_includes_request_id(async_client: httpx.AsyncClient) -> None:
    bad_cursor = await async_client.get("/api/lands?cursor=bad")
    assert bad_cursor.status_code == 400
    assert "x-request-id" in bad_cursor.headers
