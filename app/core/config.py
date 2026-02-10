import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path


class SettingsError(RuntimeError):
    """Raised when required settings are missing or invalid."""


@dataclass(frozen=True)
class Settings:
    app_name: str
    map_center_lon: float
    map_center_lat: float
    map_default_zoom: int
    vworld_key: str
    admin_id: str
    admin_pw_hash: str
    secret_key: str
    allowed_ip_prefixes: tuple[str, ...]
    base_dir: str


def _load_dotenv_if_present(base_dir: Path) -> None:
    """Load .env file into environment when python-dotenv is unavailable or not preloaded."""
    env_path = base_dir / ".env"
    if not env_path.exists():
        return

    try:
        # Prefer python-dotenv when available.
        from dotenv import load_dotenv

        load_dotenv(dotenv_path=env_path)
        return
    except Exception:
        # Fallback: minimal parser for KEY=VALUE lines.
        pass

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


def _get_required_env(name: str) -> str:
    value = os.getenv(name)
    if value is None or value.strip() == "":
        raise SettingsError(f"Required environment variable is missing: {name}")
    return value.strip()


def _parse_allowed_ips(raw_ips: str) -> tuple[str, ...]:
    prefixes = tuple(ip.strip() for ip in raw_ips.split(",") if ip.strip())
    return prefixes or ("127.0.0.1",)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    base_dir = Path(__file__).resolve().parents[2]
    _load_dotenv_if_present(base_dir)

    return Settings(
        app_name=os.getenv("APP_NAME", "IdlePublicProperty"),
        map_center_lon=float(os.getenv("MAP_CENTER_LON", "126.4500")),
        map_center_lat=float(os.getenv("MAP_CENTER_LAT", "36.7848")),
        map_default_zoom=int(os.getenv("MAP_DEFAULT_ZOOM", "14")),
        vworld_key=_get_required_env("VWORLD_KEY"),
        admin_id=_get_required_env("ADMIN_ID"),
        admin_pw_hash=_get_required_env("ADMIN_PW_HASH"),
        secret_key=_get_required_env("SECRET_KEY"),
        allowed_ip_prefixes=_parse_allowed_ips(os.getenv("ALLOWED_IPS", "127.0.0.1")),
        base_dir=str(base_dir),
    )