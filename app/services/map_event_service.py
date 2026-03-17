from __future__ import annotations

import json
import re
from typing import Any

from app.db.connection import db_connection
from app.repositories import event_repository
from app.services.map_event_types import NormalizedLandClickMapEvent, NormalizedSearchMapEvent
from app.services.service_errors import ValidationError
from app.services.service_models import (
    LandClickMapEventCommand,
    MapEventCommand,
    SearchMapEventCommand,
    UnknownMapEventCommand,
)

EVENT_TYPE_SEARCH = "search"
EVENT_TYPE_LAND_CLICK = "land_click"
MIN_AREA_BUCKETS: list[tuple[float, float, str]] = [
    (0.0, 100.0, "0-99"),
    (100.0, 200.0, "100-199"),
    (200.0, 300.0, "200-299"),
    (300.0, 500.0, "300-499"),
    (500.0, 1000.0, "500-999"),
]
MIN_AREA_BUCKET_OVERFLOW = "1000+"
DIGIT_RE = re.compile(r"\d+")


def record_map_event(command: MapEventCommand) -> None:
    if isinstance(command, SearchMapEventCommand):
        persist_search_map_event(normalize_search_map_event(command))
        return

    if isinstance(command, LandClickMapEventCommand):
        persist_land_click_map_event(normalize_land_click_map_event(command))
        return

    if isinstance(command, UnknownMapEventCommand):
        raise ValidationError(status_code=400, message="Unsupported eventType.")

    raise ValidationError(status_code=400, message="Unsupported eventType.")


def normalize_search_map_event(command: SearchMapEventCommand) -> NormalizedSearchMapEvent:
    anon_id = normalize_anon_id(command.anon_id)
    min_area_value = parse_min_area(command.min_area)
    region_name = normalize_search_term(command.search_term) or None
    return NormalizedSearchMapEvent(
        anon_id=anon_id,
        min_area_value=min_area_value,
        min_area_bucket=min_area_bucket_for(min_area_value),
        region_name=region_name,
        raw_region_query=build_search_raw_region_query(command),
        raw_min_area_input=build_search_raw_min_area_input(command),
        raw_max_area_input=normalize_raw_text(command.raw_max_area_input, max_length=1000),
        raw_rent_only_input=normalize_raw_text(command.raw_rent_only, max_length=32),
        raw_payload_json=build_search_raw_payload_json(command),
    )


def normalize_land_click_map_event(command: LandClickMapEventCommand) -> NormalizedLandClickMapEvent:
    land_address = normalize_land_address(command.land_address)
    if not land_address:
        raise ValidationError(status_code=400, message="landAddress is required for land_click.")
    return NormalizedLandClickMapEvent(
        anon_id=normalize_anon_id(command.anon_id),
        land_address=land_address,
        raw_land_id_input=normalize_raw_text(command.land_id, max_length=64),
        raw_land_address_input=normalize_raw_text(command.land_address, max_length=1000),
        raw_click_source_input=normalize_raw_text(command.click_source, max_length=32),
        raw_payload_json=build_land_click_raw_payload_json(command),
    )


def persist_search_map_event(event: NormalizedSearchMapEvent) -> None:
    with db_connection() as conn:
        event_repository.insert_map_event(
            conn,
            event_type=EVENT_TYPE_SEARCH,
            anon_id=event.anon_id,
            region_name=event.region_name,
            min_area_value=event.min_area_value,
            min_area_bucket=event.min_area_bucket,
            region_source="user_input",
        )
        event_repository.insert_raw_query_log(
            conn,
            event_type=EVENT_TYPE_SEARCH,
            anon_id=event.anon_id,
            raw_region_query=event.raw_region_query,
            raw_min_area_input=event.raw_min_area_input,
            raw_max_area_input=event.raw_max_area_input,
            raw_rent_only_input=event.raw_rent_only_input,
            raw_land_id_input=None,
            raw_land_address_input=None,
            raw_click_source_input=None,
            raw_payload_json=event.raw_payload_json,
        )
        conn.commit()


def persist_land_click_map_event(event: NormalizedLandClickMapEvent) -> None:
    with db_connection() as conn:
        event_repository.insert_map_event(
            conn,
            event_type=EVENT_TYPE_LAND_CLICK,
            anon_id=event.anon_id,
            land_address=event.land_address,
        )
        event_repository.insert_raw_query_log(
            conn,
            event_type=EVENT_TYPE_LAND_CLICK,
            anon_id=event.anon_id,
            raw_region_query=None,
            raw_min_area_input=None,
            raw_max_area_input=None,
            raw_rent_only_input=None,
            raw_land_id_input=event.raw_land_id_input,
            raw_land_address_input=event.raw_land_address_input,
            raw_click_source_input=event.raw_click_source_input,
            raw_payload_json=event.raw_payload_json,
        )
        conn.commit()


def build_search_raw_region_query(command: SearchMapEventCommand) -> str | None:
    return normalize_raw_text(
        command.raw_search_term if command.raw_search_term is not None else command.search_term,
        max_length=1000,
    )


def build_search_raw_min_area_input(command: SearchMapEventCommand) -> str | None:
    return normalize_raw_text(
        command.raw_min_area_input if command.raw_min_area_input is not None else command.min_area,
        max_length=1000,
    )


def build_search_raw_payload_json(command: SearchMapEventCommand) -> str:
    return serialize_raw_payload(
        {
            "eventType": EVENT_TYPE_SEARCH,
            "anonId": command.anon_id,
            "minArea": command.min_area,
            "searchTerm": command.search_term,
            "rawSearchTerm": command.raw_search_term,
            "rawMinAreaInput": command.raw_min_area_input,
            "rawMaxAreaInput": command.raw_max_area_input,
            "rawRentOnly": command.raw_rent_only,
        }
    )


def build_land_click_raw_payload_json(command: LandClickMapEventCommand) -> str:
    return serialize_raw_payload(
        {
            "eventType": EVENT_TYPE_LAND_CLICK,
            "anonId": command.anon_id,
            "landAddress": command.land_address,
            "landId": command.land_id,
            "clickSource": command.click_source,
        }
    )


def get_admin_stats(limit: int = 10) -> dict[str, Any]:
    clamped_limit = max(1, min(int(limit), 50))

    with db_connection(row_factory=True) as conn:
        summary = event_repository.fetch_event_summary(conn)
        top_regions = event_repository.fetch_top_regions(conn, limit=clamped_limit)
        top_min_area_buckets = event_repository.fetch_top_min_area_buckets(conn, limit=clamped_limit)
        top_clicked_lands = event_repository.fetch_top_clicked_lands(conn, limit=clamped_limit)
        daily_trend = event_repository.fetch_daily_event_counts(conn)

    return {
        "summary": {
            "searchCount": int(summary["search_count"] or 0),
            "clickCount": int(summary["click_count"] or 0),
            "uniqueSessionCount": int(summary["unique_session_count"] or 0),
        },
        "topRegions": [{"region": str(row["region_name"]), "count": int(row["count"])} for row in top_regions],
        "topMinAreaBuckets": [
            {"bucket": str(row["min_area_bucket"]), "count": int(row["count"])} for row in top_min_area_buckets
        ],
        "topClickedLands": [
            {
                "address": str(row["land_address"]),
                "clickCount": int(row["click_count"]),
                "uniqueSessionCount": int(row["unique_session_count"]),
            }
            for row in top_clicked_lands
        ],
        "dailyTrend": [
            {
                "date": str(row["date"]),
                "searchCount": int(row["search_count"]),
                "clickCount": int(row["click_count"]),
            }
            for row in daily_trend
        ],
    }


def normalize_anon_id(raw: Any) -> str | None:
    if raw is None:
        return None
    value = str(raw).strip()
    if not value:
        return None
    return value[:128]


def normalize_land_address(raw: Any) -> str:
    if raw is None:
        return ""
    return str(raw).strip()[:500]


def parse_min_area(raw: Any) -> float:
    if raw is None or raw == "":
        return 0.0
    try:
        value = float(raw)
    except (TypeError, ValueError) as exc:
        raise ValidationError(status_code=400, message="minArea must be a number.") from exc
    if value < 0:
        raise ValidationError(status_code=400, message="minArea must be >= 0.")
    return value


def min_area_bucket_for(min_area: float) -> str:
    for lower, upper, label in MIN_AREA_BUCKETS:
        if lower <= min_area < upper:
            return label
    return MIN_AREA_BUCKET_OVERFLOW


def normalize_search_term(raw: Any) -> str:
    text = str(raw or "").strip()
    if not text:
        return ""
    without_digits = DIGIT_RE.sub("", text)
    return without_digits.strip()[:200]


def serialize_raw_payload(payload: dict[str, Any]) -> str:
    try:
        return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))[:4000]
    except (TypeError, ValueError):
        return "{}"


def normalize_raw_text(raw: Any, *, max_length: int) -> str | None:
    if raw is None:
        return None
    value = str(raw)
    return value[:max_length]
