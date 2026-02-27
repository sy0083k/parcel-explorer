from app.db.connection import db_connection
from app.repositories import poi_repository


def test_poi_repository_crud(db_path: object) -> None:
    with db_connection() as conn:
        poi_repository.init_db(conn)
        poi_repository.delete_all(conn)
        poi_repository.insert_land(
            conn,
            address="addr",
            land_type="type",
            area=1.5,
            adm_property="adm",
            gen_property="gen",
            contact="010",
        )
        conn.commit()

        missing = poi_repository.fetch_missing_geom(conn)
        assert len(missing) == 1

        item_id, _ = missing[0]
        poi_repository.update_geom(conn, item_id, '{"type":"Point","coordinates":[0,0]}')
        conn.commit()

        assert poi_repository.count_missing_geom(conn) == 0


def test_map_event_repository_aggregations(db_path: object) -> None:
    with db_connection(row_factory=True) as conn:
        poi_repository.init_db(conn)
        poi_repository.insert_map_event(
            conn,
            event_type="search",
            anon_id="anon-a",
            region_name="대산읍",
            min_area_value=100.0,
            min_area_bucket="100-199",
            region_source="user_input",
        )
        poi_repository.insert_map_event(
            conn,
            event_type="search",
            anon_id="anon-b",
            region_name="대산읍",
            min_area_value=120.0,
            min_area_bucket="100-199",
            region_source="user_input",
        )
        poi_repository.insert_map_event(
            conn,
            event_type="search",
            anon_id="anon-c",
            region_name="성연면",
            min_area_value=50.0,
            min_area_bucket="0-99",
            region_source="derived_address",
        )
        poi_repository.insert_map_event(
            conn,
            event_type="land_click",
            anon_id="anon-a",
            land_address="서산시 대산읍 대로 1",
        )
        poi_repository.insert_map_event(
            conn,
            event_type="land_click",
            anon_id="anon-a",
            land_address="서산시 대산읍 대로 1",
        )
        conn.commit()

        summary = poi_repository.fetch_event_summary(conn)
        assert int(summary["search_count"]) == 3
        assert int(summary["click_count"]) == 2
        assert int(summary["unique_session_count"]) == 3

        top_regions = poi_repository.fetch_top_regions(conn, limit=10)
        assert len(top_regions) == 1
        assert top_regions[0]["region_name"] == "대산읍"
        assert int(top_regions[0]["count"]) == 2

        top_buckets = poi_repository.fetch_top_min_area_buckets(conn, limit=10)
        assert len(top_buckets) == 2
        assert top_buckets[0]["min_area_bucket"] == "100-199"

        top_lands = poi_repository.fetch_top_clicked_lands(conn, limit=10)
        assert len(top_lands) == 1
        assert top_lands[0]["land_address"] == "서산시 대산읍 대로 1"
        assert int(top_lands[0]["click_count"]) == 2
        assert int(top_lands[0]["unique_session_count"]) == 1


def test_web_visit_repository_aggregations(db_path: object) -> None:
    with db_connection(row_factory=True) as conn:
        poi_repository.init_db(conn)
        poi_repository.insert_web_visit_event(
            conn,
            anon_id="anon-a",
            session_id="session-a",
            event_type="visit_start",
            page_path="/",
            occurred_at="2026-02-20 00:00:00",
            client_tz="Asia/Seoul",
            user_agent="Mozilla/5.0",
            is_bot=False,
        )
        poi_repository.insert_web_visit_event(
            conn,
            anon_id="anon-a",
            session_id="session-a",
            event_type="visit_end",
            page_path="/",
            occurred_at="2026-02-20 00:10:00",
            client_tz="Asia/Seoul",
            user_agent="Mozilla/5.0",
            is_bot=False,
        )
        poi_repository.insert_web_visit_event(
            conn,
            anon_id="anon-b",
            session_id="session-b",
            event_type="visit_start",
            page_path="/",
            occurred_at="2026-02-20 01:00:00",
            client_tz="Asia/Seoul",
            user_agent="Mozilla/5.0",
            is_bot=False,
        )
        conn.commit()

        total_visitors = poi_repository.fetch_web_total_visitors(conn, page_path="/")
        assert total_visitors == 2

        daily_visitors = poi_repository.fetch_web_daily_visitors(
            conn,
            page_path="/",
            since_utc="2026-02-19 15:00:00",
            until_utc="2026-02-20 15:00:00",
        )
        assert daily_visitors == 2

        sessions = poi_repository.fetch_web_session_durations_seconds(
            conn,
            page_path="/",
            since_utc="2026-02-18 00:00:00",
        )
        assert len(sessions) == 2


def test_raw_query_log_repository_insert_and_filter(db_path: object) -> None:
    with db_connection(row_factory=True) as conn:
        poi_repository.init_db(conn)
        poi_repository.insert_raw_query_log(
            conn,
            event_type="search",
            anon_id="anon-a",
            raw_region_query="  예천동  ",
            raw_min_area_input=" 120 ",
            raw_max_area_input="300",
            raw_rent_only_input="true",
            raw_land_id_input=None,
            raw_land_address_input=None,
            raw_click_source_input=None,
            raw_payload_json='{"eventType":"search"}',
        )
        poi_repository.insert_raw_query_log(
            conn,
            event_type="land_click",
            anon_id="anon-b",
            raw_region_query=None,
            raw_min_area_input=None,
            raw_max_area_input=None,
            raw_rent_only_input=None,
            raw_land_id_input="15",
            raw_land_address_input="충남 서산시 ...",
            raw_click_source_input="nav_next",
            raw_payload_json='{"eventType":"land_click"}',
        )
        conn.commit()

        only_search = poi_repository.fetch_raw_query_logs(
            conn,
            event_type="search",
            created_at_from=None,
            created_at_to=None,
            limit=10,
        )
        assert len(only_search) == 1
        assert only_search[0]["event_type"] == "search"
        assert only_search[0]["raw_region_query"] == "  예천동  "

        only_click = poi_repository.fetch_raw_query_logs(
            conn,
            event_type="land_click",
            created_at_from=None,
            created_at_to=None,
            limit=10,
        )
        assert len(only_click) == 1
        assert only_click[0]["raw_land_id_input"] == "15"
        assert only_click[0]["raw_click_source_input"] == "nav_next"
