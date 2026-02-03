import os
import sqlite3
import json
import time
import requests
import pandas as pd
import secrets
from dotenv import load_dotenv

from fastapi import FastAPI, Depends, HTTPException, status, UploadFile, File, Request,Form
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import FileResponse, JSONResponse, HTMLResponse, RedirectResponse
from contextlib import asynccontextmanager
from starlette.middleware.sessions import SessionMiddleware

# 1. 환경 설정 및 보안 변수
load_dotenv()
VWORLD_KEY = os.getenv("VWORLD_KEY")
ADMIN_ID = os.getenv("ADMIN_ID")
ADMIN_PW = os.getenv("ADMIN_PW")
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key") # 세션 암호화용 키

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

# 2. 세션 미들웨어 설정
app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY)

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# --- [인증 확인 유틸리티] ---
def is_authenticated(request: Request):
    """현재 세션에 관리자 정보가 있는지 확인합니다."""
    return request.session.get("user") == ADMIN_ID

# --- [API] 로그인 및 로그아웃 ---
@app.post("/api/login")
async def login(request: Request, username: str = Form(...), password: str = Form(...)):
    """로그인 처리 및 세션 생성"""
    if username == ADMIN_ID and password == ADMIN_PW:
        request.session["user"] = username
        return {"success": True}
    return JSONResponse(status_code=401, content={"success": False, "message": "아이디 또는 비밀번호가 틀립니다."})

@app.get("/api/logout")
async def logout(request: Request):
    """세션 삭제 및 로그인 페이지로 리다이렉트"""
    request.session.clear()
    return RedirectResponse(url="/admin/login")

# --- [페이지 라우팅] ---
@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/admin/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """로그인 폼 페이지"""
    return templates.TemplateResponse("login.html", {"request": request})

@app.get("/admin", response_class=HTMLResponse)
async def admin_page(request: Request):
    """관리자 메인 페이지 (세션 체크)"""
    if not is_authenticated(request):
        return RedirectResponse(url="/admin/login")
    return templates.TemplateResponse("admin.html", {"request": request})

@app.post("/api/admin/upload")
async def upload_excel(request: Request, file: UploadFile = File(...)):
    if not is_authenticated(request):
        raise HTTPException(status_code=401, detail="인증이 필요합니다.")
        
    try:
        df = pd.read_excel(file.file, sheet_name="목록")
        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()
        cursor.execute("DELETE FROM idle_land") # 기존 데이터 초기화
        
        # 1차 시도: 모든 데이터 DB 추가 (경계선 없어도 저장)
        print("🚀 1차 데이터 저장 시작...")        
        for _, row in df.head(20).iterrows(): # 테스트를 위해 20개만 로드
            addr = row['소재지(지번)']
            geom_data = get_parcel_geom(addr)            
            cursor.execute("""
                INSERT INTO idle_land (address, land_type, area, description, contact, geom) 
                VALUES (?,?,?,?,?,?)
            """, (str(addr), str(row['(공부상)지목']), float(row['(공부상)면적(㎡)']), 
                  str(row['유휴사유 상세설명']), str(row['담당자연락처']), geom_data))            
        conn.commit()
        
        # 2차 시도: geom이 None인 항목만 다시 시도
        print("🔄 경계선 획득 실패 항목 재시도 중...")
        cursor.execute("SELECT id, address FROM idle_land WHERE geom IS NULL")
        failed_items = cursor.fetchall()
        
        retry_count = 0
        for item_id, address in failed_items:
            # 재시도 전에는 조금 더 긴 휴식 (0.5초)
            time.sleep(0.5)
            geom_data = get_parcel_geom(address)
            if geom_data:
                cursor.execute("UPDATE idle_land SET geom = ? WHERE id = ?", (geom_data, item_id))
                retry_count += 1
        
        conn.commit()
        
        # 최종 상태 확인 (여전히 실패한 건수 계산)
        cursor.execute("SELECT COUNT(*) FROM idle_land WHERE geom IS NULL")
        final_failed = cursor.fetchone()[0]
        
        total_count = len(df)
        conn.close()
        return {
            "success": True,
            "message": f"총 {total_count}건 처리 완료. (재시도 성공: {retry_count}건, 최종 실패: {final_failed}건)"
        }

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
            "properties": dict(row)
        })
    return {"type": "FeatureCollection", "features": features}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)