from __future__ import annotations

from dataclasses import dataclass
from typing import BinaryIO, Literal


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


LimiterAction = Literal["none", "reset", "register_failure"]
