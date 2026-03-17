import logging
import secrets
from dataclasses import dataclass

import bcrypt

from app.logging_utils import RequestIdFilter
from app.services.service_models import LimiterAction, RequestContext

logger = logging.getLogger(__name__)
logger.addFilter(RequestIdFilter())


@dataclass(frozen=True)
class LoginCommand:
    context: RequestContext
    username: str
    password: str
    admin_id: str
    admin_password_hash: str
    limiter_blocked: bool


@dataclass(frozen=True)
class LoginResult:
    success: bool
    status_code: int
    message: str | None
    limiter_action: LimiterAction


@dataclass(frozen=True)
class LogoutResult:
    redirect_url: str
    clear_session: bool


def login(command: LoginCommand) -> LoginResult:
    actor = command.username or "anonymous"

    if command.limiter_blocked:
        logger.warning(
            "login blocked by limiter",
            extra={
                "request_id": command.context.request_id,
                "event": "auth.login.blocked",
                "actor": actor,
                "ip": command.context.client_ip,
                "status": 429,
            },
        )
        return LoginResult(
            success=False,
            status_code=429,
            message="로그인 시도가 너무 많습니다. 잠시 후 다시 시도해주세요.",
            limiter_action="none",
        )

    if not command.context.csrf_valid:
        return LoginResult(
            success=False,
            status_code=403,
            message="잘못된 요청입니다. 페이지를 새로고침 해주세요.",
            limiter_action="none",
        )

    is_id_match = secrets.compare_digest(command.username, command.admin_id)
    try:
        is_pw_match = bcrypt.checkpw(
            command.password.encode("utf-8"),
            command.admin_password_hash.encode("utf-8"),
        )
    except ValueError:
        logger.error(
            "invalid admin password hash configuration",
            extra={
                "request_id": command.context.request_id,
                "event": "auth.login.error",
                "actor": actor,
                "ip": command.context.client_ip,
                "status": 500,
            },
        )
        return LoginResult(
            success=False,
            status_code=500,
            message="서버 인증 설정 오류입니다. 관리자에게 문의하세요.",
            limiter_action="none",
        )
    except Exception:
        logger.exception(
            "password backend verification failed",
            extra={
                "request_id": command.context.request_id,
                "event": "auth.login.error",
                "actor": actor,
                "ip": command.context.client_ip,
                "status": 500,
            },
        )
        return LoginResult(
            success=False,
            status_code=500,
            message="비밀번호 검증 백엔드 오류입니다. 관리자에게 문의하세요.",
            limiter_action="none",
        )

    if is_id_match and is_pw_match:
        logger.info(
            "login success",
            extra={
                "request_id": command.context.request_id,
                "event": "auth.login.success",
                "actor": actor,
                "ip": command.context.client_ip,
                "status": 200,
            },
        )
        return LoginResult(
            success=True,
            status_code=200,
            message=None,
            limiter_action="reset",
        )

    logger.warning(
        "login failed",
        extra={
            "request_id": command.context.request_id,
            "event": "auth.login.failed",
            "actor": actor,
            "ip": command.context.client_ip,
            "status": 401,
        },
    )
    return LoginResult(
        success=False,
        status_code=401,
        message="아이디 또는 비밀번호가 틀립니다.",
        limiter_action="register_failure",
    )


def logout(*, csrf_valid: bool) -> LogoutResult:
    if not csrf_valid:
        raise ValueError("csrf_invalid")
    return LogoutResult(redirect_url="/admin/login", clear_session=True)
