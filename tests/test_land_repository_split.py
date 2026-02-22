from app.db.connection import db_connection
from app.repositories import land_repository


def test_land_repository_insert_and_page_fetch(db_path: object) -> None:
    with db_connection(row_factory=True) as conn:
        land_repository.init_land_schema(conn)
        land_repository.delete_all(conn)
        land_repository.insert_land(
            conn,
            address="addr-1",
            land_type="답",
            area=12.5,
            adm_property="Y",
            gen_property="N",
            contact="010",
        )
        land_repository.insert_land(
            conn,
            address="addr-2",
            land_type="전",
            area=20.0,
            adm_property="N",
            gen_property="대부가능",
            contact="011",
        )
        missing = list(land_repository.fetch_missing_geom(conn))
        assert len(missing) == 2

        first_id, _ = missing[0]
        land_repository.update_geom(conn, first_id, '{"type":"Point","coordinates":[1,2]}')
        conn.commit()

        rows = land_repository.fetch_lands_with_geom_page(conn, after_id=None, limit=10)
        assert len(rows) == 1
        assert rows[0]["address"] == "addr-1"
        assert land_repository.count_missing_geom(conn) == 1
