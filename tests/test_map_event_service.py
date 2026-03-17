from app.db.connection import db_connection
from app.repositories import event_repository
from app.services import map_event_service
from app.services.service_errors import ValidationError
from app.services.service_models import LandClickMapEventCommand, SearchMapEventCommand


def test_map_event_service_helpers() -> None:
    assert map_event_service.min_area_bucket_for(0) == "0-99"
    assert map_event_service.min_area_bucket_for(550) == "500-999"
    assert map_event_service.min_area_bucket_for(1000) == "1000+"
    assert map_event_service.normalize_search_term(" 성연면 2지구 ") == "성연면 지구"


def test_map_event_service_record_map_event(db_path: object) -> None:
    with db_connection() as conn:
        event_repository.init_event_schema(conn)
        conn.commit()

    map_event_service.record_map_event(
        SearchMapEventCommand(
            anon_id="anon-1",
            min_area=120,
            search_term="대산읍12",
            raw_search_term="대산읍12",
        )
    )

    with db_connection(row_factory=True) as conn:
        summary = event_repository.fetch_event_summary(conn)
        assert int(summary["search_count"] or 0) == 1


def test_normalize_search_map_event_builds_normalized_payload() -> None:
    normalized = map_event_service.normalize_search_map_event(
        SearchMapEventCommand(
            anon_id=" anon-1 ",
            min_area="120",
            search_term="대산읍12",
            raw_search_term=" 대산읍12 ",
            raw_min_area_input=" 120 ",
            raw_max_area_input=" 500 ",
            raw_rent_only="true",
        )
    )

    assert normalized.anon_id == "anon-1"
    assert normalized.min_area_value == 120.0
    assert normalized.min_area_bucket == "100-199"
    assert normalized.region_name == "대산읍"
    assert normalized.raw_region_query == " 대산읍12 "
    assert normalized.raw_min_area_input == " 120 "
    assert normalized.raw_max_area_input == " 500 "
    assert normalized.raw_rent_only_input == "true"


def test_normalize_land_click_map_event_builds_normalized_payload() -> None:
    normalized = map_event_service.normalize_land_click_map_event(
        LandClickMapEventCommand(
            anon_id=" anon-2 ",
            land_address=" 충남 서산시 대산읍 독곶리 1-1 ",
            land_id=99,
            click_source="map_click",
        )
    )

    assert normalized.anon_id == "anon-2"
    assert normalized.land_address == "충남 서산시 대산읍 독곶리 1-1"
    assert normalized.raw_land_id_input == "99"
    assert normalized.raw_land_address_input == " 충남 서산시 대산읍 독곶리 1-1 "
    assert normalized.raw_click_source_input == "map_click"


def test_map_event_service_invalid_land_click_raises_validation_error() -> None:
    try:
        map_event_service.record_map_event(
            LandClickMapEventCommand(anon_id="anon-1", land_address=None)
        )
        raise AssertionError("expected ValidationError")
    except ValidationError as exc:
        assert exc.status_code == 400
        assert exc.message == "landAddress is required for land_click."
