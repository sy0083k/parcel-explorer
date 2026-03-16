# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

After completing any task that modifies code, suggest an appropriate git commit title.

## Mandatory Pre-Check
- 계획 수립/구현/리뷰 전에 `docs/engineering-guidelines.md`를 먼저 확인한다 (최우선 기준).
- `docs/refactoring-strategy.md`, `docs/reports/*`는 **아카이브/기준선 참고용**이며 현행 강제 규칙으로 사용하지 않는다.

## Commands

### Run the app
```bash
uvicorn app.main:app --reload
```

### Install dependencies
```bash
pip install -r requirements.txt
cd frontend && npm ci && cd ..
```

### Build frontend
```bash
cd frontend && npm run build && cd ..
```

### Quality checks (run before any commit)
```bash
python -m compileall -q app tests
mypy app tests create_hash.py
ruff check app tests
scripts/check_quality_warnings.sh
cd frontend && npm run typecheck && npm run build && cd ..
```

### Run tests
```bash
pytest -q                        # all tests
pytest -m unit -q                # unit tests only
pytest -m integration -q         # integration tests only
pytest -m e2e -q                 # e2e tests (no network)
RUN_HTTP_E2E=1 pytest -q tests/test_e2e_smoke.py  # e2e with live HTTP
pytest -q tests/test_services.py # single file
```

### Generate admin password hash
```bash
python create_hash.py
```

## Architecture

### Backend layers (strictly enforced)
```
Router -> Service -> Repository -> (DB)
                 -> Client     -> (VWorld API)
```

- **Routers** (`app/routers/`): thin HTTP layer only — no business logic, no SQL
- **Services** (`app/services/`): all business logic and orchestration
- **Repositories** (`app/repositories/`): all SQL/SQLite access; `poi_repository.py` is a facade
- **Clients** (`app/clients/`): all external API calls (VWorld Geocoder/WFS/WMTS)
- **Validators** (`app/validators/`): upload normalization and validation
- **Config** (`app/core/config.py`): loads all settings from environment variables

### Frontend structure
- `frontend/src/map.ts`: orchestration entry point — assembles modules and binds events
- `frontend/src/map/`: feature modules (`map-view`, `filters`, `list-panel`, `telemetry`, `download-client`, `session-tracker`, `lands-client`, `state`, `types`)
- `frontend/src/http.ts`: **all** network calls must go through this utility (timeout/error normalization)
- `frontend/src/admin.ts`, `login.ts`: page-specific entry points
- 중복 fetch/에러 처리 로직 복붙 금지

### API versioning
`/api/v1/*` is an alias for `/api/*` with identical contracts. Implementation: `map_v1_router.py` reuses `map_router.py`'s `create_router()`. New features go in `/api/*` first; maintain equivalence in `/api/v1/*`.

API 계약(필드/상태코드/의미) 변경 시 `/api/v1/*` 동등성 영향과 운영 절차를 함께 검토한다.

### Key runtime details
- DB: SQLite at `data/database.db`, initialized on startup via `lifespan` in `main.py`
- Sessions: Starlette `SessionMiddleware` with bcrypt-hashed admin credentials
- Security: admin routes require IP allowlist (`ALLOWED_IPS`) + session auth + CSRF on state-changing requests
- Rate limiting: in-memory sliding window — `POST /api/events` (60/min), `POST /api/web-events` (120/min), `GET /public-download` (설정 기반)
- Background jobs: geometry enrichment via VWorld WFS runs as a FastAPI background task; not durable across restarts
- Static assets: Vite builds to `static/dist/`; templates use `vite_assets()` helper to resolve hashed filenames

### Logging pattern
```python
import logging
logger = logging.getLogger(__name__)

logger.error("message", extra={"event": "event_name", "actor": user_id, "status": 400})
logger.exception("message")  # inside except block — includes traceback automatically
```

## Key constraints

- **Layer violations are prohibited**: no SQL in routers/services, no business logic in repositories, no direct HTTP calls outside clients
- Admin settings and password changes hot-reload `app.state.config` immediately (via `rebuild_runtime_state()` in `app/core/runtime_config.py`). Exception: `SESSION_HTTPS_ONLY`'s effect on the `Set-Cookie` header is baked into `SessionMiddleware` at startup and still requires a restart to take effect
- Rate limiting and login attempt tracking are in-memory; they don't share state across multiple instances
- When updating features or security controls, sync the relevant docs: `docs/architecture.md`, `docs/maintenance.md`, `docs/stride-lite.md`, `README.MD`, `docs/index.md`, `docs/TODO.MD`
- Test markers: tag new tests with `@pytest.mark.unit`, `@pytest.mark.integration`, or `@pytest.mark.e2e`
- 변경 설명(PR/커밋 메시지)에는 테스트 결과와 잔여 리스크를 포함한다
- `ruff` is configured with `line-length = 100`, rules `E, F, I, B`, ignoring `E501`
- The `docs/engineering-guidelines.md` is the source of truth for coding standards; `docs/index.md` is the documentation hub

## Security

### Principles
- Never hardcode API keys or `SECRET_KEY`; never modify the production DB directly
- CSRF verification is required on all state-changing endpoints — do not remove it
- Modify `ALLOWED_IPS` validation logic with care
- Session cookies must respect the `SESSION_HTTPS_ONLY` setting
- `VWORLD_GEOCODER_KEY`는 공개 API 응답·로그에 노출하지 않는다. 단, 관리자 전용 경로에서의 운영 목적 노출은 공개 범위와 통제 조건을 문서에 명시한 경우 허용한다.

### Implementation locations
- IP allowlist: `app/core/config.py` (`_parse_allowed_ips`), enforced in `app/routers/admin.py`
- Session middleware: `app/main.py`
- CSRF: admin router (`app/routers/admin.py`)
- Login failure limiting: in-memory (`LoginAttemptLimiter` in `app/auth_security.py`, used in `app/services/auth_service.py`); vulnerable to multi-instance bypass (TODO)
- Formula injection defense: raw-queries CSV export
- 프록시 신뢰 정책: `TRUST_PROXY_HEADERS` / `TRUSTED_PROXY_IPS` — `app/core/config.py`에서 관리

### Known risks (see docs/TODO.MD)
- Login failure counter is in-memory — bypassable in multi-instance deployments

## TODO Governance
- 리스크/개선 작업을 다룰 때 `docs/TODO.MD`를 함께 업데이트한다.
- 상태(`todo/doing/blocked/done`), 목표일, 리뷰 로그를 최신화한다.