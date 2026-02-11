# app/routers/auth.py
from fastapi import APIRouter, Request, Form, Depends
import logging
import secrets
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from app.dependencies import (
    check_internal_network,
    get_or_create_csrf_token,
    validate_csrf_token,
)
from passlib.context import CryptContext
from app.logging_utils import RequestIdFilter

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

router = APIRouter()
logger = logging.getLogger(__name__)
logger.addFilter(RequestIdFilter())


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
    request_id = getattr(request.state, "request_id", "-")
    client_ip = request.client.host if request.client else "unknown"
    limiter = request.app.state.login_limiter
    limiter_key = f"{client_ip}:{username}"

    if limiter.is_blocked(limiter_key):
        logger.warning("login blocked by limiter", extra={"request_id": request_id})
        return JSONResponse(
            status_code=429,
            content={"success": False, "message": "로그인 시도가 너무 많습니다. 잠시 후 다시 시도해주세요."},
        )

    if not validate_csrf_token(request, csrf_token):
        return JSONResponse(
            status_code=403,
            content={"success": False, "message": "잘못된 요청입니다. 페이지를 새로고침 해주세요."},
        )

    is_id_match = secrets.compare_digest(username, config.ADMIN_ID)
    is_pw_match = pwd_context.verify(password, config.ADMIN_PW_HASH)

    if is_id_match and is_pw_match:
        request.session.clear()
        request.session["user"] = username
        request.session["csrf_token"] = get_or_create_csrf_token(request)
        limiter.reset(limiter_key)
        logger.info("login success", extra={"request_id": request_id})
        return JSONResponse(content={"success": True})

    limiter.register_failure(limiter_key)
    logger.warning("login failed", extra={"request_id": request_id})
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