import secrets
from fastapi import Request, HTTPException, status


def is_authenticated(request: Request):
    """세션 인증 확인"""
    config = request.app.state.config
    return request.session.get("user") == config.ADMIN_ID


def check_internal_network(request: Request):
    config = request.app.state.config
    if not request.client:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Client Unknown")

    client_ip = request.client.host
    is_allowed = any(client_ip.startswith(prefix) for prefix in config.ALLOWED_IP_PREFIXES)

    if not is_allowed:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="관리자 페이지는 내부 행정망에서만 접근 가능합니다.",
        )
    return True


def get_or_create_csrf_token(request: Request) -> str:
    token = request.session.get("csrf_token")
    if not token:
        token = secrets.token_urlsafe(32)
        request.session["csrf_token"] = token
    return token


def validate_csrf_token(request: Request, token_from_form: str | None) -> bool:
    session_token = request.session.get("csrf_token")
    if not session_token or not token_from_form:
        return False
    return secrets.compare_digest(session_token, token_from_form)
