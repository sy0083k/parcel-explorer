#!/usr/bin/env python3
"""Export public parcel rows from data/database.db to seed/lands.json.

Only the `poi` table is exported. Event and visit logs never enter the seed.
"""
import json
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COLUMNS = ("address", "land_type", "area", "adm_property", "gen_property", "contact", "geom")


def main() -> None:
    conn = sqlite3.connect(f"file:{ROOT / 'data' / 'database.db'}?mode=ro", uri=True)
    try:
        rows = conn.execute(f"SELECT {', '.join(COLUMNS)} FROM poi ORDER BY id").fetchall()
    finally:
        conn.close()
    target = ROOT / "seed" / "lands.json"
    target.parent.mkdir(exist_ok=True)
    payload = [dict(zip(COLUMNS, row, strict=True)) for row in rows]
    target.write_text(json.dumps(payload, ensure_ascii=False, indent=0) + "\n", encoding="utf-8")
    print(f"exported {len(payload)} rows to {target}")


if __name__ == "__main__":
    main()
