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


def test_recover_no_stale_jobs(db_path: object) -> None:
    with db_connection() as conn:
        poi_repository.init_db(conn)
        conn.commit()
    assert geo_service.recover_interrupted_geom_jobs() is None


def test_recover_stale_jobs_no_missing_geom(db_path: object) -> None:
    with db_connection() as conn:
        poi_repository.init_db(conn)
        poi_repository.delete_all(conn)
        job_id = poi_repository.create_geom_update_job(conn)
        conn.commit()

    assert geo_service.recover_interrupted_geom_jobs() is None

    with db_connection() as conn:
        row = conn.execute(
            "SELECT status, error_message FROM geom_update_jobs WHERE id = ?", (job_id,)
        ).fetchone()
    assert row is not None
    assert row[0] == "failed"
    assert "재시작" in (row[1] or "")


def test_recover_stale_jobs_with_missing_geom(db_path: object) -> None:
    with db_connection() as conn:
        poi_repository.init_db(conn)
        poi_repository.delete_all(conn)
        poi_repository.insert_land(
            conn, address="addr", land_type="t", area=1.0,
            adm_property="a", gen_property="g", contact="010",
        )
        old_job_id = poi_repository.create_geom_update_job(conn)
        poi_repository.mark_geom_job_running(conn, old_job_id)
        conn.commit()

    new_job_id = geo_service.recover_interrupted_geom_jobs()
    assert new_job_id is not None
    assert new_job_id != old_job_id

    with db_connection() as conn:
        old_row = conn.execute(
            "SELECT status FROM geom_update_jobs WHERE id = ?", (old_job_id,)
        ).fetchone()
        new_row = conn.execute(
            "SELECT status FROM geom_update_jobs WHERE id = ?", (new_job_id,)
        ).fetchone()
    assert old_row[0] == "failed"
    assert new_row[0] == "pending"


def test_recover_no_stale_jobs_with_missing_geom(db_path: object) -> None:
    with db_connection() as conn:
        poi_repository.init_db(conn)
        poi_repository.delete_all(conn)
        poi_repository.insert_land(
            conn, address="addr", land_type="t", area=1.0,
            adm_property="a", gen_property="g", contact="010",
        )
        conn.commit()
    assert geo_service.recover_interrupted_geom_jobs() is None


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
