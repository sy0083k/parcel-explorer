from __future__ import annotations

from dataclasses import dataclass
from typing import Any, BinaryIO, Literal


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
class MapEventCommand:
    payload: dict[str, Any]


@dataclass(frozen=True)
class WebVisitEventCommand:
    payload: dict[str, Any]
    metadata: RequestMetadata


@dataclass(frozen=True)
class RawQueryExportCommand:
    event_type: str
    date_from: str | None
    date_to: str | None
    limit: int
    max_rows: int = 100000
    timeout_s: float = 30.0


LimiterAction = Literal["none", "reset", "register_failure"]
