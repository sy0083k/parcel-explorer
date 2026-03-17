import sqlite3
from typing import Iterable, Sequence


def init_land_schema(conn: sqlite3.Connection) -> None:
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS poi (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            address TEXT,
            land_type TEXT,
            area REAL,
            adm_property TEXT,
            gen_property TEXT,
            contact TEXT,
            geom TEXT
        )
        """
    )


def fetch_lands_with_geom(conn: sqlite3.Connection) -> Sequence[sqlite3.Row]:
    init_land_schema(conn)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM poi WHERE geom IS NOT NULL")
    return cursor.fetchall()


def fetch_lands_with_geom_page(
    conn: sqlite3.Connection,
    *,
    after_id: int | None,
    limit: int,
) -> Sequence[sqlite3.Row]:
    init_land_schema(conn)
    cursor = conn.cursor()
    if after_id is None:
        cursor.execute("SELECT * FROM poi WHERE geom IS NOT NULL ORDER BY id LIMIT ?", (limit,))
    else:
        cursor.execute(
            "SELECT * FROM poi WHERE geom IS NOT NULL AND id > ? ORDER BY id LIMIT ?",
            (after_id, limit),
        )
    return cursor.fetchall()


def delete_all(conn: sqlite3.Connection) -> None:
    init_land_schema(conn)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM poi")


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
    init_land_schema(conn)
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO poi (address, land_type, area, adm_property, gen_property, contact, geom)
        VALUES (?,?,?,?,?,?,NULL)
        """,
        (
            address,
            land_type,
            area,
            adm_property,
            gen_property,
            contact,
        ),
    )


def fetch_missing_geom(conn: sqlite3.Connection, *, limit: int | None = None) -> Iterable[tuple[int, str]]:
    init_land_schema(conn)
    cursor = conn.cursor()
    if limit is None:
        cursor.execute("SELECT id, address FROM poi WHERE geom IS NULL ORDER BY id")
    else:
        cursor.execute("SELECT id, address FROM poi WHERE geom IS NULL ORDER BY id LIMIT ?", (limit,))
    return cursor.fetchall()


def update_geom(conn: sqlite3.Connection, item_id: int, geom: str) -> None:
    init_land_schema(conn)
    cursor = conn.cursor()
    cursor.execute("UPDATE poi SET geom = ? WHERE id = ?", (geom, item_id))


def count_missing_geom(conn: sqlite3.Connection) -> int:
    init_land_schema(conn)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM poi WHERE geom IS NULL")
    row = cursor.fetchone()
    return int(row[0]) if row else 0


def count_all_lands(conn: sqlite3.Connection) -> int:
    init_land_schema(conn)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM poi")
    row = cursor.fetchone()
    return int(row[0]) if row else 0
