# app/routers/auth.py
from typing import cast

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from app.dependencies import check_internal_network, get_or_create_csrf_token
from app.services import auth_service

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
    return auth_service.login(request, username=username, password=password, csrf_token=csrf_token)


@router.post("/admin/login", dependencies=[Depends(check_internal_network)])
async def login_admin_alias(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    csrf_token: str = Form(default=""),
):
    return await login(request=request, username=username, password=password, csrf_token=csrf_token)


@router.get("/logout")
async def logout(request: Request) -> RedirectResponse:
    return auth_service.logout(request)
