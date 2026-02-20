# app/routers/admin.py
import bcrypt
import logging
from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from typing import cast

from app.dependencies import (
    check_internal_network,
    get_or_create_csrf_token,
    is_authenticated,
    require_authenticated,
    validate_csrf_token,
)
from app.logging_utils import RequestIdFilter
from app.services import admin_settings_service, stats_service, upload_service

router = APIRouter()
logger = logging.getLogger(__name__)
logger.addFilter(RequestIdFilter())


@router.get("/", response_class=HTMLResponse, dependencies=[Depends(check_internal_network)])
async def admin_root(request: Request) -> Response:
    if not is_authenticated(request):
        return RedirectResponse(url="/admin/login", status_code=303)

    templates = request.app.state.templates
    csrf_token = get_or_create_csrf_token(request)
    settings = admin_settings_service.get_current_settings()
    updated = request.query_params.get("updated") == "1"
    return cast(
        Response,
        templates.TemplateResponse(
            request, "admin.html", {"csrf_token": csrf_token, "settings": settings, "updated": updated}
        ),
    )


@router.post("/upload", dependencies=[Depends(check_internal_network), Depends(require_authenticated)])
async def upload_excel(
    request: Request,
    background_tasks: BackgroundTasks,
    csrf_token: str = Form(default=""),
    file: UploadFile = File(...),
):
    return upload_service.handle_excel_upload(
        request=request,
        background_tasks=background_tasks,
        csrf_token=csrf_token,
        file=file,
    )


@router.post("/settings", dependencies=[Depends(check_internal_network), Depends(require_authenticated)])
async def update_settings(
    request: Request,
    csrf_token: str = Form(default=""),
    settings_password: str = Form(default=""),
    app_name: str = Form(default=""),
    vworld_wmts_key: str = Form(default=""),
    vworld_geocoder_key: str = Form(default=""),
    allowed_ips: str = Form(default=""),
    max_upload_size_mb: str = Form(default=""),
    max_upload_rows: str = Form(default=""),
    login_max_attempts: str = Form(default=""),
    login_cooldown_seconds: str = Form(default=""),
    vworld_timeout_s: str = Form(default=""),
    vworld_retries: str = Form(default=""),
    vworld_backoff_s: str = Form(default=""),
    session_https_only: str = Form(default=""),
    trust_proxy_headers: str = Form(default=""),
    trusted_proxy_ips: str = Form(default=""),
    upload_sheet_name: str = Form(default=""),
):
    if not validate_csrf_token(request, csrf_token):
        raise HTTPException(status_code=403, detail="CSRF 토큰 검증에 실패했습니다.")

    if not settings_password:
        raise HTTPException(status_code=400, detail="관리자 비밀번호를 입력해주세요.")

    config = request.app.state.config
    if not bcrypt.checkpw(settings_password.encode("utf-8"), config.ADMIN_PW_HASH.encode("utf-8")):
        raise HTTPException(status_code=401, detail="관리자 비밀번호가 올바르지 않습니다.")

    updates = {
        "APP_NAME": app_name,
        "VWORLD_WMTS_KEY": vworld_wmts_key,
        "VWORLD_GEOCODER_KEY": vworld_geocoder_key,
        "ALLOWED_IPS": allowed_ips,
        "MAX_UPLOAD_SIZE_MB": max_upload_size_mb,
        "MAX_UPLOAD_ROWS": max_upload_rows,
        "LOGIN_MAX_ATTEMPTS": login_max_attempts,
        "LOGIN_COOLDOWN_SECONDS": login_cooldown_seconds,
        "VWORLD_TIMEOUT_S": vworld_timeout_s,
        "VWORLD_RETRIES": vworld_retries,
        "VWORLD_BACKOFF_S": vworld_backoff_s,
        "SESSION_HTTPS_ONLY": session_https_only,
        "TRUST_PROXY_HEADERS": trust_proxy_headers,
        "TRUSTED_PROXY_IPS": trusted_proxy_ips,
        "UPLOAD_SHEET_NAME": upload_sheet_name,
    }

    try:
        cleaned = admin_settings_service.validate_updates(updates)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    admin_settings_service.update_env_file(request.app.state.config.BASE_DIR, cleaned)
    request_id = getattr(request.state, "request_id", "-")
    client_ip = request.client.host if request.client else "unknown"
    logger.info(
        "admin settings updated",
        extra={
            "request_id": request_id,
            "event": "admin.settings.updated",
            "actor": request.session.get("user", "anonymous"),
            "ip": client_ip,
            "status": 303,
        },
    )
    return RedirectResponse(url="/admin/?updated=1", status_code=303)


@router.post("/password", dependencies=[Depends(check_internal_network), Depends(require_authenticated)])
async def update_password(
    request: Request,
    csrf_token: str = Form(default=""),
    current_password: str = Form(default=""),
    new_password: str = Form(default=""),
    new_password_confirm: str = Form(default=""),
):
    if not validate_csrf_token(request, csrf_token):
        raise HTTPException(status_code=403, detail="CSRF 토큰 검증에 실패했습니다.")

    if not current_password or not new_password:
        raise HTTPException(status_code=400, detail="비밀번호를 입력해주세요.")

    if new_password != new_password_confirm:
        raise HTTPException(status_code=400, detail="새 비밀번호가 일치하지 않습니다.")

    if len(new_password) < 8:
        raise HTTPException(status_code=400, detail="새 비밀번호는 8자 이상이어야 합니다.")

    config = request.app.state.config
    if not bcrypt.checkpw(current_password.encode("utf-8"), config.ADMIN_PW_HASH.encode("utf-8")):
        raise HTTPException(status_code=401, detail="현재 비밀번호가 올바르지 않습니다.")

    new_hash = bcrypt.hashpw(new_password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    admin_settings_service.update_admin_password_hash(config.BASE_DIR, new_hash)
    request_id = getattr(request.state, "request_id", "-")
    client_ip = request.client.host if request.client else "unknown"
    logger.info(
        "admin password updated",
        extra={
            "request_id": request_id,
            "event": "admin.password.updated",
            "actor": request.session.get("user", "anonymous"),
            "ip": client_ip,
            "status": 303,
        },
    )
    return RedirectResponse(url="/admin/?updated=1", status_code=303)


@router.get("/stats", dependencies=[Depends(check_internal_network), Depends(require_authenticated)])
async def get_stats(limit: int = 10) -> dict:
    return stats_service.get_admin_stats(limit=limit)


@router.get("/stats/web", dependencies=[Depends(check_internal_network), Depends(require_authenticated)])
async def get_web_stats(days: int = 30) -> dict:
    return stats_service.get_web_stats(days=days)
