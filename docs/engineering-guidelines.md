# Engineering Guidelines

프로젝트: IdlePublicProperty  
작성일: 2026-02-22  
최종 수정일: 2026-02-25

## 문서 목적과 범위
- 이 문서는 테크 스택, 코딩 철학, 코딩 스타일의 단일 기준(Source of Truth)이다.
- 다른 문서(`goals.md`, `architecture.md`, `maintenance.md`)는 본 문서를 참조하고 중복 규칙을 반복하지 않는다.
- 규칙 강도는 다음 기준을 따른다.
  - `MUST`: 반드시 준수. 위반 시 수정 또는 근거 있는 예외 기록이 필요하다.
  - `SHOULD`: 기본 권장. 예외 허용 가능하지만 사유를 남긴다.
  - `AVOID`: 특별한 이유가 없으면 지양한다.

## Canonical Tech Stack (MUST)
- Backend: Python 3.12, FastAPI
- Frontend: TypeScript, Vite, OpenLayers
- Database: SQLite3 (`data/database.db`)
- Data 처리: pandas, openpyxl/xlrd
- Test/품질: pytest, mypy, coverage, compileall
- External API: VWorld (Geocoder, WFS, WMTS)

## Coding Philosophy
- `MUST`: 라우터는 얇게 유지하고 비즈니스 로직은 서비스 계층으로 이동한다.
- `MUST`: DB 접근/SQL은 리포지토리 계층에서만 수행한다.
- `MUST`: 외부 API 호출은 클라이언트 계층에서만 수행한다.
- `MUST`: 설정은 환경변수 중심으로 관리하고 비밀정보 하드코딩을 금지한다.
- `SHOULD`: 실패는 명시적 예외/로그로 관측 가능하게 만든다.
- `SHOULD`: 변경은 작은 단위로 나누고 회귀 테스트를 함께 유지한다.

## Backend Style Rules
- `MUST`: 공개 API 응답에는 필요한 필드만 노출한다.
- `MUST`: 요청 입력값은 경계(라우터/서비스)에서 검증한다.
- `MUST`: 에러 메시지는 사용자 메시지와 내부 로그 메시지를 구분한다.
- `SHOULD`: 웹앱 기능 확장으로 요청/응답 스키마 검증과 타입 관리 복잡도가 증가하면 Pydantic 도입을 검토한다.
- `SHOULD`: 타입 힌트를 유지하고 함수 경계를 명확히 한다.
- `SHOULD`: 매직 넘버는 상수화하고 의미 있는 이름을 사용한다.
- `AVOID`: 라우터에 도메인 로직/DB 로직을 직접 작성하는 패턴.

## Frontend Style Rules
- `MUST`: 네트워크 실패 시 사용자에게 이해 가능한 오류 메시지를 제공한다.
- `MUST`: API 호출 유틸(`frontend/src/http.ts`)을 통해 타임아웃/오류 정규화를 재사용한다.
- `MUST`: 지도 페이지는 `frontend/src/map.ts` 오케스트레이션 + `frontend/src/map/*` 기능 모듈 구조를 유지한다.
- `SHOULD`: UI 상태 처리와 비즈니스 로직을 함수 단위로 분리한다.
- `SHOULD`: 서버 계약(API 필드명/타입)에 맞춘 타입 정의를 유지한다.
- `AVOID`: 페이지 스크립트에서 중복된 fetch/에러 처리 로직을 복붙하는 패턴.

## Security & Config Handling Rules
- `MUST`: 관리자 보호 경로는 내부망 제한을 유지한다. 이 중 인증이 필요한 경로는 세션 인증을 적용하고, 상태 변경 요청(POST/PUT/PATCH/DELETE)은 CSRF 검증을 동시에 적용한다.
- `MUST`: 비밀값(`SECRET_KEY`, 비밀번호 해시 등)은 로그/응답에 노출하지 않는다. 단, 공개 클라이언트 렌더링에 필수인 공개용 키(`VWORLD_WMTS_KEY`)와 관리자 운영 화면에서만 필요한 키(`VWORLD_GEOCODER_KEY`)는 예외적으로 응답 노출을 허용하되, 최소 권한(도메인/용도 제한)과 사용량 모니터링 정책을 유지한다.
- `MUST`: 프록시 환경에서 `TRUST_PROXY_HEADERS`/`TRUSTED_PROXY_IPS` 정책을 명확히 설정한다.
- `SHOULD`: 세션/인증/보안 헤더 변경은 `stride-lite.md`와 함께 검토한다.
- `SHOULD`: 업로드/다운로드 제한값은 환경변수로 조정하고 운영 문서에 반영한다.

## Testing & Definition of Done
- `MUST`: 변경 범위에 맞는 테스트를 추가/수정하고 `pytest -q`를 통과한다.
- `MUST`: 테스트는 `unit`/`integration`/`e2e` 분류 마커 체계를 따른다.
- `MUST`: 배포 전 기본 체크를 수행한다.
  - `python -m compileall -q app tests`
  - `mypy app tests create_hash.py`
  - `ruff check app tests`
  - `scripts/check_quality_warnings.sh`
  - `cd frontend && npm run typecheck && npm run build`
  - `pytest -m unit -q`
  - `pytest -m integration -q`
  - `pytest -m e2e -q`
  - `pytest -q`
- `SHOULD`: 회귀 위험이 큰 보안/인증/업로드 흐름은 통합 테스트로 검증한다.
- `SHOULD`: 변경 설명에 테스트 결과와 잔여 리스크를 함께 기록한다.

## Code Review Checklist
- 구조 일관성: 라우터/서비스/리포지토리 분리가 유지되는가?
- 보안성: 인증/권한/CSRF/내부망 제한이 훼손되지 않았는가?
- 데이터 계약: API 스키마/필드 노출이 의도대로 유지되는가?
- 운영성: 로그, 에러 처리, 설정값 변경 영향이 설명되었는가?
- 품질: 테스트/타입체크/빌드 검증 결과가 포함되었는가?

## Change Control
- 코딩 원칙/스타일 기준 변경 시 이 문서를 우선 수정한다.
- 다른 문서에는 상세 규칙을 복제하지 않고 링크만 유지한다.
- 기능 변경 시 관련 문서(`architecture.md`, `maintenance.md`, `stride-lite.md`)를 함께 갱신한다.
- API/환경변수/운영 절차 변경 시 `README.MD`와 `docs/index.md`의 링크/요약도 함께 갱신한다.
- `docs/refactoring-strategy.md`는 아카이브 문서이며 현행 실행 기준으로 사용하지 않는다.
- 분기별(또는 주요 릴리스 전) 기준 문서 최신성 점검을 권장한다.
