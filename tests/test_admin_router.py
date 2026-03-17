from types import SimpleNamespace

from app.routers import admin


def test_build_raw_query_export_log_context_uses_request_metadata() -> None:
    request = SimpleNamespace(
        state=SimpleNamespace(request_id="req-1"),
        session={"user": "admin"},
        client=SimpleNamespace(host="127.0.0.1"),
    )

    context = admin._build_raw_query_export_log_context(
        request,
        event_type="search",
        date_from="2026-02-22",
        date_to="2026-02-23",
        limit=100,
        filename="raw-queries-20260317.csv",
    )

    assert context["request_id"] == "req-1"
    assert context["actor"] == "admin"
    assert context["ip"] == "127.0.0.1"
    assert context["event_type_filter"] == "search"
    assert context["date_from"] == "2026-02-22"
    assert context["date_to"] == "2026-02-23"
    assert context["requested_limit"] == 100
    assert context["export_filename"] == "raw-queries-20260317.csv"
