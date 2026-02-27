from _pytest.monkeypatch import MonkeyPatch

from app.db.connection import db_connection
from app.repositories import poi_repository
from app.services import geo_service


def test_geo_service_updates_geom(db_path: object, monkeypatch: MonkeyPatch) -> None:
    with db_connection() as conn:
        poi_repository.init_db(conn)
        poi_repository.delete_all(conn)
        poi_repository.insert_land(
            conn,
            address="addr",
            land_type="type",
            area=1.0,
            adm_property="adm",
            gen_property="gen",
            contact="010",
        )
        conn.commit()

    class DummyClient:
        def __init__(self, *args: object, **kwargs: object) -> None:
            pass

        def get_parcel_geometry(self, address: str, request_id: str = "-") -> str | None:
            return '{"type":"Point","coordinates":[0,0]}'

    monkeypatch.setattr(geo_service, "VWorldClient", DummyClient)
    updated, failed = geo_service.update_geoms(max_retries=1)
    assert updated == 1
    assert failed == 0


def test_geo_service_handles_missing_geom(db_path: object, monkeypatch: MonkeyPatch) -> None:
    with db_connection() as conn:
        poi_repository.init_db(conn)
        poi_repository.delete_all(conn)
        poi_repository.insert_land(
            conn,
            address="addr",
            land_type="type",
            area=1.0,
            adm_property="adm",
            gen_property="gen",
            contact="010",
        )
        conn.commit()

    class DummyClient:
        def __init__(self, *args: object, **kwargs: object) -> None:
            pass

        def get_parcel_geometry(self, address: str, request_id: str = "-") -> str | None:
            return None

    monkeypatch.setattr(geo_service, "VWorldClient", DummyClient)
    updated, failed = geo_service.update_geoms(max_retries=1)
    assert updated == 0
    assert failed == 1


def test_geo_service_job_lifecycle(db_path: object, monkeypatch: MonkeyPatch) -> None:
    with db_connection() as conn:
        poi_repository.init_db(conn)
        poi_repository.delete_all(conn)
        poi_repository.insert_land(
            conn,
            address="addr",
            land_type="type",
            area=1.0,
            adm_property="adm",
            gen_property="gen",
            contact="010",
        )
        conn.commit()

    class DummyClient:
        def __init__(self, *args: object, **kwargs: object) -> None:
            pass

        def get_parcel_geometry(self, address: str, request_id: str = "-") -> str | None:
            return '{"type":"Point","coordinates":[1,1]}'

    monkeypatch.setattr(geo_service, "VWorldClient", DummyClient)

    job_id = geo_service.enqueue_geom_update_job()
    updated, failed = geo_service.run_geom_update_job(job_id, max_retries=1)
    assert updated == 1
    assert failed == 0

    with db_connection() as conn:
        row = conn.execute(
            "SELECT status, attempts, updated_count, failed_count FROM geom_update_jobs WHERE id = ?",
            (job_id,),
        ).fetchone()
    assert row is not None
    assert row[0] == "done"
    assert row[1] >= 1
    assert row[2] == 1
    assert row[3] == 0
