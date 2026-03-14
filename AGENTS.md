  ## Purpose
  이 문서는 이 저장소에서 작업하는 모든 에이전트/기여자가 따라야 하는 **실행 규칙**이다.
  현행 기준 문서와 코드 구조를 일관되게 유지하는 것이 목적이다.

  ## Source Of Truth
  - 최우선 기준: `docs/engineering-guidelines.md`
  - 보조 기준:
    - `docs/index.md`
    - `docs/architecture.md`
    - `docs/maintenance.md`
    - `docs/stride-lite.md`
    - `docs/TODO.MD`
    - `README.MD`

  ## Mandatory Pre-Check (필수)
  - 계획 수립/구현/리뷰 전에 `docs/engineering-guidelines.md`를 먼저 확인한다.
  - 답변/PR 설명에 아래를 명시한다:
    - 가이드라인 준수 여부
    - 충돌 지점(있다면)과 사유/대안
  - `docs/refactoring-strategy.md`, `docs/reports/*`는 **아카이브/기준선 참고용**이며 현행 강제 규칙으로 사용하지 않는다.

  ## Execution Reference
  - 앱 실행: `uvicorn app.main:app --reload`
  - 의존성 설치: `pip install -r requirements.txt` / `cd frontend && npm ci`
  - 프런트 빌드: `cd frontend && npm run build`
  - 관리자 비밀번호 해시 생성: `python create_hash.py`
  - 품질 점검:
    - `python -m compileall -q app tests`
    - `mypy app tests create_hash.py`
    - `ruff check app tests`
    - `scripts/check_quality_warnings.sh`
    - `cd frontend && npm run typecheck && npm run build`
  - 테스트 실행:
    - `pytest -q`
    - `pytest -m unit -q`
    - `pytest -m integration -q`
    - `pytest -m e2e -q`
    - `RUN_HTTP_E2E=1 pytest -q tests/test_e2e_smoke.py`
    - `pytest -q tests/test_services.py`

  ## Architecture Guardrails (MUST)
  - 백엔드 레이어 체인은 `Router -> Service -> Repository -> (DB)` / `Service -> Client -> (External API)`를 유지한다.
  - Router는 얇게 유지하고 비즈니스 로직은 Service 계층으로 이동한다.
  - DB 접근/SQL은 Repository 계층에서만 수행한다.
  - 외부 API 호출은 Client 계층에서만 수행한다.
  - `app/repositories/poi_repository.py`는 facade로 취급하고, 실제 SQL 책임은 세부 Repository에 둔다.
  - 업로드 정규화/검증은 `app/validators/` 계층에서 수행한다.
  - 설정은 환경변수 중심으로 관리하고 비밀정보 하드코딩을 금지한다.
  - 설정 로딩 단일 기준은 `app/core/config.py`다.

  ## Frontend Guardrails (MUST)
  - 네트워크 호출은 `frontend/src/http.ts` 유틸을 재사용한다.
  - 지도 페이지 구조는 `frontend/src/map.ts`(오케스트레이션) + `frontend/src/map/*`(기능 모듈) 분리를 유지한다.
  - `frontend/src/admin.ts`, `frontend/src/login.ts`는 페이지별 엔트리 포인트로 유지한다.
  - 지도 기능 모듈(`map-view`, `filters`, `list-panel`, `telemetry`, `download-client`, `session-tracker`, `lands-client`, `state`, `types`)의 책임 분리를 해치지 않는다.
  - 중복 fetch/에러 처리 로직 복붙을 금지한다.

  ## Security Invariants (MUST)
  - 관리자 보호 경로는 내부망 제한을 유지한다. 이 중 인증이 필요한 경로는 세션 인증을 적용하고, 상태 변경 요청(POST/PUT/PATCH/DELETE)은 CSRF 검증을 동시에 적용한다.
  - 상태 변경 엔드포인트에서 CSRF 검증을 제거하거나 우회하지 않는다.
  - 비밀값(`SECRET_KEY`, 비밀번호 해시 등)은 로그/응답에 노출하지 않는다. 단, VWorld 키는 운영 목적에 따라 예외를 둘 수 있으며 공개 범위와 통제 조건을 문서에 명시해야 한다.
  - `VWORLD_GEOCODER_KEY`는 공개 API 응답/로그에 노출하지 않는다. 관리자 보호 경로에서의 운영 목적 노출은 공개 범위와 통제 조건을 문서화한 경우에만 허용한다.
  - 운영 DB를 직접 수정하는 방식으로 문제를 해결하지 않는다.
  - `ALLOWED_IPS` 및 관련 검증 로직 변경은 보안 영향 검토 없이 수행하지 않는다.
  - 프록시 환경에서는 `TRUST_PROXY_HEADERS` / `TRUSTED_PROXY_IPS` 정책을 명확히 유지한다.

  ## API & Contract Rules
  - `/api/v1/*`는 `/api/*`와 동등한 호환(alias) 계약을 유지한다.
  - 구현은 `app/routers/map_v1_router.py`가 `app/routers/map_router.py`의 `create_router()`를 재사용하는 구조를 유지한다.
  - 신규 기능/변경은 `/api/*` 기준으로 적용하고 `/api/v1/*` 동등성을 함께 유지한다.
  - API 계약(필드/상태코드/의미) 변경 시 동등성 영향과 운영 절차를 함께 검토한다.

  ## Change Control (문서 동기화 필수)
  기능/정책 변경 시 아래 문서를 함께 갱신한다:
  - 구조/흐름 변경: `docs/architecture.md`
  - 운영/절차 변경: `docs/maintenance.md`
  - 보안 통제 변경: `docs/stride-lite.md`
  - 사용자/운영 요약: `README.MD`
  - 문서 허브 링크: `docs/index.md`
  - 리스크/개선 항목 영향: `docs/TODO.MD`

  ## Testing & DoD (MUST)
  - 변경 범위에 맞는 테스트를 추가/수정하고 `pytest -q`를 통과해야 한다.
  - 새 테스트는 `unit` / `integration` / `e2e` 마커 체계를 따른다.
  - 배포 전 기본 검증 기준:
    - `python -m compileall -q app tests`
    - `mypy app tests create_hash.py`
    - `ruff check app tests`
    - `scripts/check_quality_warnings.sh`
    - `cd frontend && npm run typecheck && npm run build`
    - `pytest -m unit -q`
    - `pytest -m integration -q`
    - `pytest -m e2e -q`
    - `pytest -q`
  - 변경 설명에는 테스트 결과와 잔여 리스크를 포함한다.

  ## Logging & Quality
  - 구조화 로그를 우선 사용하고 `event`, `actor`, `ip`, `status` 등 핵심 필드를 `extra`에 담는다.
  - 예외 블록에서는 traceback 보존을 위해 `logger.exception(...)` 사용을 우선한다.
  - `ruff` 기준은 `line-length = 100`, `E/F/I/B`, `E501 ignore`를 따른다.
  - 문서 허브는 `docs/index.md`이며, 상세 기준 문서 링크를 임의로 분기시키지 않는다.

  ## Operational Notes (작업 시 반영)
  - 관리자 설정/비밀번호 변경은 `app.state.config` hot-reload 대상이지만, `SESSION_HTTPS_ONLY`는 `SessionMiddleware` 초기화 시 고정되므로 변경 시 재시작 필요성을 명시한다.
  - 로그인/이벤트 레이트리밋은 인메모리 기반이므로 멀티 인스턴스 한계를 설명한다.

  ## TODO Governance
  - 리스크/개선 작업을 다룰 때 `docs/TODO.MD`를 함께 업데이트한다.
  - 상태(`todo/doing/blocked/done`), 목표일, 리뷰 로그를 최신화한다.
