from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ValidatedRawQueryExport:
    event_type_filter: str | None
    effective_limit: int
    created_at_from: str | None
    created_at_to: str | None
    timeout_s: float
