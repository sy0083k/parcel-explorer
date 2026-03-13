from __future__ import annotations

from typing import Any

from app.auth_security import LoginAttemptLimiter
from app.core.config import Settings


class RuntimeConfig:
    """Mutable runtime configuration object. Replaced atomically on hot-reload."""

    def __init__(self, s: Settings) -> None:
        self.APP_NAME = s.app_name
        self.CENTER_LON = s.map_center_lon
        self.CENTER_LAT = s.map_center_lat
        self.DEFAULT_ZOOM = s.map_default_zoom
        self.VWORLD_WMTS_KEY = s.vworld_wmts_key
        self.VWORLD_GEOCODER_KEY = s.vworld_geocoder_key
        self.BASE_DIR = s.base_dir
        self.ADMIN_ID = s.admin_id
        self.ADMIN_PW_HASH = s.admin_pw_hash
        self.ALLOWED_IP_NETWORKS = s.allowed_ip_networks
        self.MAX_UPLOAD_SIZE_MB = s.max_upload_size_mb
        self.MAX_UPLOAD_ROWS = s.max_upload_rows
        self.LOGIN_MAX_ATTEMPTS = s.login_max_attempts
        self.LOGIN_COOLDOWN_SECONDS = s.login_cooldown_seconds
        self.VWORLD_TIMEOUT_S = s.vworld_timeout_s
        self.VWORLD_RETRIES = s.vworld_retries
        self.VWORLD_BACKOFF_S = s.vworld_backoff_s
        self.SESSION_HTTPS_ONLY = s.session_https_only
        self.SESSION_COOKIE_NAME = s.session_cookie_name
        self.SESSION_NAMESPACE = s.session_namespace
        self.TRUST_PROXY_HEADERS = s.trust_proxy_headers
        self.TRUSTED_PROXY_NETWORKS = s.trusted_proxy_networks
        self.UPLOAD_SHEET_NAME = s.upload_sheet_name
        self.ALLOWED_WEB_TRACK_PATHS = s.allowed_web_track_paths
        self.PUBLIC_DOWNLOAD_MAX_SIZE_MB = s.public_download_max_size_mb
        self.PUBLIC_DOWNLOAD_ALLOWED_EXTS = s.public_download_allowed_exts
        self.PUBLIC_DOWNLOAD_DIR = s.public_download_dir


def rebuild_runtime_state(app: Any, new_settings: Settings) -> None:
    """Replace app.state.config atomically; rebuild login_limiter if its params changed."""
    old_config = app.state.config
    app.state.config = RuntimeConfig(new_settings)

    if (
        old_config.LOGIN_MAX_ATTEMPTS != new_settings.login_max_attempts
        or old_config.LOGIN_COOLDOWN_SECONDS != new_settings.login_cooldown_seconds
    ):
        app.state.login_limiter = LoginAttemptLimiter(
            max_attempts=new_settings.login_max_attempts,
            cooldown_seconds=new_settings.login_cooldown_seconds,
        )
