import os
import sqlite3
import pandas as pd
import requests
import json
import secrets
from dotenv import load_dotenv
from fastapi import FastAPI, Depends, HTTPException, status, UploadFile, File, Request
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import FileResponse, JSONResponse, HTMLResponse
from contextlib import asynccontextmanager

# 1. 환경 설정 및 보안 변수
load_dotenv()
VWORLD_KEY = os.getenv("VWORLD_KEY")
ADMIN_ID = os.getenv("ADMIN_ID")
ADMIN_PW = os.getenv("ADMIN_PW")

security = HTTPBasic()
templates = Jinja2Templates(directory="templates")

# --- [함수] 주소로 필지 경계선 가져오기 ---
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

# --- [인증] 관리자 확인 함수 ---
def get_current_username(credentials: HTTPBasicCredentials = Depends(security)):
    is_user_ok = secrets.compare_digest(credentials.username, ADMIN_ID)
    is_pass_ok = secrets.compare_digest(credentials.password, ADMIN_PW)
    if not (is_user_ok and is_pass_ok):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="로그인 실패",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username

# --- [서버 시작 시 실행] DB 및 테이블 생성 ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    # 서버 실행 시 database.db 파일과 테이블이 없으면 생성합니다.
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS idle_land (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            address TEXT,
            land_type TEXT,
            area REAL,
            description TEXT,
            contact TEXT,
            geom TEXT
        )
    ''')
    conn.commit()
    conn.close()
    yield

app = FastAPI(lifespan=lifespan)

# --- [API] 관리자 페이지 및 업로드 ---
@app.get("/admin", response_class=HTMLResponse)
async def get_admin_page(request: Request, username: str = Depends(get_current_username)):
    """
    HTTP Basic Auth 인증이 완료된 사용자에게만 
    templates 폴더 안의 admin.html을 렌더링해서 보여줍니다.
    """
    return templates.TemplateResponse("admin.html", {"request": request})

@app.post("/api/admin/upload")
async def upload_excel(file: UploadFile = File(...), username: str = Depends(get_current_username)):
    try:
        df = pd.read_excel(file.file, sheet_name="목록")
        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()
        cursor.execute("DELETE FROM idle_land") # 기존 데이터 초기화
        
        count = 0        
        for _, row in df.head(20).iterrows(): # 테스트를 위해 20개만 로드
            addr = row['소재지(지번)']
            geom_data = get_parcel_geom(addr)
            if geom_data:
                cursor.execute("""
                    INSERT INTO idle_land (address, land_type, area, description, contact, geom) 
                    VALUES (?,?,?,?,?,?)
                """, (str(addr), str(row['(공부상)지목']), float(row['(공부상)면적(㎡)']), 
                      str(row['유휴사유 상세설명']), str(row['담당자연락처']), geom_data))
                count += 1
        conn.commit()
        conn.close()
        return {"success": True, "message": f"{count}건의 데이터 업데이트 완료"}    

    except Exception as e:
        return JSONResponse(status_code=500, content={"success": False, "message": str(e)})

# --- [API] 데이터 조회 ---
@app.get("/api/config")
async def get_config():
    return {"vworldKey": VWORLD_KEY}

@app.get("/api/lands")
async def get_lands():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM idle_land")
    rows = cursor.fetchall()
    conn.close()
    # 결과가 없으면 빈 리스트를 반환하여 프론트엔드 에러 방지
    features = []
    for row in rows:
        features.append({
            "type": "Feature",
            "geometry": json.loads(row['geom']),
            "properties": dict(row)
        })
    return {"type": "FeatureCollection", "features": features}

# --- [정적 파일 서빙] ---
@app.get("/")
async def read_index():
    return FileResponse("index.html")

# 기타 파일들(이미지, CSS 등)을 위해 현재 폴더를 매핑
app.mount("/", StaticFiles(directory="."), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)