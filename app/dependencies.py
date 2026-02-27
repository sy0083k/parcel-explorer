import secrets
from ipaddress import IPv4Address, IPv6Address, ip_address

from fastapi import HTTPException, Request, status


def is_authenticated(request: Request) -> bool:
    """세션 인증 확인"""
    config = request.app.state.config
    return bool(request.session.get("user") == config.ADMIN_ID)


async def require_authenticated(request: Request) -> None:
    """세션 인증을 강제하는 공통 의존성."""
    if not is_authenticated(request):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="인증이 필요합니다.")


async def check_internal_network(request: Request) -> bool:
    config = request.app.state.config
    if not request.client:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Client Unknown")

    client_ip = _resolve_client_ip(request)
    is_allowed = any(client_ip in network for network in config.ALLOWED_IP_NETWORKS)

    if not is_allowed:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="관리자 페이지는 내부 행정망에서만 접근 가능합니다.",
        )
    return True


def _resolve_client_ip(request: Request) -> IPv4Address | IPv6Address:
    config = request.app.state.config
    if not request.client:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Client Unknown")

    try:
        peer_ip = ip_address(request.client.host)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid Client IP") from exc

    if not config.TRUST_PROXY_HEADERS:
        return peer_ip

    is_trusted_proxy = any(peer_ip in network for network in config.TRUSTED_PROXY_NETWORKS)
    if not is_trusted_proxy:
        return peer_ip

    forwarded_for = request.headers.get("x-forwarded-for", "")
    if not forwarded_for:
        return peer_ip

    first_hop = forwarded_for.split(",")[0].strip()
    if not first_hop:
        return peer_ip

    try:
        return ip_address(first_hop)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid X-Forwarded-For IP",
        ) from exc


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
