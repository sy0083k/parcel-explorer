import sqlite3

import pytest

from app.db.connection import db_connection
from app.repositories import event_repository
from app.services import raw_query_export_service
from app.services.service_errors import ServiceError, ValidationError
from app.services.service_models import RawQueryExportCommand


def test_raw_query_export_service_date_parsers() -> None:
    assert raw_query_export_service.parse_date_start("2026-02-22") == "2026-02-22 00:00:00"
    assert raw_query_export_service.parse_date_end_exclusive("2026-02-22") == "2026-02-23 00:00:00"


def test_raw_query_export_service_export_csv(db_path: object) -> None:
    with db_connection() as conn:
        event_repository.init_event_schema(conn)
        event_repository.insert_raw_query_log(
            conn,
            event_type="search",
            anon_id="anon-1",
            raw_region_query="대산읍",
            raw_min_area_input="120",
            raw_max_area_input="500",
            raw_rent_only_input="true",
            raw_land_id_input=None,
            raw_land_address_input=None,
            raw_click_source_input=None,
            raw_payload_json="{}",
        )
        conn.commit()

    result = raw_query_export_service.export_raw_query_csv(
        RawQueryExportCommand(
            event_type="search",
            date_from=None,
            date_to=None,
            limit=100,
        )
    )
    assert "event_type" in result.csv_text
    assert "search" in result.csv_text
    assert result.row_count == 1
    assert result.effective_limit == 100


def test_raw_query_export_service_escapes_formula_like_cells(db_path: object) -> None:
    with db_connection() as conn:
        event_repository.init_event_schema(conn)
        event_repository.insert_raw_query_log(
            conn,
            event_type="search",
            anon_id="=anon",
            raw_region_query="+region",
            raw_min_area_input="-10",
            raw_max_area_input="@max",
            raw_rent_only_input="=true",
            raw_land_id_input=None,
            raw_land_address_input="=addr",
            raw_click_source_input="+map",
            raw_payload_json='{"raw":"=payload"}',
        )
        conn.commit()

    result = raw_query_export_service.export_raw_query_csv(
        RawQueryExportCommand(
            event_type="search",
            date_from=None,
            date_to=None,
            limit=100,
        )
    )
    assert "'=anon" in result.csv_text
    assert "'+region" in result.csv_text
    assert "'-10" in result.csv_text
    assert "'@max" in result.csv_text
    assert "'=true" in result.csv_text
    assert "'=addr" in result.csv_text
    assert "'+map" in result.csv_text


@pytest.mark.unit
def test_export_max_rows_cap_is_applied(db_path: object) -> None:
    """max_rows보다 큰 limit은 max_rows로 클램프된다."""
    with db_connection() as conn:
        event_repository.init_event_schema(conn)
        conn.commit()

    result = raw_query_export_service.export_raw_query_csv(
        RawQueryExportCommand(
            event_type="all",
            date_from=None,
            date_to=None,
            limit=999999,
            max_rows=500,
        )
    )
    assert result.effective_limit == 500


@pytest.mark.unit
def test_export_raises_503_on_query_timeout(db_path: object, monkeypatch: pytest.MonkeyPatch) -> None:
    """쿼리 실행 시간 초과(interrupted) 시 HTTP 503이 발생한다."""

    def _interrupted(*_args: object, **_kwargs: object) -> None:
        raise sqlite3.OperationalError("interrupted")

    monkeypatch.setattr(event_repository, "fetch_raw_query_logs", _interrupted)

    with db_connection() as conn:
        event_repository.init_event_schema(conn)
        conn.commit()

    with pytest.raises(ServiceError) as exc:
        raw_query_export_service.export_raw_query_csv(
            RawQueryExportCommand(
                event_type="all",
                date_from=None,
                date_to=None,
                limit=100,
                timeout_s=30.0,
            )
        )
    assert exc.value.status_code == 503


def test_raw_query_export_service_escapes_tab_and_pipe_prefix(db_path: object) -> None:
    with db_connection() as conn:
        event_repository.init_event_schema(conn)
        event_repository.insert_raw_query_log(
            conn,
            event_type="search",
            anon_id="\tanon",
            raw_region_query="|region",
            raw_min_area_input="100",
            raw_max_area_input="500",
            raw_rent_only_input="false",
            raw_land_id_input=None,
            raw_land_address_input=None,
            raw_click_source_input=None,
            raw_payload_json="{}",
        )
        conn.commit()

    result = raw_query_export_service.export_raw_query_csv(
        RawQueryExportCommand(
            event_type="search",
            date_from=None,
            date_to=None,
            limit=100,
        )
    )
    assert "'\tanon" in result.csv_text
    assert "'|region" in result.csv_text


def test_raw_query_export_service_invalid_event_type_raises_validation_error() -> None:
    with pytest.raises(ValidationError) as exc:
        raw_query_export_service.export_raw_query_csv(
            RawQueryExportCommand(
                event_type="invalid",
                date_from=None,
                date_to=None,
                limit=100,
            )
        )
    assert exc.value.status_code == 400
    assert exc.value.message == "event_type must be one of: all, search, land_click."
