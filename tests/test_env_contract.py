from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def parse_env_keys(path: Path) -> set[str]:
    keys: set[str] = set()
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _ = line.split("=", 1)
        keys.add(key.strip())
    return keys


def test_env_example_matches_runtime_contract() -> None:
    keys = parse_env_keys(ROOT / ".env.example")
    required = {
        "VWORLD_WMTS_KEY",
        "VWORLD_GEOCODER_KEY",
        "ADMIN_ID",
        "ADMIN_PW_HASH",
        "SECRET_KEY",
        "ALLOWED_IPS",
        "SESSION_HTTPS_ONLY",
        "SESSION_COOKIE_NAME",
        "SESSION_NAMESPACE",
        "MAX_UPLOAD_SIZE_MB",
        "MAX_UPLOAD_ROWS",
        "LOGIN_MAX_ATTEMPTS",
        "LOGIN_COOLDOWN_SECONDS",
    }
    assert required.issubset(keys)
