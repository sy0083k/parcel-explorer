# app/routers/admin.py
import logging
from datetime import datetime
from typing import cast

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    HTTPException,
    Request,
    UploadFile,
)
from fastapi.responses import HTMLResponse, RedirectResponse, Response

from app.dependencies import (
    check_internal_network,
    get_or_create_csrf_token,
    is_authenticated,
    require_authenticated,
)
from app.logging_utils import RequestIdFilter
from app.services import (
    admin_settings_service,
    geo_service,
    public_download_service,
    stats_service,
    upload_service,
)

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
    file: UploadFile = File(...),  # noqa: B008
):
    return upload_service.handle_excel_upload(
        request=request,
        background_tasks=background_tasks,
        csrf_token=csrf_token,
        file=file,
    )


@router.post("/public-download/upload", dependencies=[Depends(check_internal_network), Depends(require_authenticated)])
async def upload_public_download_file(
    request: Request,
    csrf_token: str = Form(default=""),
    file: UploadFile = File(...),  # noqa: B008
):
    return public_download_service.handle_public_download_upload(
        request=request,
        csrf_token=csrf_token,
        file=file,
    )


@router.get("/public-download/meta", dependencies=[Depends(check_internal_network), Depends(require_authenticated)])
async def get_public_download_meta(request: Request) -> dict:
    return public_download_service.get_public_download_meta(request)


@router.post("/settings", dependencies=[Depends(check_internal_network), Depends(require_authenticated)])
async def update_settings(
    request: Request,
):
    form_data = await request.form()
    admin_settings_service.apply_settings_update(
        request,
        csrf_token=str(form_data.get("csrf_token", "")),
        settings_password=str(form_data.get("settings_password", "")),
        updates=admin_settings_service.collect_settings_updates(form_data),
    )
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
    admin_settings_service.apply_password_update(
        request,
        csrf_token=csrf_token,
        current_password=current_password,
        new_password=new_password,
        new_password_confirm=new_password_confirm,
    )
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
    payload = stats_service.get_admin_stats(limit=limit)
    payload["landSummary"] = stats_service.get_land_stats()
    return payload


@router.post("/lands/geom-refresh", dependencies=[Depends(check_internal_network), Depends(require_authenticated)])
async def start_land_geom_refresh(
    request: Request,
    background_tasks: BackgroundTasks,
    csrf_token: str = Form(default=""),
) -> dict:
    return geo_service.start_geom_refresh_job(
        request=request,
        background_tasks=background_tasks,
        csrf_token=csrf_token,
    )


@router.get(
    "/lands/geom-refresh/{job_id}",
    dependencies=[Depends(check_internal_network), Depends(require_authenticated)],
)
async def get_land_geom_refresh_status(job_id: int) -> dict:
    return {"success": True, "job": geo_service.get_geom_refresh_job_status(job_id)}


@router.get("/stats/web", dependencies=[Depends(check_internal_network), Depends(require_authenticated)])
async def get_web_stats(days: int = 30) -> dict:
    return stats_service.get_web_stats(days=days)


@router.get("/raw-queries/export", dependencies=[Depends(check_internal_network), Depends(require_authenticated)])
async def export_raw_queries(
    request: Request,
    event_type: str = "all",
    date_from: str | None = None,
    date_to: str | None = None,
    limit: int = 10000,
) -> Response:
    request_id = getattr(request.state, "request_id", "-")
    actor = request.session.get("user", "anonymous")
    client_ip = request.client.host if request.client else "unknown"
    filename = f"raw-queries-{datetime.now().strftime('%Y%m%d')}.csv"
    try:
        result = stats_service.export_raw_query_csv(
            event_type=event_type,
            date_from=date_from,
            date_to=date_to,
            limit=limit,
        )
    except HTTPException as exc:
        logger.warning(
            "raw query export rejected",
            extra={
                "request_id": request_id,
                "event": "admin.raw_queries_export.rejected",
                "actor": actor,
                "ip": client_ip,
                "status": exc.status_code,
                "event_type_filter": event_type,
                "date_from": date_from or "-",
                "date_to": date_to or "-",
                "requested_limit": limit,
                "effective_limit": "-",
                "exported_row_count": "-",
                "export_filename": filename,
                "reason": exc.detail if isinstance(exc.detail, str) else "invalid_request",
            },
        )
        raise
    except Exception:
        logger.exception(
            "raw query export failed",
            extra={
                "request_id": request_id,
                "event": "admin.raw_queries_export.failed",
                "actor": actor,
                "ip": client_ip,
                "status": 500,
                "event_type_filter": event_type,
                "date_from": date_from or "-",
                "date_to": date_to or "-",
                "requested_limit": limit,
                "effective_limit": "-",
                "exported_row_count": "-",
                "export_filename": filename,
                "reason": "unexpected_exception",
            },
        )
        raise

    logger.info(
        "raw query export succeeded",
        extra={
            "request_id": request_id,
            "event": "admin.raw_queries_export.succeeded",
            "actor": actor,
            "ip": client_ip,
            "status": 200,
            "event_type_filter": event_type,
            "date_from": date_from or "-",
            "date_to": date_to or "-",
            "requested_limit": limit,
            "effective_limit": result.effective_limit,
            "exported_row_count": result.row_count,
            "export_filename": filename,
        },
    )
    headers = {"Content-Disposition": f'attachment; filename="{filename}"'}
    return Response(content=result.csv_text, media_type="text/csv; charset=utf-8", headers=headers)
