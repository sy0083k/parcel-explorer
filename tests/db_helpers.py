from app.db.connection import db_connection
from app.repositories import event_repository, job_repository, land_repository, web_visit_repository


def init_test_db() -> None:
    with db_connection() as conn:
        land_repository.init_land_schema(conn)
        job_repository.init_job_schema(conn)
        event_repository.init_event_schema(conn)
        web_visit_repository.init_web_visit_schema(conn)
        conn.commit()


def seed_lands(*, count: int, with_geom: bool = True) -> None:
    init_test_db()
    with db_connection() as conn:
        land_repository.delete_all(conn)
        for idx in range(count):
            land_repository.insert_land(
                conn,
                address=f"addr-{idx}",
                land_type="type",
                area=1.0 + idx,
                adm_property="adm",
                gen_property="gen",
                contact="010",
            )
        conn.commit()

        if with_geom:
            for item_id, _ in land_repository.fetch_missing_geom(conn):
                land_repository.update_geom(conn, item_id, '{"type":"Point","coordinates":[0,0]}')
            conn.commit()


def seed_browser_e2e_lands() -> None:
    init_test_db()
    with db_connection() as conn:
        land_repository.delete_all(conn)
        for row in (
            {
                "address": "충남 서산시 예천동 100-1",
                "land_type": "답",
                "area": 150.0,
                "adm_property": "O",
                "gen_property": "대부 가능",
                "contact": "010-1111-1111",
            },
            {
                "address": "충남 서산시 예천동 100-2",
                "land_type": "전",
                "area": 80.0,
                "adm_property": "O",
                "gen_property": "대부 가능",
                "contact": "010-2222-2222",
            },
            {
                "address": "충남 서산시 읍내동 55-1",
                "land_type": "대",
                "area": 220.0,
                "adm_property": "N",
                "gen_property": "매각",
                "contact": "010-3333-3333",
            },
        ):
            land_repository.insert_land(conn, **row)
        conn.commit()

        for item_id, _ in land_repository.fetch_missing_geom(conn):
            land_repository.update_geom(conn, item_id, '{"type":"Point","coordinates":[126.45,36.78]}')
        conn.commit()
