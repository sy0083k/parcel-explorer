# app/routers/auth.py
from fastapi import APIRouter, Request, Form, Depends
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from app.dependencies import (
    check_internal_network,
    get_or_create_csrf_token,
    validate_csrf_token,
)
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

router = APIRouter()


@router.get("/admin/login", response_class=HTMLResponse, dependencies=[Depends(check_internal_network)])
async def login_page(request: Request):
    templates = request.app.state.templates
    csrf_token = get_or_create_csrf_token(request)
    return templates.TemplateResponse("login.html", {"request": request, "csrf_token": csrf_token})


@router.post("/login", dependencies=[Depends(check_internal_network)])
async def login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    csrf_token: str = Form(default=""),
):
    """로그인 처리 및 세션 생성 (해시 검증 방식)"""
    config = request.app.state.config

    if not validate_csrf_token(request, csrf_token):
        return JSONResponse(
            status_code=403,
            content={"success": False, "message": "잘못된 요청입니다. 페이지를 새로고침 해주세요."},
        )

    is_id_match = username == config.ADMIN_ID
    is_pw_match = pwd_context.verify(password, config.ADMIN_PW_HASH)

    if is_id_match and is_pw_match:
        request.session["user"] = username
        return JSONResponse(content={"success": True})

    return JSONResponse(
        status_code=401,
        content={"success": False, "message": "아이디 또는 비밀번호가 틀립니다."},
    )


@router.post("/admin/login", dependencies=[Depends(check_internal_network)])
async def login_admin_alias(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    csrf_token: str = Form(default=""),
):
    """/admin 경로 하위 로그인 POST를 /login과 동일 정책으로 지원."""
    return await login(request=request, username=username, password=password, csrf_token=csrf_token)


@router.get("/logout")
async def logout(request: Request):
    request.session.clear()
    response = RedirectResponse(url="/admin/login", status_code=303)
    response.delete_cookie("session", path="/")
    return response