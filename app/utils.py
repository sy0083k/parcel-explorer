import sqlite3
import requests
import json
import time
import os
VWORLD_KEY = os.getenv("VWORLD_KEY")
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def init_db():
    """DB 초기화 로직 (lifespan에서 호출)"""
    data_dir = os.path.join(BASE_DIR, "data")
    os.makedirs(data_dir, exist_ok=True)
    conn = sqlite3.connect(os.path.join(data_dir, "database.db"))
    cursor = conn.cursor()
    cursor.execute('''
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
    ''')
    conn.commit()
    conn.close()

def get_parcel_geom(address):
    """주소를 받아 브이월드에서 필지 경계선(Polygon) 데이터를 가져옴"""
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

def update_geoms(max_retries=5):
    """DB를 조회하여 geom이 없는 항목들에 대해 경계선 데이터를 다시 가져옵니다."""
    conn = sqlite3.connect(os.path.join(BASE_DIR, "data/database.db"))
    cursor = conn.cursor()
    
    retry_count = 0
    for attempt in range(1, max_retries + 1):
        # 1. geom 데이터가 없는 항목들 조회
        cursor.execute("SELECT id, address FROM idle_land WHERE geom IS NULL")
        failed_items = cursor.fetchall()
        
        if not failed_items: break
        
        for item_id, address in failed_items:
            # API 부하 방지를 위한 미세 지연 (선택 사항)
            time.sleep(0.5) 
            geom_data = get_parcel_geom(address)
            if geom_data:
                cursor.execute("UPDATE idle_land SET geom = ? WHERE id = ?", (geom_data, item_id))
                retry_count += 1                
            conn.commit()
    
    # 최종 상태 확인 (여전히 실패한 건수 계산)
    cursor.execute("SELECT COUNT(*) FROM idle_land WHERE geom IS NULL")
    failed = cursor.fetchone()[0]    
    conn.close()
    return retry_count, failed