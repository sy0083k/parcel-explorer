import sqlite3
from typing import Iterable, Sequence

from app.repositories import event_repository, job_repository, land_repository, web_visit_repository


def init_db(conn: sqlite3.Connection) -> None:
    land_repository.init_land_schema(conn)
    job_repository.init_job_schema(conn)
    event_repository.init_event_schema(conn)
    web_visit_repository.init_web_visit_schema(conn)
    conn.commit()


def fetch_lands_with_geom(conn: sqlite3.Connection) -> Sequence[sqlite3.Row]:
    return land_repository.fetch_lands_with_geom(conn)


def fetch_lands_with_geom_page(
    conn: sqlite3.Connection,
    *,
    after_id: int | None,
    limit: int,
) -> Sequence[sqlite3.Row]:
    return land_repository.fetch_lands_with_geom_page(conn, after_id=after_id, limit=limit)


def delete_all(conn: sqlite3.Connection) -> None:
    land_repository.delete_all(conn)


def insert_land(
    conn: sqlite3.Connection,
    *,
    address: str,
    land_type: str,
    area: float,
    adm_property: str,
    gen_property: str,
    contact: str,
) -> None:
    land_repository.insert_land(
        conn,
        address=address,
        land_type=land_type,
        area=area,
        adm_property=adm_property,
        gen_property=gen_property,
        contact=contact,
    )


def fetch_missing_geom(conn: sqlite3.Connection, *, limit: int | None = None) -> Iterable[tuple[int, str]]:
    return land_repository.fetch_missing_geom(conn, limit=limit)


def update_geom(conn: sqlite3.Connection, item_id: int, geom: str) -> None:
    land_repository.update_geom(conn, item_id, geom)


def count_missing_geom(conn: sqlite3.Connection) -> int:
    return land_repository.count_missing_geom(conn)


def count_all_lands(conn: sqlite3.Connection) -> int:
    return land_repository.count_all_lands(conn)


def create_geom_update_job(conn: sqlite3.Connection) -> int:
    return job_repository.create_geom_update_job(conn)


def mark_geom_job_running(conn: sqlite3.Connection, job_id: int) -> None:
    job_repository.mark_geom_job_running(conn, job_id)


def mark_geom_job_done(conn: sqlite3.Connection, job_id: int, *, updated_count: int, failed_count: int) -> None:
    job_repository.mark_geom_job_done(conn, job_id, updated_count=updated_count, failed_count=failed_count)


def mark_geom_job_failed(
    conn: sqlite3.Connection,
    job_id: int,
    *,
    updated_count: int,
    failed_count: int,
    error_message: str,
) -> None:
    job_repository.mark_geom_job_failed(
        conn,
        job_id,
        updated_count=updated_count,
        failed_count=failed_count,
        error_message=error_message,
    )


def fetch_geom_job(conn: sqlite3.Connection, job_id: int) -> sqlite3.Row | None:
    return job_repository.fetch_geom_job(conn, job_id)


def fetch_latest_active_geom_job(conn: sqlite3.Connection) -> sqlite3.Row | None:
    return job_repository.fetch_latest_active_geom_job(conn)


def insert_map_event(
    conn: sqlite3.Connection,
    *,
    event_type: str,
    anon_id: str | None,
    land_address: str | None = None,
    region_name: str | None = None,
    min_area_value: float | None = None,
    min_area_bucket: str | None = None,
    region_source: str = "derived_address",
) -> None:
    event_repository.insert_map_event(
        conn,
        event_type=event_type,
        anon_id=anon_id,
        land_address=land_address,
        region_name=region_name,
        min_area_value=min_area_value,
        min_area_bucket=min_area_bucket,
        region_source=region_source,
    )


def insert_raw_query_log(
    conn: sqlite3.Connection,
    *,
    event_type: str,
    anon_id: str | None,
    raw_region_query: str | None,
    raw_min_area_input: str | None,
    raw_max_area_input: str | None,
    raw_rent_only_input: str | None,
    raw_land_id_input: str | None,
    raw_land_address_input: str | None,
    raw_click_source_input: str | None,
    raw_payload_json: str,
) -> None:
    event_repository.insert_raw_query_log(
        conn,
        event_type=event_type,
        anon_id=anon_id,
        raw_region_query=raw_region_query,
        raw_min_area_input=raw_min_area_input,
        raw_max_area_input=raw_max_area_input,
        raw_rent_only_input=raw_rent_only_input,
        raw_land_id_input=raw_land_id_input,
        raw_land_address_input=raw_land_address_input,
        raw_click_source_input=raw_click_source_input,
        raw_payload_json=raw_payload_json,
    )


def fetch_event_summary(conn: sqlite3.Connection) -> sqlite3.Row:
    return event_repository.fetch_event_summary(conn)


def fetch_top_regions(conn: sqlite3.Connection, *, limit: int) -> Sequence[sqlite3.Row]:
    return event_repository.fetch_top_regions(conn, limit=limit)


def fetch_top_min_area_buckets(conn: sqlite3.Connection, *, limit: int) -> Sequence[sqlite3.Row]:
    return event_repository.fetch_top_min_area_buckets(conn, limit=limit)


def fetch_top_clicked_lands(conn: sqlite3.Connection, *, limit: int) -> Sequence[sqlite3.Row]:
    return event_repository.fetch_top_clicked_lands(conn, limit=limit)


def fetch_raw_query_logs(
    conn: sqlite3.Connection,
    *,
    event_type: str | None,
    created_at_from: str | None,
    created_at_to: str | None,
    limit: int,
) -> Sequence[sqlite3.Row]:
    return event_repository.fetch_raw_query_logs(
        conn,
        event_type=event_type,
        created_at_from=created_at_from,
        created_at_to=created_at_to,
        limit=limit,
    )


def fetch_daily_event_counts(conn: sqlite3.Connection) -> Sequence[sqlite3.Row]:
    return event_repository.fetch_daily_event_counts(conn)


def insert_web_visit_event(
    conn: sqlite3.Connection,
    *,
    anon_id: str,
    session_id: str,
    event_type: str,
    page_path: str,
    occurred_at: str,
    client_tz: str | None,
    user_agent: str | None,
    is_bot: bool,
    page_query: str | None = None,
    client_lang: str | None = None,
    platform: str | None = None,
    referrer_url: str | None = None,
    referrer_domain: str | None = None,
    utm_source: str | None = None,
    utm_medium: str | None = None,
    utm_campaign: str | None = None,
    utm_term: str | None = None,
    utm_content: str | None = None,
    screen_width: int | None = None,
    screen_height: int | None = None,
    viewport_width: int | None = None,
    viewport_height: int | None = None,
    browser_family: str = "other",
    device_type: str = "unknown",
    os_family: str = "other",
) -> None:
    web_visit_repository.insert_web_visit_event(
        conn,
        anon_id=anon_id,
        session_id=session_id,
        event_type=event_type,
        page_path=page_path,
        page_query=page_query,
        occurred_at=occurred_at,
        client_tz=client_tz,
        client_lang=client_lang,
        platform=platform,
        user_agent=user_agent,
        is_bot=is_bot,
        referrer_url=referrer_url,
        referrer_domain=referrer_domain,
        utm_source=utm_source,
        utm_medium=utm_medium,
        utm_campaign=utm_campaign,
        utm_term=utm_term,
        utm_content=utm_content,
        screen_width=screen_width,
        screen_height=screen_height,
        viewport_width=viewport_width,
        viewport_height=viewport_height,
        browser_family=browser_family,
        device_type=device_type,
        os_family=os_family,
    )


def fetch_web_total_visitors(conn: sqlite3.Connection, *, page_path: str) -> int:
    return web_visit_repository.fetch_web_total_visitors(conn, page_paths=(page_path,))


def fetch_web_daily_visitors(conn: sqlite3.Connection, *, page_path: str, since_utc: str, until_utc: str) -> int:
    return web_visit_repository.fetch_web_daily_visitors(
        conn,
        page_paths=(page_path,),
        since_utc=since_utc,
        until_utc=until_utc,
    )


def fetch_web_session_durations_seconds(
    conn: sqlite3.Connection,
    *,
    page_path: str,
    since_utc: str,
) -> Sequence[sqlite3.Row]:
    return web_visit_repository.fetch_web_session_durations_seconds(
        conn,
        page_paths=(page_path,),
        since_utc=since_utc,
    )


def fetch_web_daily_unique_visitors_trend(
    conn: sqlite3.Connection,
    *,
    page_path: str,
    since_utc: str,
) -> Sequence[sqlite3.Row]:
    return web_visit_repository.fetch_web_daily_unique_visitors_trend(
        conn,
        page_paths=(page_path,),
        since_utc=since_utc,
    )
