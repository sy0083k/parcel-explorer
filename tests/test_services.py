from app.db.connection import db_connection
from app.repositories import land_repository
from app.services import land_service
from tests.db_helpers import init_test_db


def _insert_land_with_geom(
    *,
    address: str,
    land_type: str = "type",
    area: float = 1.5,
    adm_property: str = "adm",
    gen_property: str = "gen",
    contact: str = "010",
    geom: str = '{"type":"Point","coordinates":[1,2]}',
) -> int:
    with db_connection() as conn:
        land_repository.insert_land(
            conn,
            address=address,
            land_type=land_type,
            area=area,
            adm_property=adm_property,
            gen_property=gen_property,
            contact=contact,
        )
        conn.commit()

        missing = land_repository.fetch_missing_geom(conn)
        item_id, _ = next(item for item in missing if item[1] == address)
        land_repository.update_geom(conn, item_id, geom)
        conn.commit()
        return item_id


def test_land_service_returns_geojson(db_path: object) -> None:
    init_test_db()
    with db_connection() as conn:
        land_repository.delete_all(conn)
        conn.commit()

    _insert_land_with_geom(address="addr")

    payload = land_service.get_public_land_features()
    assert payload["type"] == "FeatureCollection"
    assert len(payload["features"]) == 1
    feature = payload["features"][0]
    assert feature["geometry"]["type"] == "Point"


def test_land_service_returns_empty_feature_collection_when_no_rows(db_path: object) -> None:
    init_test_db()
    with db_connection() as conn:
        land_repository.delete_all(conn)
        conn.commit()

    payload = land_service.get_public_land_features()

    assert payload == {"type": "FeatureCollection", "features": []}


def test_land_service_filters_properties_to_public_fields(db_path: object) -> None:
    init_test_db()
    with db_connection() as conn:
        land_repository.delete_all(conn)
        conn.commit()

    item_id = _insert_land_with_geom(
        address="addr-public",
        land_type="답",
        area=12.5,
        adm_property="Y",
        gen_property="대부가능",
        contact="010-1111-1111",
    )

    payload = land_service.get_public_land_features()

    assert len(payload["features"]) == 1
    feature = payload["features"][0]
    assert feature["properties"] == {
        "id": item_id,
        "address": "addr-public",
        "land_type": "답",
        "area": 12.5,
        "adm_property": "Y",
        "gen_property": "대부가능",
        "contact": "010-1111-1111",
    }
    assert "geom" not in feature["properties"]


def test_land_service_page_sets_next_cursor_only_when_page_is_full(db_path: object) -> None:
    init_test_db()
    with db_connection() as conn:
        land_repository.delete_all(conn)
        conn.commit()

    first_id = _insert_land_with_geom(address="addr-1", area=1.0)
    second_id = _insert_land_with_geom(address="addr-2", area=2.0)
    third_id = _insert_land_with_geom(address="addr-3", area=3.0)

    first_page = land_service.get_public_land_features_page(cursor=None, limit=2)

    assert first_page["type"] == "FeatureCollection"
    assert len(first_page["features"]) == 2
    assert [feature["properties"]["id"] for feature in first_page["features"]] == [first_id, second_id]
    assert first_page["nextCursor"] == str(second_id)

    second_page = land_service.get_public_land_features_page(cursor=second_id, limit=2)

    assert second_page["type"] == "FeatureCollection"
    assert len(second_page["features"]) == 1
    assert second_page["features"][0]["properties"]["id"] == third_id
    assert second_page["nextCursor"] is None
