import logging
import os
import sys
import time
import uuid
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from pathlib import Path
from typing import cast

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

from app.auth_security import LoginAttemptLimiter
from app.core import get_settings
from app.core.runtime_config import RuntimeConfig
from app.exceptions import http_exception_handler, unhandled_exception_handler
from app.logging_utils import RequestIdFilter, configure_logging
from app.rate_limit import SlidingWindowRateLimiter
from app.routers import admin, auth, map_router, map_v1_router
from app.services import health_service
from app.services.geo_service import init_db
from app.utils import vite_assets

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

configure_logging()
logger = logging.getLogger(__name__)
logger.addFilter(RequestIdFilter())
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    init_db()
    yield


app = FastAPI(lifespan=lifespan)
app.add_exception_handler(HTTPException, http_exception_handler)
app.add_exception_handler(Exception, unhandled_exception_handler)


@app.middleware("http")
async def add_request_context(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    started = time.perf_counter()
    request_id = request.headers.get("x-request-id") or str(uuid.uuid4())
    request.state.request_id = request_id
    response = await call_next(request)
    latency_ms = round((time.perf_counter() - started) * 1000, 2)
    client_ip = request.client.host if request.client else "unknown"
    response.headers["X-Request-ID"] = request_id
    logger.info(
        "request completed",
        extra={
            "request_id": request_id,
            "event": "http.request.completed",
            "actor": "anonymous",
            "ip": client_ip,
            "status": response.status_code,
            "latency_ms": latency_ms,
        },
    )
    return response


@app.middleware("http")
async def add_security_headers(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    response = await call_next(request)
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self' https://cdn.jsdelivr.net https://api.vworld.kr; "
        "script-src 'self' https://cdn.jsdelivr.net https://api.vworld.kr; "
        "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
        "img-src 'self' data: https://api.vworld.kr https://xdworld.vworld.kr;"
    )
    return response


app.add_middleware(
    SessionMiddleware,
    secret_key=settings.secret_key,
    max_age=3600,
    https_only=settings.session_https_only,
    session_cookie=settings.session_cookie_name,
    same_site="lax",
)

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


@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request) -> HTMLResponse:
    return cast(HTMLResponse, templates.TemplateResponse(request, "index.html", {}))


@app.get("/health")
async def healthcheck(request: Request, deep: int = 0) -> dict[str, object]:
    request_id = getattr(request.state, "request_id", "-")
    checks = health_service.evaluate_health_checks(deep=deep, request_id=request_id)
    return {"status": "ok", "request_id": request_id, "checks": checks}
