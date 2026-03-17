from types import SimpleNamespace

from app.routers import admin
from app.services.raw_query_export_service import RawQueryCsvExportResult


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


def test_raw_query_export_filename_uses_yyyymmdd() -> None:
    filename = admin._raw_query_export_filename(now=admin.datetime(2026, 3, 17))

    assert filename == "raw-queries-20260317.csv"


def test_build_raw_query_export_response_sets_headers() -> None:
    response = admin._build_raw_query_export_response(
        RawQueryCsvExportResult(
            csv_text="id,event_type\n1,search\n",
            row_count=1,
            effective_limit=100,
        ),
        "raw-queries-20260317.csv",
    )

    assert response.headers["content-disposition"] == 'attachment; filename="raw-queries-20260317.csv"'
    assert response.media_type == "text/csv; charset=utf-8"
