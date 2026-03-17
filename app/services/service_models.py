from __future__ import annotations

from dataclasses import dataclass
from typing import BinaryIO, Literal, TypeAlias


@dataclass(frozen=True)
class RequestContext:
    request_id: str
    actor: str
    client_ip: str
    csrf_valid: bool


@dataclass(frozen=True)
class UploadedFileInput:
    filename: str
    content_type: str
    file: BinaryIO


@dataclass(frozen=True)
class RequestMetadata:
    user_agent: str | None = None
    allowed_web_track_paths: tuple[str, ...] = ("/",)


@dataclass(frozen=True)
class SearchMapEventCommand:
    anon_id: object | None
    min_area: object | None
    search_term: object | None
    raw_search_term: object | None = None
    raw_min_area_input: object | None = None
    raw_max_area_input: object | None = None
    raw_rent_only: object | None = None


@dataclass(frozen=True)
class LandClickMapEventCommand:
    anon_id: object | None
    land_address: object | None
    land_id: object | None = None
    click_source: object | None = None


@dataclass(frozen=True)
class UnknownMapEventCommand:
    event_type: str
    anon_id: object | None


@dataclass(frozen=True)
class WebVisitEventCommand:
    metadata: RequestMetadata
    event_type: object | None
    anon_id: object | None
    session_id: object | None
    page_path: object | None
    page_query: object | None = None
    client_ts: object | None = None
    client_tz: object | None = None
    client_lang: object | None = None
    platform: object | None = None
    referrer_url: object | None = None
    referrer_domain: object | None = None
    utm_source: object | None = None
    utm_medium: object | None = None
    utm_campaign: object | None = None
    utm_term: object | None = None
    utm_content: object | None = None
    screen_width: object | None = None
    screen_height: object | None = None
    viewport_width: object | None = None
    viewport_height: object | None = None


@dataclass(frozen=True)
class RawQueryExportCommand:
    event_type: str
    date_from: str | None
    date_to: str | None
    limit: int
    max_rows: int = 100000
    timeout_s: float = 30.0


LimiterAction = Literal["none", "reset", "register_failure"]

MapEventCommand: TypeAlias = SearchMapEventCommand | LandClickMapEventCommand | UnknownMapEventCommand
