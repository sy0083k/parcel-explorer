from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import datetime, timedelta
from io import StringIO

from fastapi import HTTPException

from app.db.connection import db_connection
from app.repositories import event_repository

EVENT_TYPE_SEARCH = "search"
EVENT_TYPE_LAND_CLICK = "land_click"
CSV_FORMULA_PREFIXES = ("=", "+", "-", "@")


@dataclass(frozen=True)
class RawQueryCsvExportResult:
    csv_text: str
    row_count: int
    effective_limit: int


def export_raw_query_csv(
    *,
    event_type: str,
    date_from: str | None,
    date_to: str | None,
    limit: int,
) -> RawQueryCsvExportResult:
    if event_type not in {"all", EVENT_TYPE_SEARCH, EVENT_TYPE_LAND_CLICK}:
        raise HTTPException(status_code=400, detail="event_type must be one of: all, search, land_click.")

    clamped_limit = max(1, min(int(limit), 100000))
    created_at_from = parse_date_start(date_from)
    created_at_to = parse_date_end_exclusive(date_to)
    if created_at_from is not None and created_at_to is not None and created_at_from >= created_at_to:
        raise HTTPException(status_code=400, detail="date_from must be earlier than or equal to date_to.")

    with db_connection(row_factory=True) as conn:
        rows = event_repository.fetch_raw_query_logs(
            conn,
            event_type=None if event_type == "all" else event_type,
            created_at_from=created_at_from,
            created_at_to=created_at_to,
            limit=clamped_limit,
        )

    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(
        [
            "id",
            "created_at",
            "event_type",
            "anon_id",
            "raw_region_query",
            "raw_min_area_input",
            "raw_max_area_input",
            "raw_rent_only_input",
            "raw_land_id_input",
            "raw_land_address_input",
            "raw_click_source_input",
            "raw_payload_json",
        ]
    )
    for row in rows:
        writer.writerow(
            [
                int(row["id"]),
                _safe_csv_string(row["created_at"]),
                _safe_csv_string(row["event_type"]),
                _safe_csv_string(row["anon_id"]),
                _safe_csv_string(row["raw_region_query"]),
                _safe_csv_string(row["raw_min_area_input"]),
                _safe_csv_string(row["raw_max_area_input"]),
                _safe_csv_string(row["raw_rent_only_input"]),
                _safe_csv_string(row["raw_land_id_input"]),
                _safe_csv_string(row["raw_land_address_input"]),
                _safe_csv_string(row["raw_click_source_input"]),
                _safe_csv_string(row["raw_payload_json"]),
            ]
        )
    return RawQueryCsvExportResult(
        csv_text=output.getvalue(),
        row_count=len(rows),
        effective_limit=clamped_limit,
    )


def _safe_csv_string(value: object) -> str:
    text = str(value or "")
    if text.startswith(CSV_FORMULA_PREFIXES):
        return f"'{text}"
    return text


def parse_date_start(raw: str | None) -> str | None:
    if raw is None or raw.strip() == "":
        return None
    try:
        parsed = datetime.strptime(raw, "%Y-%m-%d")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="date_from must be YYYY-MM-DD.") from exc
    return parsed.strftime("%Y-%m-%d 00:00:00")


def parse_date_end_exclusive(raw: str | None) -> str | None:
    if raw is None or raw.strip() == "":
        return None
    try:
        parsed = datetime.strptime(raw, "%Y-%m-%d")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="date_to must be YYYY-MM-DD.") from exc
    return (parsed + timedelta(days=1)).strftime("%Y-%m-%d 00:00:00")
