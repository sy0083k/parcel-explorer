import sqlite3

from app.repositories import event_repository, job_repository, land_repository, web_visit_repository


def init_app_schema(conn: sqlite3.Connection) -> None:
    land_repository.init_land_schema(conn)
    job_repository.init_job_schema(conn)
    event_repository.init_event_schema(conn)
    web_visit_repository.init_web_visit_schema(conn)
