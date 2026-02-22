from app.db.connection import db_connection
from app.repositories import event_repository
from app.services import map_event_service


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
        {
            "eventType": "search",
            "anonId": "anon-1",
            "minArea": 120,
            "searchTerm": "대산읍12",
            "rawSearchTerm": "대산읍12",
        }
    )

    with db_connection(row_factory=True) as conn:
        summary = event_repository.fetch_event_summary(conn)
        assert int(summary["search_count"] or 0) == 1
