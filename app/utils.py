import json
import logging
import os
import sqlite3
import time
from urllib.parse import quote_plus

from app.clients.http_client import get_json_with_retry
from app.core import get_settings
from app.logging_utils import RequestIdFilter

logger = logging.getLogger(__name__)
logger.addFilter(RequestIdFilter())

settings = get_settings()
BASE_DIR = settings.base_dir


def init_db():
    """DB 초기화 로직 (lifespan에서 호출)"""
    data_dir = os.path.join(BASE_DIR, "data")
    os.makedirs(data_dir, exist_ok=True)
    conn = sqlite3.connect(os.path.join(data_dir, "database.db"))
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS idle_land (
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
    conn.commit()
    conn.close()


def get_parcel_geom(address: str, request_id: str = "-"):
    """주소를 받아 브이월드에서 필지 경계선(Polygon) 데이터를 가져옴"""
    encoded_address = quote_plus(address)
    geo_url = (
        "https://api.vworld.kr/req/address"
        f"?service=address&request=getcoord&address={encoded_address}"
        f"&key={settings.vworld_key}&type=parcel"
    )
    try:
        res = get_json_with_retry(
            geo_url,
            timeout_s=settings.vworld_timeout_s,
            retries=settings.vworld_retries,
            backoff_s=settings.vworld_backoff_s,
            request_id=request_id,
        )
        if res.get("response", {}).get("status") == "OK":
            x = res["response"]["result"]["point"]["x"]
            y = res["response"]["result"]["point"]["y"]

            wfs_url = (
                f"https://api.vworld.kr/req/wfs?key={settings.vworld_key}&service=WFS&version=1.1.0"
                f"&request=GetFeature&typename=lp_pa_cbnd_bubun,lp_pa_cbnd_bonbun"
                f"&bbox={x},{y},{x},{y}&srsname=EPSG:4326&output=application/json"
            )
            wfs_res = get_json_with_retry(
                wfs_url,
                timeout_s=settings.vworld_timeout_s,
                retries=settings.vworld_retries,
                backoff_s=settings.vworld_backoff_s,
                request_id=request_id,
            )
            if wfs_res.get("features"):
                return json.dumps(wfs_res["features"][0]["geometry"])
            return json.dumps({"type": "Point", "coordinates": [float(x), float(y)]})
    except Exception as exc:
        logger.warning("경계선 획득 실패 (%s): %s", address, str(exc), extra={"request_id": request_id})
    return None


def update_geoms(max_retries=5):
    """DB를 조회하여 geom이 없는 항목들에 대해 경계선 데이터를 다시 가져옵니다."""
    conn = sqlite3.connect(os.path.join(BASE_DIR, "data/database.db"))
    cursor = conn.cursor()

    retry_count = 0
    for attempt in range(1, max_retries + 1):
        cursor.execute("SELECT id, address FROM idle_land WHERE geom IS NULL")
        failed_items = cursor.fetchall()

        if not failed_items:
            break

        for item_id, address in failed_items:
            time.sleep(0.5)
            geom_data = get_parcel_geom(address)
            if geom_data:
                cursor.execute("UPDATE idle_land SET geom = ? WHERE id = ?", (geom_data, item_id))
                retry_count += 1
            conn.commit()

    cursor.execute("SELECT COUNT(*) FROM idle_land WHERE geom IS NULL")
    failed = cursor.fetchone()[0]
    conn.close()
    return retry_count, failed
