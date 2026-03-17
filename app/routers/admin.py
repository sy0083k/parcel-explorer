import logging
from typing import cast

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    Request,
    UploadFile,
)
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, Response

from app.core import get_settings
from app.core.runtime_config import rebuild_runtime_state
from app.dependencies import (
    check_internal_network,
    get_or_create_csrf_token,
    is_authenticated,
    require_authenticated,
)
from app.logging_utils import RequestIdFilter
from app.routers import admin_support
from app.services import (
    admin_settings_service,
    admin_stats_service,
    geo_service,
    public_download_service,
    upload_service,
)
from app.services.service_errors import ServiceError

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
    result = upload_service.handle_excel_upload(
        upload_service.UploadCommand(
            context=admin_support.build_request_context(request, csrf_token=csrf_token),
            requested_sheet=request.app.state.config.UPLOAD_SHEET_NAME,
            max_upload_size_mb=int(request.app.state.config.MAX_UPLOAD_SIZE_MB),
            max_upload_rows=int(request.app.state.config.MAX_UPLOAD_ROWS),
        ),
        file_input=admin_support.build_uploaded_file_input(file),
    )
    if isinstance(result, upload_service.UploadRejectedResult):
        return JSONResponse(status_code=result.status_code, content=result.payload)
    if result.should_schedule_geom_job:
        background_tasks.add_task(geo_service.run_geom_update_job, result.geom_job_id, 5)
    return result.payload


@router.post("/public-download/upload", dependencies=[Depends(check_internal_network), Depends(require_authenticated)])
async def upload_public_download_file(
    request: Request,
    csrf_token: str = Form(default=""),
    file: UploadFile = File(...),  # noqa: B008
):
    config = request.app.state.config
    try:
        result = public_download_service.handle_public_download_upload(
            public_download_service.PublicDownloadUploadCommand(
                context=admin_support.build_request_context(request, csrf_token=csrf_token),
                config=admin_support.build_public_download_config(config),
            ),
            file_input=admin_support.build_uploaded_file_input(file),
        )
    except ServiceError as exc:
        admin_support.raise_http_exception(exc)
    return {
        "success": result.success,
        "message": result.message,
        "filename": result.filename,
        "uploadedAt": result.uploaded_at,
        "sizeBytes": result.size_bytes,
    }


@router.get("/public-download/meta", dependencies=[Depends(check_internal_network), Depends(require_authenticated)])
async def get_public_download_meta(request: Request) -> dict:
    config = request.app.state.config
    return public_download_service.get_public_download_meta(admin_support.build_public_download_config(config))


@router.post("/settings", dependencies=[Depends(check_internal_network), Depends(require_authenticated)])
async def update_settings(
    request: Request,
):
    form_data = await request.form()
    config = request.app.state.config
    try:
        admin_settings_service.apply_settings_update(
            admin_settings_service.SettingsUpdateCommand(
                context=admin_support.build_request_context(
                    request,
                    csrf_token=str(form_data.get("csrf_token", "")),
                ),
                settings_password=str(form_data.get("settings_password", "")),
                current_password_hash=config.ADMIN_PW_HASH,
                base_dir=config.BASE_DIR,
                updates=admin_settings_service.collect_settings_updates(form_data),
            )
        )
    except ServiceError as exc:
        admin_support.raise_http_exception(exc)
    rebuild_runtime_state(request.app, get_settings())
    logger.info(
        "admin settings updated",
        extra={
            **admin_support.build_request_log_context(request),
            "event": "admin.settings.updated",
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
    config = request.app.state.config
    try:
        admin_settings_service.apply_password_update(
            admin_settings_service.PasswordUpdateCommand(
                context=admin_support.build_request_context(request, csrf_token=csrf_token),
                current_password=current_password,
                new_password=new_password,
                new_password_confirm=new_password_confirm,
                current_password_hash=config.ADMIN_PW_HASH,
                base_dir=config.BASE_DIR,
            )
        )
    except ServiceError as exc:
        admin_support.raise_http_exception(exc)
    rebuild_runtime_state(request.app, get_settings())
    logger.info(
        "admin password updated",
        extra={
            **admin_support.build_request_log_context(request),
            "event": "admin.password.updated",
            "status": 303,
        },
    )
    return RedirectResponse(url="/admin/?updated=1", status_code=303)


@router.get("/stats", dependencies=[Depends(check_internal_network), Depends(require_authenticated)])
async def get_stats(limit: int = 10) -> dict:
    return admin_stats_service.get_dashboard_stats(limit=limit)


@router.post("/lands/geom-refresh", dependencies=[Depends(check_internal_network), Depends(require_authenticated)])
async def start_land_geom_refresh(
    request: Request,
    background_tasks: BackgroundTasks,
    csrf_token: str = Form(default=""),
) -> dict:
    try:
        result = geo_service.start_geom_refresh_job(
            geo_service.GeomRefreshStartCommand(
                context=admin_support.build_request_context(request, csrf_token=csrf_token)
            )
        )
    except ServiceError as exc:
        admin_support.raise_http_exception(exc)
    if result.started:
        background_tasks.add_task(geo_service.run_geom_update_job, result.job_id, 5)
    return {
        "success": result.success,
        "jobId": result.job_id,
        "started": result.started,
        "message": result.message,
    }


@router.get(
    "/lands/geom-refresh/{job_id}",
    dependencies=[Depends(check_internal_network), Depends(require_authenticated)],
)
async def get_land_geom_refresh_status(job_id: int) -> dict:
    try:
        job = geo_service.get_geom_refresh_job_status(job_id)
    except ServiceError as exc:
        admin_support.raise_http_exception(exc)
    return {"success": True, "job": job}


@router.get("/stats/web", dependencies=[Depends(check_internal_network), Depends(require_authenticated)])
async def get_web_stats(days: int = 30) -> dict:
    return admin_stats_service.get_web_stats(days=days)


@router.get("/raw-queries/export", dependencies=[Depends(check_internal_network), Depends(require_authenticated)])
async def export_raw_queries(
    request: Request,
    event_type: str = "all",
    date_from: str | None = None,
    date_to: str | None = None,
    limit: int = 10000,
) -> Response:
    filename = admin_support.build_raw_query_export_filename()
    try:
        result = admin_stats_service.export_raw_query_csv(
            event_type=event_type,
            date_from=date_from,
            date_to=date_to,
            limit=limit,
        )
    except ServiceError as exc:
        admin_support.log_raw_query_export_rejected(
            logger,
            request=request,
            event_type=event_type,
            date_from=date_from,
            date_to=date_to,
            limit=limit,
            filename=filename,
            exc=exc,
        )
        admin_support.raise_http_exception(exc)
    except Exception:
        admin_support.log_raw_query_export_failed(
            logger,
            request=request,
            event_type=event_type,
            date_from=date_from,
            date_to=date_to,
            limit=limit,
            filename=filename,
        )
        raise

    admin_support.log_raw_query_export_succeeded(
        logger,
        request=request,
        event_type=event_type,
        date_from=date_from,
        date_to=date_to,
        limit=limit,
        filename=filename,
        effective_limit=result.effective_limit,
        row_count=result.row_count,
    )
    return admin_support.build_raw_query_export_response(result, filename)
