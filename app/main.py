import asyncio
import logging
import os
import sys
import time
import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import cast

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.datastructures import MutableHeaders
from starlette.middleware.sessions import SessionMiddleware
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.auth_security import LoginAttemptLimiter
from app.core import get_settings
from app.core.runtime_config import RuntimeConfig
from app.exceptions import http_exception_handler, unhandled_exception_handler
from app.logging_utils import RequestIdFilter, configure_logging
from app.rate_limit import SlidingWindowRateLimiter
from app.routers import admin, auth, map_router, map_v1_router
from app.services import health_service
from app.services.geo_service import init_db, recover_interrupted_geom_jobs, run_geom_update_job
from app.utils import vite_assets

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

configure_logging()
logger = logging.getLogger(__name__)
logger.addFilter(RequestIdFilter())
settings = get_settings()


class SecurityHeadersMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        async def send_with_security_headers(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = MutableHeaders(scope=message)
                headers["X-Frame-Options"] = "DENY"
                headers["X-Content-Type-Options"] = "nosniff"
                headers["Content-Security-Policy"] = (
                    "default-src 'self' https://cdn.jsdelivr.net https://api.vworld.kr; "
                    "script-src 'self' https://cdn.jsdelivr.net https://api.vworld.kr; "
                    "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
                    "img-src 'self' data: https://api.vworld.kr https://xdworld.vworld.kr;"
                )
            await send(message)

        await self.app(scope, receive, send_with_security_headers)


class RequestContextMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        started = time.perf_counter()
        headers = MutableHeaders(scope=scope)
        request_id = headers.get("x-request-id") or str(uuid.uuid4())
        scope.setdefault("state", {})
        scope["state"]["request_id"] = request_id
        client = scope.get("client")
        client_ip = client[0] if client else "unknown"
        status_code: int | None = None
        request_logged = False

        async def send_with_request_context(message: Message) -> None:
            nonlocal request_logged, status_code
            if message["type"] == "http.response.start":
                status_code = int(message["status"])
                response_headers = MutableHeaders(scope=message)
                response_headers["X-Request-ID"] = request_id
            await send(message)
            if (
                message["type"] == "http.response.body"
                and not message.get("more_body", False)
                and not request_logged
            ):
                request_logged = True
                resolved_status = status_code or 500
                logger.info(
                    "request completed",
                    extra={
                        "request_id": request_id,
                        "event": "http.request.completed",
                        "actor": "anonymous",
                        "ip": client_ip,
                        "method": scope["method"],
                        "path": scope["path"],
                        "status": resolved_status,
                        "status_class": f"{resolved_status // 100}xx",
                        "latency_ms": round((time.perf_counter() - started) * 1000, 2),
                    },
                )

        await self.app(scope, receive, send_with_request_context)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    init_db()
    job_id = recover_interrupted_geom_jobs()
    if job_id is not None:
        asyncio.create_task(asyncio.to_thread(run_geom_update_job, job_id, 5))
    if "/" in settings.allowed_web_track_paths:
        logger.warning(
            "ALLOWED_WEB_TRACK_PATHS contains '/' — all page paths will be collected. "
            "Specify explicit paths in production to minimize data collection.",
            extra={"event": "config.web_track_paths.all_paths_active"},
        )
    yield


app = FastAPI(lifespan=lifespan)
app.add_exception_handler(HTTPException, http_exception_handler)
app.add_exception_handler(Exception, unhandled_exception_handler)

app.add_middleware(
    SessionMiddleware,
    secret_key=settings.secret_key,
    max_age=3600,
    https_only=settings.session_https_only,
    session_cookie=settings.session_cookie_name,
    same_site="lax",
)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RequestContextMiddleware)

BASE_DIR = settings.base_dir
app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))
templates.env.globals["vite_assets"] = lambda entry: vite_assets(entry, settings.base_dir)


app.state.config = RuntimeConfig(settings)
app.state.templates = templates
app.state.login_limiter = LoginAttemptLimiter(
    max_attempts=settings.login_max_attempts,
    cooldown_seconds=settings.login_cooldown_seconds,
)
app.state.event_rate_limiter = SlidingWindowRateLimiter()

app.include_router(auth.router, tags=["Authentication"])
app.include_router(admin.router, prefix="/admin", tags=["Admin"])
app.include_router(map_router.router, prefix="/api", tags=["Map"])
app.include_router(map_v1_router.router, prefix="/api/v1", tags=["MapV1"])


@app.get("/favicon.ico", include_in_schema=False)
async def favicon() -> FileResponse:
    return FileResponse(os.path.join(BASE_DIR, "static", "favicon.svg"), media_type="image/svg+xml")


@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request) -> HTMLResponse:
    return cast(HTMLResponse, templates.TemplateResponse(request, "index.html", {}))


@app.get("/health")
async def healthcheck(request: Request, deep: int = 0) -> dict[str, object]:
    request_id = getattr(request.state, "request_id", "-")
    checks = health_service.evaluate_health_checks(deep=deep, request_id=request_id)
    return {"status": "ok", "request_id": request_id, "checks": checks}
