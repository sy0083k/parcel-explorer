from app.db.connection import db_connection
from app.repositories import event_repository


def test_event_repository_summary_and_raw_query_filter(db_path: object) -> None:
    with db_connection(row_factory=True) as conn:
        event_repository.init_event_schema(conn)
        event_repository.insert_map_event(
            conn,
            event_type="search",
            anon_id="anon-1",
            region_name="대산읍",
            min_area_value=120.0,
            min_area_bucket="100-199",
            region_source="user_input",
        )
        event_repository.insert_map_event(
            conn,
            event_type="land_click",
            anon_id="anon-1",
            land_address="충남 서산시 대산읍 독곶리 1-1",
        )
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

        summary = event_repository.fetch_event_summary(conn)
        assert int(summary["search_count"]) == 1
        assert int(summary["click_count"]) == 1

        search_logs = event_repository.fetch_raw_query_logs(
            conn,
            event_type="search",
            created_at_from=None,
            created_at_to=None,
            limit=10,
        )
        assert len(search_logs) == 1
        assert str(search_logs[0]["event_type"]) == "search"
