from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class NormalizedSearchMapEvent:
    anon_id: str | None
    min_area_value: float
    min_area_bucket: str
    region_name: str | None
    raw_region_query: str | None
    raw_min_area_input: str | None
    raw_max_area_input: str | None
    raw_rent_only_input: str | None
    raw_payload_json: str


@dataclass(frozen=True)
class NormalizedLandClickMapEvent:
    anon_id: str | None
    land_address: str
    raw_land_id_input: str | None
    raw_land_address_input: str | None
    raw_click_source_input: str | None
    raw_payload_json: str
