from app.db.connection import db_connection
from app.repositories import idle_land_repository


def test_idle_land_repository_crud(db_path):
    with db_connection() as conn:
        idle_land_repository.init_db(conn)
        idle_land_repository.delete_all(conn)
        idle_land_repository.insert_land(
            conn,
            address="addr",
            land_type="type",
            area=1.5,
            adm_property="adm",
            gen_property="gen",
            contact="010",
        )
        conn.commit()

        missing = idle_land_repository.fetch_missing_geom(conn)
        assert len(missing) == 1

        item_id, _ = missing[0]
        idle_land_repository.update_geom(conn, item_id, '{"type":"Point","coordinates":[0,0]}')
        conn.commit()

        assert idle_land_repository.count_missing_geom(conn) == 0
