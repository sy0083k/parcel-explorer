# app/routers/auth.py
from typing import cast

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, Response

from app.dependencies import (
    SESSION_NAMESPACE_KEY,
    check_internal_network,
    get_or_create_csrf_token,
    require_authenticated,
    validate_csrf_token,
)
from app.services import auth_service
from app.services.service_models import RequestContext

router = APIRouter()


@router.get("/admin/login", response_class=HTMLResponse, dependencies=[Depends(check_internal_network)])
async def login_page(request: Request) -> HTMLResponse:
    templates = request.app.state.templates
    csrf_token = get_or_create_csrf_token(request)
    return cast(HTMLResponse, templates.TemplateResponse(request, "login.html", {"csrf_token": csrf_token}))


@router.post("/login", dependencies=[Depends(check_internal_network)])
async def login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    csrf_token: str = Form(default=""),
):
    config = request.app.state.config
    limiter = request.app.state.login_limiter
    client_ip = request.client.host if request.client else "unknown"
    limiter_key = f"{client_ip}:{username}"
    result = auth_service.login(
        auth_service.LoginCommand(
            context=RequestContext(
                request_id=getattr(request.state, "request_id", "-"),
                actor=username or "anonymous",
                client_ip=client_ip,
                csrf_valid=validate_csrf_token(request, csrf_token),
            ),
            username=username,
            password=password,
            admin_id=config.ADMIN_ID,
            admin_password_hash=config.ADMIN_PW_HASH,
            limiter_blocked=limiter.is_blocked(limiter_key),
        )
    )
    if result.limiter_action == "reset":
        request.session.clear()
        request.session["user"] = username
        request.session[SESSION_NAMESPACE_KEY] = config.SESSION_NAMESPACE
        request.session["csrf_token"] = get_or_create_csrf_token(request)
        limiter.reset(limiter_key)
        return JSONResponse(content={"success": True})
    if result.limiter_action == "register_failure":
        limiter.register_failure(limiter_key)
    return JSONResponse(
        status_code=result.status_code,
        content={"success": False, "message": result.message},
    )


@router.post("/admin/login", dependencies=[Depends(check_internal_network)])
async def login_admin_alias(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    csrf_token: str = Form(default=""),
):
    return await login(request=request, username=username, password=password, csrf_token=csrf_token)


@router.post("/logout", dependencies=[Depends(check_internal_network), Depends(require_authenticated)])
async def logout_post(
    request: Request,
    csrf_token: str = Form(default=""),
) -> Response:
    config = request.app.state.config
    if not validate_csrf_token(request, csrf_token):
        return JSONResponse(
            status_code=403,
            content={"success": False, "message": "잘못된 요청입니다. 페이지를 새로고침 해주세요."},
        )
    result = auth_service.logout(csrf_valid=True)
    if result.clear_session:
        request.session.clear()
    response = RedirectResponse(url=result.redirect_url, status_code=303)
    response.delete_cookie(
        config.SESSION_COOKIE_NAME,
        path="/",
        secure=config.SESSION_HTTPS_ONLY,
        httponly=True,
        samesite="lax",
    )
    return response
