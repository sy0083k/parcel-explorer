import os
import sqlite3
import json
import time
import requests
import pandas as pd
import secrets
import logging
from dotenv import load_dotenv
from fastapi import FastAPI, Depends, HTTPException, status, UploadFile, File, Request, Form, BackgroundTasks
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import FileResponse, JSONResponse, HTMLResponse, RedirectResponse
from contextlib import asynccontextmanager
from starlette.middleware.sessions import SessionMiddleware
from passlib.context import CryptContext

# ==========================================
# 1. 환경 설정 및 보안 변수
# ==========================================
load_dotenv()
VWORLD_KEY = os.getenv("VWORLD_KEY")
ADMIN_ID = os.getenv("ADMIN_ID")
ADMIN_PW = os.getenv("ADMIN_PW")
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key")
raw_ips = os.getenv("ALLOWED_IPS", "127.0.0.1")
ALLOWED_IP_PREFIXES = [ip.strip() for ip in raw_ips.split(",") if ip.strip()]
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    
# ==========================================
# 2. DB 초기화 및 Lifespan
# ==========================================
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
            adm_property TEXT,
            gen_property TEXT,
            contact TEXT,
            geom TEXT
        )
    ''')
    conn.commit()
    conn.close()
    yield
    
# ==========================================
# 3. 유틸리티 함수
# ==========================================
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
    conn = sqlite3.connect('database.db')
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
    
def is_authenticated(request: Request):
    """세션 인증 확인"""
    return request.session.get("user") == ADMIN_ID

def check_internal_network(request: Request):
    """
    내부망 IP 접근 제어 함수
    """
    # 1. 클라이언트 객체 확인 (방어 코드)
    if not request.client:
        print("[보안 경고] 클라이언트 정보 식별 불가")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="Client Unknown"
        )

    client_ip = request.client.host
    
    # 디버깅용 출력 (접속 성공 시 주석 처리 가능)
    print(f"[접속 시도 IP] {client_ip}")

    # 2. 허용 목록(ALLOWED_IP_PREFIXES)과 대조
    # 여기서 에러가 났던 이유는 ALLOWED_IP_PREFIXES가 없었기 때문입니다.
    is_allowed = any(client_ip.startswith(prefix) for prefix in ALLOWED_IP_PREFIXES)
    
    if not is_allowed:
        print(f"[접근 차단] 허용되지 않은 IP: {client_ip}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="관리자 페이지는 내부 행정망에서만 접근 가능합니다."
        )
        
    return True
    
# ==========================================
# 4. 앱 초기화 및 미들웨어 설정
# ==========================================
app = FastAPI(lifespan=lifespan)

@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    
    # 1. X-Frame-Options: 클릭재킹 방지 (iframe 내 로딩 차단)
    # admin.html이 다른 사이트의 iframe에 들어가는 것을 막습니다.
    response.headers["X-Frame-Options"] = "DENY"
    
    # 2. X-Content-Type-Options: MIME 스니핑 차단
    # 브라우저가 파일 타입을 추측하여 실행하는 것을 방지합니다.
    response.headers["X-Content-Type-Options"] = "nosniff"
    
    # 3. Content-Security-Policy (CSP): XSS 방지 (기초 설정)
    # 스크립트 소스를 현재 도메인('self')과 신뢰할 수 있는 소스(CDN 등)로 제한
    # ※ 주의: 사용 중인 CDN 주소(OpenLayers, VWorld 등)를 포함해야 지도가 깨지지 않습니다.
    # 아래 설정은 예시이며, 지도 서비스에 맞춰 'unsafe-inline' 등이 필요할 수 있습니다.
    response.headers["Content-Security-Policy"] = (
    "default-src 'self' https://cdn.jsdelivr.net https://api.vworld.kr; "
    "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://api.vworld.kr; "
    "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "  # 이 라인을 추가하세요
    "img-src 'self' data: https://api.vworld.kr https://xdworld.vworld.kr;" # 지도 타일 이미지를 위해 권장
)
    
    return response

app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY, max_age=None, https_only=True)
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

class Config:
    APP_NAME = os.getenv("APP_NAME")

app.state.config = Config()
# ==========================================
# 5. API 엔드포인트 (Auth & Data)
# ==========================================
@app.post("/api/login")
async def login(request: Request, username: str = Form(...), password: str = Form(...)):
    """로그인 처리 및 세션 생성 (해시 검증 방식)"""
    
    # 1. 아이디 일치 확인
    is_id_match = (username == ADMIN_ID)
    
    # 2. 비밀번호 해시 검증 (평문 password와 해시된 ADMIN_PW 비교)
    # pwd_context.verify 함수가 내부적으로 복잡한 비교 과정을 처리합니다.
    is_pw_match = pwd_context.verify(password, ADMIN_PW)
    
    if is_id_match and is_pw_match:
        request.session["user"] = username
        return {"success": True}
        
    return JSONResponse(
        status_code=401, 
        content={"success": False, "message": "아이디 또는 비밀번호가 틀립니다."}
    )

@app.get("/api/logout")
async def logout(request: Request):
    """세션 삭제 및 로그인 페이지로 리다이렉트"""
    request.session.clear()
    return RedirectResponse(url="/admin/login")
    
@app.get("/api/config")
async def get_config():
    """프론트엔드에 설정값 전달"""
    return {
        "vworldKey": VWORLD_KEY,
        "center": [
            float(os.getenv("MAP_CENTER_LON", 126.4500)), 
            float(os.getenv("MAP_CENTER_LAT", 36.7848))
        ],
        "zoom": int(os.getenv("MAP_DEFAULT_ZOOM", 13))
    }
    
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
    
@app.post("/api/admin/upload", dependencies=[Depends(check_internal_network)])
async def upload_excel(request: Request, background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    if not is_authenticated(request):
        raise HTTPException(status_code=401, detail="인증이 필요합니다.")
        
    try:
        df = pd.read_excel(file.file, sheet_name="목록")
        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()
        cursor.execute("DELETE FROM idle_land") # 기존 데이터 초기화
        
        print("🚀 엑셀 데이터 저장 시작...")        
        for _, row in df.iterrows():
            addr = row['소재지(지번)']        
            cursor.execute("""
                INSERT INTO idle_land (address, land_type, area, adm_property, gen_property, contact, geom) 
                VALUES (?,?,?,?,?,?,NULL)
            """, (str(addr), str(row['(공부상)지목']), float(row['(공부상)면적(㎡)']), 
                  str(row['행정재산']), str(row['일반재산']), str(row['담당자연락처'])))            
        conn.commit()      
        conn.close()
        
        # 🚀 핵심: 엑셀 저장이 끝나면 백그라운드 작업으로 경계선 획득 실행
        # 이 코드가 실행되면 서버는 클라이언트에게 즉시 응답을 보내고, 작업은 따로 수행됩니다.
        background_tasks.add_task(update_geoms, 5)
        
        return {
            "success": True,
            "total": len(df),
            "message": "엑셀 데이터 입력 완료"
        }

    except Exception as e:
        return JSONResponse(status_code=500, content={"success": False, "message": str(e)})
                
# ==========================================
# 6. 페이지 라우팅 (HTML)
# ==========================================
@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/admin/login", response_class=HTMLResponse, dependencies=[Depends(check_internal_network)])
async def login_page(request: Request):
    """로그인 폼 페이지"""
    return templates.TemplateResponse("login.html", {"request": request})

@app.get("/admin", response_class=HTMLResponse, dependencies=[Depends(check_internal_network)])
async def admin_page(request: Request):
    """관리자 메인 페이지 (세션 체크)"""
    if not is_authenticated(request):
        return RedirectResponse(url="/admin/login")
    return templates.TemplateResponse("admin.html", {"request": request})

# ==========================================
# 7. 서버 실행 (Entry Point)
# ==========================================
if __name__ == "__main__":
    import uvicorn
    # 앱 실행 시 필요한 설정을 로드하여 서버 시작
    uvicorn.run(app, host="0.0.0.0", port=8000)