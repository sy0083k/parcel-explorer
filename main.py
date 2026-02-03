from fastapi import FastAPI, Response
from fastapi.staticfiles import StaticFiles
import sqlite3
import pandas as pd
import requests
import json
import httpx  # 지도 타일 프록시를 위해 필요
from contextlib import asynccontextmanager

# 보안을 위해 백엔드에만 키를 저장합니다.
VWORLD_KEY = "E8951B69-D1A8-3B9D-921F-25502BAE6D7B"
EXCEL_FILE = "유휴 공유재산 리스트 지자체 누리집 공개 서식.xlsx"

def get_parcel_geom(address):
    """주소를 받아 브이월드에서 필지 경계선(Polygon) 데이터를 가져옵니다."""
    geo_url = f"https://api.vworld.kr/req/address?service=address&request=getcoord&address={address}&key={VWORLD_KEY}&type=parcel"
    try:
        res = requests.get(geo_url).json()
        if res.get('response', {}).get('status') == 'OK':
            x = res['response']['result']['point']['x']
            y = res['response']['result']['point']['y']
            
            wfs_url = (
                f"https://api.vworld.kr/req/wfs?key={VWORLD_KEY}&service=WFS&version=1.1.0"
                f"&request=GetFeature&typename=lp_pa_cbnd_bubun,lp_pa_cbnd_bonbun"
                f"&bbox={x},{y},{x},{y}&srsname=EPSG:4326&output=application/json"
            )
            wfs_res = requests.get(wfs_url).json()
            if wfs_res.get('features'):
                return json.dumps(wfs_res['features'][0]['geometry'])
            else:
                return json.dumps({"type": "Point", "coordinates": [float(x), float(y)]})
    except Exception as e:
        print(f"경계선 획득 실패 ({address}): {e}")
    return None

@asynccontextmanager
async def lifespan(app: FastAPI):
    # DB 초기화 및 데이터 로딩 로직
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS idle_land (
            id INTEGER PRIMARY KEY,
            address TEXT,
            land_type TEXT,
            area REAL,
            description TEXT,
            contact TEXT,
            geom TEXT
        )
    ''')
    
    cursor.execute("SELECT count(*) FROM idle_land")
    if cursor.fetchone()[0] == 0:
        try:
            print("📦 엑셀 데이터를 분석하고 필지 경계선을 불러오는 중입니다...")
            df = pd.read_excel(EXCEL_FILE, sheet_name="목록")
            for _, row in df.head(20).iterrows(): # 테스트를 위해 20개만 로드
                addr = row['소재지(지번)']
                geom_data = get_parcel_geom(addr)
                if geom_data:
                    cursor.execute("""
                        INSERT INTO idle_land (address, land_type, area, description, contact, geom) 
                        VALUES (?,?,?,?,?,?)
                    """, (str(addr), str(row['(공부상)지목']), float(row['(공부상)면적(㎡)']), 
                          str(row['유휴사유 상세설명']), str(row['담당자연락처']), geom_data))
            conn.commit()
            print("✅ 데이터베이스 준비 완료!")
        except Exception as e:
            print(f"❌ 초기화 오류: {e}")
    conn.close()
    yield

app = FastAPI(lifespan=lifespan)

@app.get("/api/config")
async def get_config():
    """프론트엔드에 필요한 설정(API 키)을 안전하게 전달합니다."""
    return {"vworldKey": VWORLD_KEY}

@app.get("/api/lands")
async def get_lands():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM idle_land")
    rows = cursor.fetchall()
    conn.close()
    
    features = []
    for row in rows:
        features.append({
            "type": "Feature",
            "geometry": json.loads(row['geom']),
            "properties": dict(row)
        })
    return {"type": "FeatureCollection", "features": features}

app.mount("/", StaticFiles(directory="static", html=True), name="static")