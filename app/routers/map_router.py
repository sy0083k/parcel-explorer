import os
import sqlite3
import json
from fastapi import APIRouter, Request

# APIRouter 인스턴스 생성
router = APIRouter()

PUBLIC_LAND_FIELDS = {"id", "address", "land_type", "area", "adm_property", "gen_property"}

@router.get("/config")
async def get_config(request: Request):
    """지도를 초기화하는 데 필요한 설정값 반환"""
    config = request.app.state.config
    return {
        "vworldKey": config.VWORLD_KEY,
        "center": [config.CENTER_LON, config.CENTER_LAT],
        "zoom": config.DEFAULT_ZOOM
    }

@router.get("/lands")
async def get_lands(request: Request):
    config = request.app.state.config
    conn = sqlite3.connect(os.path.join(config.BASE_DIR, "data/database.db"))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    # 경계선 데이터(geom)가 있는 것만 지도에 표시
    cursor.execute("SELECT * FROM idle_land WHERE geom IS NOT NULL")
    rows = cursor.fetchall()
    conn.close()
    # 결과가 없으면 빈 리스트를 반환하여 프론트엔드 에러 방지
    features = []
    for row in rows:
        features.append({
            "type": "Feature",
            "geometry": json.loads(row['geom']),
            "properties": {key: row[key] for key in row.keys() if key in PUBLIC_LAND_FIELDS}
        })
    return {"type": "FeatureCollection", "features": features}