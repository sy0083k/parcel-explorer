## Purpose
이 문서는 이 저장소에서 작업하는 모든 에이전트/기여자가 따라야 하는 실행 규칙과 문서 진입 순서를 정의한다.
상세 구현 규칙의 원문은 현행 기준 문서에 두고, 여기서는 작업 전 확인 사항과 실행 상의 필수 요구만 요약한다.

## Source of Truth and Document Roles
- 최우선 규범 기준: `docs/engineering-guidelines.md`
- 보조 현행 문서:
  - `docs/architecture.md`
  - `docs/maintenance.md`
  - `docs/stride-lite.md`
  - `docs/TODO.MD`
  - `README.MD`
- 문서 허브: `docs/index.md`
  - 탐색과 링크 확인을 위한 허브 문서로 사용한다.
  - 구현/리뷰 기준을 독자적으로 정의하는 문서로 취급하지 않는다.

## Mandatory Pre-Check (필수)
- 계획 수립, 구현, 리뷰 전에 `docs/engineering-guidelines.md`를 먼저 확인한다.
- 상세 규칙은 이 문서에 복제하지 말고, 아래 기준 문서를 직접 확인한다.
  - 구조/흐름: `docs/architecture.md`
  - 운영/검증 절차: `docs/maintenance.md`
  - 보안 통제/잔여 위험: `docs/stride-lite.md`
  - 문서 동기화 원칙과 링크 허브: `docs/index.md`
  - 리스크/개선 과제 현황: `docs/TODO.MD`
  - 사용자/운영 요약: `README.MD`
- 답변/PR 설명에는 아래를 명시한다.
  - 가이드라인 준수 여부
  - 충돌 지점(있다면)과 사유/대안
  - 테스트 결과
  - 잔여 리스크

## Execution Reference
- 앱 실행: `uvicorn app.main:app --reload`
- Python 런타임 의존성 설치: `pip install -r requirements.txt`
- Python 개발/품질 의존성 설치: `pip install -r requirements-dev.txt`
- 프런트 의존성 설치: `cd frontend && npm ci`
- 프런트 빌드: `cd frontend && npm run build`
- 관리자 비밀번호 해시 생성: `python create_hash.py`

## Implementation Invariants (MUST)
- 코딩, 아키텍처, 보안, API 계약, 테스트 기준의 원문은 `docs/engineering-guidelines.md`를 따른다.
- 백엔드 레이어 구조와 역할 경계는 `docs/engineering-guidelines.md`와 `docs/architecture.md` 기준을 유지한다.
- 설정 로딩과 환경변수 기준점은 `app/core/config.py`를 따른다.
- 업로드 정규화/검증 관련 구현은 `app/validators/` 계층을 우선 확인한다.
- 프런트 네트워크 호출은 `frontend/src/http.ts`를 재사용한다.
- 지도 페이지 구조는 `frontend/src/map.ts` 오케스트레이션 + `frontend/src/map/*` 기능 모듈 분리를 유지한다.
- 관리자 보호 경로, 세션 인증, CSRF, 프록시 신뢰 정책, `/api` 와 `/api/v1` alias 계약은 각각 현행 기준 문서를 직접 확인하고 그 기준을 따른다.
- 운영 DB를 직접 수정하는 방식으로 문제를 해결하지 않는다.

## Change Control (문서 동기화 필수)
- 기능/정책 변경 시 변경 유형에 맞는 문서를 함께 갱신한다.
- 구조/흐름 변경: `docs/architecture.md`
- 운영/절차 변경: `docs/maintenance.md`
- 보안 통제 변경: `docs/stride-lite.md`
- 사용자/운영 요약 또는 API/환경변수 변경: `README.MD`
- 문서 허브 링크/변경 유형 기준 변경: `docs/index.md`
- 리스크/개선 과제의 상태, 목표일, 리뷰 로그가 바뀌는 경우에만 `docs/TODO.MD`를 갱신한다.

## Quality & Verification (MUST)
- 변경 범위에 맞는 테스트를 추가/수정하고 `pytest -q`를 통과한다.
- 테스트는 `unit` / `integration` / `e2e` 마커 체계를 따른다.
- 배포 전 기본 검증 기준:
  - `python -m compileall -q app tests`
  - `mypy app tests create_hash.py`
  - `ruff check app tests`
  - `scripts/check_quality_warnings.sh`
  - `cd frontend && npm test && npm run typecheck && npm run build`
  - `pytest -m unit -q`
  - `pytest -m integration -q`
  - `pytest -m e2e -q`
  - `pytest -q`
- 선택 실행:
  - `RUN_HTTP_E2E=1 pytest -q tests/test_e2e_smoke.py`
  - `PLAYWRIGHT_EXECUTABLE_PATH=/usr/bin/chromium RUN_BROWSER_E2E=1 pytest -q tests/test_playwright_e2e.py`
- 변경 설명에는 테스트 결과와 잔여 리스크를 포함한다.

## Operational Notes
- 구조화 로그와 예외 처리 기준은 `docs/engineering-guidelines.md`를 따른다.
- 관리자 설정/비밀번호 변경은 `app.state.config` hot-reload 대상이지만, `SESSION_HTTPS_ONLY`는 `SessionMiddleware` 초기화 시 고정되므로 변경 시 재시작 필요성을 명시한다.
- 로그인/이벤트 레이트리밋은 인메모리 기반이므로 멀티 인스턴스 한계를 설명한다.

## Response Requirements (필수)
- 저장소 파일을 수정한 작업의 최종 응답에는 적절한 git commit title을 함께 제안한다.
- 저장소 파일 변경에는 코드와 문서 변경을 모두 포함한다.
- 파일 변경이 없는 리뷰/조사/계획 작업에는 commit title 제안 의무가 없다.

## Archive Documents
- `docs/refactoring-strategy.md`는 아카이브 문서이며 현행 강제 규칙으로 사용하지 않는다.
- `docs/reports/*` 문서가 존재하더라도 아카이브/기준선 참고용으로만 취급하고, 현행 강제 규칙으로 사용하지 않는다.
