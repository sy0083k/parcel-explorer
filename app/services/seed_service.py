import json
import logging
from pathlib import Path

from app.db.connection import db_connection
from app.logging_utils import RequestIdFilter
from app.repositories import land_repository

logger = logging.getLogger(__name__)
logger.addFilter(RequestIdFilter())


def seed_lands_if_empty(seed_path: Path) -> int:
    """Load public parcel rows into an empty database. Returns the number of rows inserted."""
    if not seed_path.exists():
        logger.warning(
            "land seed file is missing",
            extra={"event": "startup.land_seed.missing", "actor": "system", "status": 500},
        )
        return 0

    rows = json.loads(seed_path.read_text(encoding="utf-8"))
    with db_connection() as conn:
        if land_repository.count_all_lands(conn) > 0:
            return 0
        for row in rows:
            land_repository.insert_land(
                conn,
                address=str(row["address"]),
                land_type=str(row["land_type"]),
                area=float(row["area"]),
                adm_property=str(row["adm_property"]),
                gen_property=str(row["gen_property"]),
                contact=str(row["contact"]),
                geom=str(row["geom"]) if row.get("geom") else None,
            )
        conn.commit()

    logger.info(
        "land seed loaded",
        extra={"event": "startup.land_seed.loaded", "actor": "system", "status": 200},
    )
    return len(rows)
