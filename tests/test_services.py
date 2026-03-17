from app.db.connection import db_connection
from app.repositories import land_repository, poi_repository
from app.services import land_service


def test_land_service_returns_geojson(db_path: object) -> None:
    with db_connection() as conn:
        poi_repository.init_db(conn)
        land_repository.delete_all(conn)
        land_repository.insert_land(
            conn,
            address="addr",
            land_type="type",
            area=1.5,
            adm_property="adm",
            gen_property="gen",
            contact="010",
        )
        conn.commit()

        missing = land_repository.fetch_missing_geom(conn)
        item_id, _ = missing[0]
        land_repository.update_geom(conn, item_id, '{"type":"Point","coordinates":[1,2]}')
        conn.commit()

    payload = land_service.get_public_land_features()
    assert payload["type"] == "FeatureCollection"
    assert len(payload["features"]) == 1
    feature = payload["features"][0]
    assert feature["geometry"]["type"] == "Point"
