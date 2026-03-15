from __future__ import annotations

from typing import Any, cast

import pandas as pd

REQUIRED_COLUMNS = [
    "소재지(지번)",
    "(공부상)지목",
    "(공부상)면적(㎡)",
    "행정재산",
    "일반재산",
    "담당자연락처",
]

MAX_ERROR_REPORT = 100


def validate_required_columns(df: pd.DataFrame) -> list[str]:
    return [col for col in REQUIRED_COLUMNS if col not in df.columns]


def normalize_upload_rows(
    df: pd.DataFrame,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], int]:
    normalized: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    total_errors = 0

    for idx, row in df.iterrows():
        row_num = int(cast(Any, idx)) + 1
        address = _to_str(row.get("소재지(지번)"))
        land_type = _to_str(row.get("(공부상)지목"))
        area_raw = row.get("(공부상)면적(㎡)")
        adm_property = _to_str(row.get("행정재산"))
        gen_property = _to_str(row.get("일반재산"))
        contact = _to_str(row.get("담당자연락처"))

        if not address:
            total_errors += 1
            _append_error(errors, row_num, "address", "missing", address)
            continue

        area = _parse_area(area_raw, row_num, errors)
        if area is None:
            total_errors += 1
            continue

        normalized.append(
            {
                "address": address,
                "land_type": land_type,
                "area": area,
                "adm_property": adm_property,
                "gen_property": gen_property,
                "contact": contact,
            }
        )

    return normalized, errors, total_errors


def _parse_area(value: Any, row_num: int, errors: list[dict[str, Any]]) -> float | None:
    if pd.isna(value):
        _append_error(errors, row_num, "area", "missing", value)
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        _append_error(errors, row_num, "area", "invalid", value)
        return None


def _to_str(value: Any) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    return str(value).strip()


def _append_error(
    errors: list[dict[str, Any]], row_num: int, field: str, code: str, value: Any
) -> None:
    if len(errors) >= MAX_ERROR_REPORT:
        return
    errors.append(
        {
            "row": row_num,
            "field": field,
            "code": code,
            "value": "" if value is None else str(value),
        }
    )


_MAGIC_BYTES: dict[str, bytes] = {
    ".xlsx": b"PK\x03\x04",
    ".xls": b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1",
}


def check_excel_magic_bytes(header: bytes, filename: str) -> bool:
    """파일 첫 바이트가 선언된 확장자의 시그니처와 일치하는지 검증한다."""
    for ext, magic in _MAGIC_BYTES.items():
        if filename.endswith(ext):
            return header[: len(magic)] == magic
    return False
