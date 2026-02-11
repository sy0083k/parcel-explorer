import pytest

from app.clients import http_client, vworld_client


def test_http_client_retries_and_raises(monkeypatch):
    calls = {"count": 0}

    class DummyResponse:
        def raise_for_status(self):
            raise RuntimeError("boom")

        def json(self):
            return {}

    def _get(*_args, **_kwargs):
        calls["count"] += 1
        return DummyResponse()

    monkeypatch.setattr(http_client.requests, "get", _get)

    with pytest.raises(RuntimeError):
        http_client.get_json_with_retry("http://example.com", timeout_s=0.1, retries=2, backoff_s=0)
    assert calls["count"] == 2


def test_vworld_client_returns_geometry(monkeypatch):
    responses = [
        {"response": {"status": "OK", "result": {"point": {"x": "1", "y": "2"}}}},
        {"features": [{"geometry": {"type": "Point", "coordinates": [1, 2]}}]},
    ]

    def _get_json_with_retry(*_args, **_kwargs):
        return responses.pop(0)

    monkeypatch.setattr(vworld_client, "get_json_with_retry", _get_json_with_retry)
    client = vworld_client.VWorldClient(api_key="k", timeout_s=1, retries=1, backoff_s=0)
    geom = client.get_parcel_geometry("addr")
    assert '"type": "Point"' in geom


def test_vworld_client_falls_back_to_point(monkeypatch):
    responses = [
        {"response": {"status": "OK", "result": {"point": {"x": "1", "y": "2"}}}},
        {"features": []},
    ]

    def _get_json_with_retry(*_args, **_kwargs):
        return responses.pop(0)

    monkeypatch.setattr(vworld_client, "get_json_with_retry", _get_json_with_retry)
    client = vworld_client.VWorldClient(api_key="k", timeout_s=1, retries=1, backoff_s=0)
    geom = client.get_parcel_geometry("addr")
    assert '"coordinates": [1.0, 2.0]' in geom
