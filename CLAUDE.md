# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

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

### API versioning
`/api/v1/*` is an alias for `/api/*` with identical contracts. Implementation: `map_v1_router.py` reuses `map_router.py`'s `create_router()`. New features go in `/api/*` first; maintain equivalence in `/api/v1/*`.

### Key runtime details
- DB: SQLite at `data/database.db`, initialized on startup via `lifespan` in `main.py`
- Sessions: Starlette `SessionMiddleware` with bcrypt-hashed admin credentials
- Security: admin routes require IP allowlist (`ALLOWED_IPS`) + session auth + CSRF on state-changing requests
- Rate limiting: in-memory sliding window — `POST /api/events` (60/min), `POST /api/web-events` (120/min)
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
- When updating features or security controls, sync the relevant docs: `docs/architecture.md`, `docs/maintenance.md`, `docs/stride-lite.md`, `README.MD`
- Test markers: tag new tests with `@pytest.mark.unit`, `@pytest.mark.integration`, or `@pytest.mark.e2e`
- `ruff` is configured with `line-length = 100`, rules `E, F, I, B`, ignoring `E501`
- The `docs/engineering-guidelines.md` is the source of truth for coding standards

## 🔐 보안 원칙 (Claude에게 중요)
- 절대 하지 말 것: API 키/SECRET_KEY 하드코딩, 운영 DB 직접 수정
- CSRF 검증은 모든 상태 변경 엔드포인트에 필수 (이미 적용됨, 제거 금지)
- ALLOWED_IPS 검증 로직은 신중히 수정할 것
- 세션 쿠키는 SESSION_HTTPS_ONLY 설정을 존중해야 함
- VWorld API 키 중 GEOCODER_KEY는 공개 API/로그에 절대 노출 금지

## 🛡 현재 보안 구현 위치
- IP 허용 목록: app/core/ 또는 app/routers/
- 세션 미들웨어: app/main.py
- CSRF: 관리자 라우터 (app/routers/)
- 로그인 실패 제한: 인메모리 (다중 인스턴스 시 취약, TODO)
- Formula Injection 방어: raw-queries CSV export

## ⚠️ 알려진 보안 리스크 (docs/TODO.MD 참조)
- 로그인 실패 카운터가 인메모리 → 다중 인스턴스 환경에서 우회 가능
- GET /logout 호환성 경로 유지 중 (CSRF 미적용)
```
