import logging
import secrets

import bcrypt
from fastapi import Request
from fastapi.responses import JSONResponse, RedirectResponse, Response

from app.dependencies import SESSION_NAMESPACE_KEY, get_or_create_csrf_token, validate_csrf_token
from app.logging_utils import RequestIdFilter

logger = logging.getLogger(__name__)
logger.addFilter(RequestIdFilter())


def login(request: Request, username: str, password: str, csrf_token: str) -> JSONResponse:
    config = request.app.state.config
    request_id = getattr(request.state, "request_id", "-")
    client_ip = request.client.host if request.client else "unknown"
    actor = username or "anonymous"
    limiter = request.app.state.login_limiter
    limiter_key = f"{client_ip}:{username}"

    if limiter.is_blocked(limiter_key):
        logger.warning(
            "login blocked by limiter",
            extra={
                "request_id": request_id,
                "event": "auth.login.blocked",
                "actor": actor,
                "ip": client_ip,
                "status": 429,
            },
        )
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
    try:
        is_pw_match = bcrypt.checkpw(password.encode("utf-8"), config.ADMIN_PW_HASH.encode("utf-8"))
    except ValueError:
        logger.error(
            "invalid admin password hash configuration",
            extra={
                "request_id": request_id,
                "event": "auth.login.error",
                "actor": actor,
                "ip": client_ip,
                "status": 500,
            },
        )
        return JSONResponse(
            status_code=500,
            content={"success": False, "message": "서버 인증 설정 오류입니다. 관리자에게 문의하세요."},
        )
    except Exception:
        logger.exception(
            "password backend verification failed",
            extra={
                "request_id": request_id,
                "event": "auth.login.error",
                "actor": actor,
                "ip": client_ip,
                "status": 500,
            },
        )
        return JSONResponse(
            status_code=500,
            content={"success": False, "message": "비밀번호 검증 백엔드 오류입니다. 관리자에게 문의하세요."},
        )

    if is_id_match and is_pw_match:
        request.session.clear()
        request.session["user"] = username
        request.session[SESSION_NAMESPACE_KEY] = config.SESSION_NAMESPACE
        request.session["csrf_token"] = get_or_create_csrf_token(request)
        limiter.reset(limiter_key)
        logger.info(
            "login success",
            extra={
                "request_id": request_id,
                "event": "auth.login.success",
                "actor": actor,
                "ip": client_ip,
                "status": 200,
            },
        )
        return JSONResponse(content={"success": True})

    limiter.register_failure(limiter_key)
    logger.warning(
        "login failed",
        extra={
            "request_id": request_id,
            "event": "auth.login.failed",
            "actor": actor,
            "ip": client_ip,
            "status": 401,
        },
    )
    return JSONResponse(
        status_code=401,
        content={"success": False, "message": "아이디 또는 비밀번호가 틀립니다."},
    )


def logout(request: Request) -> RedirectResponse:
    config = request.app.state.config
    request.session.clear()
    response = RedirectResponse(url="/admin/login", status_code=303)
    response.delete_cookie(
        config.SESSION_COOKIE_NAME,
        path="/",
        secure=config.SESSION_HTTPS_ONLY,
        httponly=True,
        samesite="lax",
    )
    return response


def logout_with_csrf(request: Request, csrf_token: str) -> Response:
    if not validate_csrf_token(request, csrf_token):
        return JSONResponse(
            status_code=403,
            content={"success": False, "message": "잘못된 요청입니다. 페이지를 새로고침 해주세요."},
        )
    return logout(request)
