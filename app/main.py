import os
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from app.routers import auth, map_router

load_dotenv()

app = FastAPI()

# 1. 현재 파일(main.py)의 위치를 기준으로 절대 경로 계산
# __file__은 app/main.py이므로, 부모의 부모가 프로젝트 루트입니다.
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 2. 정적 파일 경로 설정 (root/static)
app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")

# 3. 템플릿 경로 설정 (root/templates)
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))

# (기존 CSP 미들웨어 및 라우트 로직들...)
class Config:
    APP_NAME = os.getenv("APP_NAME")
    CENTER_LON = os.getenv("MAP_CENTER_LON", 126.4500)
    CENTER_LAT = os.getenv("MAP_CENTER_LAT", 36.7848)
    DEFAULT_ZOOM = os.getenv("MAP_DEFAULT_ZOOM")
    VWORLD_KEY = os.getenv("VWORLD_KEY")
    BASE_DIR = BASE_DIR

app.state.config = Config()
app.state.templates = templates

app.include_router(auth.router, tags=["Authentication"])
app.include_router(map_router.router, prefix="/api", tags=["Map"])

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    # templates.TemplateResponse를 사용하여 index.html을 반환합니다.
    return templates.TemplateResponse("index.html", {"request": request})

# uvicorn app.main:app --reload