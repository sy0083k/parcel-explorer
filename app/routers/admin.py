# app/routers/admin.py
import os
import sqlite3

import pandas as pd
from fastapi import APIRouter, Request, UploadFile, File, BackgroundTasks, HTTPException, Form, Depends
from fastapi.responses import JSONResponse, HTMLResponse, RedirectResponse
from app.dependencies import (
    check_internal_network,
    is_authenticated,
    require_authenticated,
    get_or_create_csrf_token,
    validate_csrf_token,
)
from app.utils import update_geoms

router = APIRouter()

REQUIRED_COLUMNS = [
    "소재지(지번)",
    "(공부상)지목",
    "(공부상)면적(㎡)",
    "행정재산",
    "일반재산",
    "담당자연락처",
]


@router.get("/", response_class=HTMLResponse, dependencies=[Depends(check_internal_network)])
async def admin_root(request: Request):
    if not is_authenticated(request):
        return RedirectResponse(url="/admin/login", status_code=303)

    templates = request.app.state.templates
    csrf_token = get_or_create_csrf_token(request)
    return templates.TemplateResponse("admin.html", {"request": request, "csrf_token": csrf_token})


@router.post("/upload", dependencies=[Depends(check_internal_network), Depends(require_authenticated)])
async def upload_excel(
    request: Request,
    background_tasks: BackgroundTasks,
    csrf_token: str = Form(default=""),
    file: UploadFile = File(...),
):
    config = request.app.state.config

    if not validate_csrf_token(request, csrf_token):
        raise HTTPException(status_code=403, detail="CSRF 토큰 검증에 실패했습니다.")

    filename = (file.filename or "").lower()
    content_type = (file.content_type or "").lower()
    if not filename.endswith((".xlsx", ".xls")):
        raise HTTPException(status_code=400, detail="엑셀 파일(.xlsx, .xls)만 업로드 가능합니다.")

    allowed_content_types = {
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "application/vnd.ms-excel",
        "application/octet-stream",
    }
    if content_type and content_type not in allowed_content_types:
        raise HTTPException(status_code=400, detail="지원하지 않는 파일 형식입니다.")

    try:
        df = pd.read_excel(file.file, sheet_name="목록")

        missing = [col for col in REQUIRED_COLUMNS if col not in df.columns]
        if missing:
            raise HTTPException(status_code=400, detail=f"필수 컬럼 누락: {', '.join(missing)}")

        conn = sqlite3.connect(os.path.join(config.BASE_DIR, "data/database.db"))
        cursor = conn.cursor()
        cursor.execute("DELETE FROM idle_land")

        for _, row in df.iterrows():
            addr = str(row["소재지(지번)"]).strip()
            area = float(row["(공부상)면적(㎡)"])

            cursor.execute(
                """
                INSERT INTO idle_land (address, land_type, area, adm_property, gen_property, contact, geom)
                VALUES (?,?,?,?,?,?,NULL)
                """,
                (
                    addr,
                    str(row["(공부상)지목"]),
                    area,
                    str(row["행정재산"]),
                    str(row["일반재산"]),
                    str(row["담당자연락처"]),
                ),
            )

        conn.commit()
        conn.close()

        background_tasks.add_task(update_geoms, 5)

        return {"success": True, "total": len(df), "message": "엑셀 데이터 입력 완료"}

    except HTTPException:
        raise
    except Exception:
        return JSONResponse(
            status_code=500,
            content={"success": False, "message": "업로드 처리 중 오류가 발생했습니다."},
        )