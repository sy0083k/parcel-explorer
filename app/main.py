import os
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from app.routers import map_router, auth, admin
from starlette.middleware.sessions import SessionMiddleware
from contextlib import asynccontextmanager
from app.utils import init_db
from app.core import get_settings

settings = get_settings()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 서버 실행 시 DB 및 테이블 생성
    init_db() 
    yield

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
    # response.headers["Content-Security-Policy"] = "default-src 'self' https://cdn.jsdelivr.net https://api.vworld.kr; script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://api.vworld.kr;"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self' https://cdn.jsdelivr.net https://api.vworld.kr; "
        "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://api.vworld.kr; "
        "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "  # 이 라인을 추가하세요
        "img-src 'self' data: https://api.vworld.kr https://xdworld.vworld.kr;" # 지도 타일 이미지를 위해 권장
    )
    
    return response

app.add_middleware(SessionMiddleware, secret_key=settings.secret_key, max_age=None, https_only=True)

BASE_DIR = settings.base_dir
app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))

# (기존 CSP 미들웨어 및 라우트 로직들...)
class Config:
    APP_NAME = settings.app_name
    CENTER_LON = settings.map_center_lon
    CENTER_LAT = settings.map_center_lat
    DEFAULT_ZOOM = settings.map_default_zoom
    VWORLD_KEY = settings.vworld_key
    BASE_DIR = settings.base_dir
    ADMIN_ID = settings.admin_id
    ADMIN_PW_HASH = settings.admin_pw_hash
    ALLOWED_IP_PREFIXES = settings.allowed_ip_prefixes

app.state.config = Config()
app.state.templates = templates

app.include_router(auth.router, tags=["Authentication"])
app.include_router(admin.router, prefix="/admin", tags=["Admin"])
app.include_router(map_router.router, prefix="/api", tags=["Map"])

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

# D:\2026\개인\IdlePublicProperty
# venv\Scripts\activate
# uvicorn app.main:app --reload