# 유지보수 가이드

프로젝트: 관심 필지 지도 (Parcel Explorer)  
작성일: 2026-02-11  
최종 수정일: 2026-03-07

## 목적
운영 중인 서비스의 안정성과 보안을 유지하기 위해 필요한 점검, 변경, 장애 대응 절차를 정의한다.

## 문서 진입점
- 문서 포털(한 페이지 허브): [`index.md`](index.md)
- 목표/범위: [`goals.md`](goals.md)
- 구조/흐름: [`architecture.md`](architecture.md)
- 엔지니어링 기준(Tech Stack/코딩 철학/스타일): [`engineering-guidelines.md`](engineering-guidelines.md)
- 보안 위협 모델: [`stride-lite.md`](stride-lite.md)

## 환경 변수
`.env`는 `KEY=value` 형식으로 작성하고 `KEY = value` 형태(등호 주변 공백)는 사용하지 않는다.

### 필수
- `VWORLD_WMTS_KEY`
- `VWORLD_GEOCODER_KEY`
- `ADMIN_ID`
- `ADMIN_PW_HASH`
- `SECRET_KEY`

### 선택
- `ALLOWED_IPS`
- `SESSION_COOKIE_NAME`
- `SESSION_NAMESPACE`
- `MAX_UPLOAD_SIZE_MB`
- `MAX_UPLOAD_ROWS`
- `LOGIN_MAX_ATTEMPTS`
- `LOGIN_COOLDOWN_SECONDS`
- `VWORLD_TIMEOUT_S`
- `VWORLD_RETRIES`
- `VWORLD_BACKOFF_S`
- `SESSION_HTTPS_ONLY`
- `TRUST_PROXY_HEADERS`
- `TRUSTED_PROXY_IPS`
- `UPLOAD_SHEET_NAME`
- `ALLOWED_WEB_TRACK_PATHS`
- `PUBLIC_DOWNLOAD_MAX_SIZE_MB`
- `PUBLIC_DOWNLOAD_ALLOWED_EXTS`
- `PUBLIC_DOWNLOAD_DIR`

## 주기적 점검
- VWorld API 키 유효성 확인
- 관리자 계정 비밀번호 해시 갱신
- 업로드 템플릿 변경 여부 확인(컬럼 스펙)
- DB 파일 권한 및 백업 상태 점검
- SQLite 잠금 징후(`database is locked`) 및 장기 쿼리 발생 여부 점검
- 로그/통계 테이블(`map_event_log`, `raw_query_log`, `web_visit_event`) 증가 추이 점검
- 공개 다운로드 파일(`data/public_download/current.*`) 및 메타(`current.json`) 무결성 점검

## 배포 전 체크리스트
1. `python -m compileall -q app tests`
2. `mypy app tests create_hash.py`
3. `cd frontend && npm ci && npm run typecheck && npm run build`
4. `pytest -q`
5. `docs/engineering-guidelines.md` 기준 준수 여부 확인
6. 환경 변수 설정 확인
7. `data/database.db` 파일 권한 확인
8. `/health` 응답 정상 확인
9. `/api/config`, `/api/lands`, `/api/public-download` 응답 정상 확인
10. `/admin/stats`, `/admin/stats/web`, `/admin/raw-queries/export`, `/admin/lands/geom-refresh*` 권한/응답 정상 확인
11. `POST /logout`(내부망/인증/CSRF) 정상 동작 확인
12. 지도 화면 핵심 사용자 흐름 수동 회귀(검색/엔터/지도 클릭/다운로드/이전·다음/레이어 전환) 확인

## CI/테스트 명령
- `python -m compileall -q app tests`
- `mypy app tests create_hash.py`
- `ruff check app tests`
- `scripts/check_quality_warnings.sh` (파일 길이/복잡도 경고 리포트)
- `cd frontend && npm run typecheck`
- `cd frontend && npm run build`
- `pytest -q`
- `pytest -m unit -q`
- `pytest -m integration -q`
- `pytest -m e2e -q` (`RUN_HTTP_E2E=1` 미설정 시 skip)
- `coverage run -m pytest`
- `coverage report -m`

### 선택 실행
- HTTP E2E 스모크: `RUN_HTTP_E2E=1 pytest -q tests/test_e2e_smoke.py`

## 배포 워크플로 (GitHub Actions)
- 파일: `.github/workflows/deploy.yml`
- 트리거: `main` push, `workflow_dispatch`
- 동작: 배포 전 품질 게이트 실행 후 SSH로 운영 서버 접속, `docker compose` 재배포, `/health` 검증

### 필수 GitHub Secrets
- `PROD_HOST`: 운영 서버 호스트/IP
- `PROD_PORT`: SSH 포트(미설정 시 22)
- `PROD_USER`: SSH 계정
- `PROD_SSH_KEY`: 배포용 개인키
- `PROD_DEPLOY_PATH`: 서버 저장소 경로(미설정 시 `/opt/IdlePublicProperty`)

### 서버 사전 조건
- 지정 경로에 저장소가 이미 clone 되어 있어야 한다.
- 서버에 Docker Engine + Docker Compose plugin이 설치되어 있어야 한다.
- 배포 계정이 해당 경로와 Docker 실행 권한을 가져야 한다.

## API 버전 운영 정책 (`/api` vs `/api/v1`)
- 현재 기본 정책: `/api/v1/*`는 유지되는 호환성(alias) 경로로 운영한다.
- 운영 점검: `/api/*`와 `/api/v1/*`의 응답 계약(필드/상태코드)과 레이트리밋 동작이 동일한지 정기 확인한다.
- 변경 적용: API 계약 변경 시 `/api/*` 반영과 동시에 `/api/v1/*` 동등성 테스트를 수행한다.

### 향후 `/api/v1` 폐기 런북(정책 사전 정의)
1. `T0` 공지: 제거 예정일과 대체 경로(`/api/*`)를 문서/공지 채널에 공지한다.
2. `T0` 헤더 적용: `/api/v1/*` 응답에 `Deprecation: true`를 추가한다.
3. `T0 + 2주` 고지 강화: `Sunset: <RFC1123 datetime>` 및 `Link: <정책 문서>; rel=\"deprecation\"`를 추가하고 재공지한다.
4. `T0 + 4주` 관측 종료: 사용량/소비자 영향(로그 기반)을 확인하고 제거 승인 여부를 판단한다.
5. 승인 후 제거: 라우터 제거, 문서 갱신, 회고 기록을 남긴다.

## 테스트/검증 시나리오 (현행 기준)
### 1. 공개 API 회귀
- `GET /api/lands`: pagination/cursor 동작 유지
- `POST /api/events`, `POST /api/web-events`: 수집/검증/레이트리밋 동작 유지
- `POST /api/web-events`: legacy payload + 확장 payload(referrer/utm/context) 모두 호환 유지
- `GET /api/public-download`: 파일 응답/부재 시 404 유지
- 권장 실행: `pytest -q tests/test_map_pagination.py tests/test_stats_api.py tests/test_public_download_api.py`

### 2. 관리자 핵심 흐름
- 로그인/CSRF/내부망 제한 유지
- 로그아웃 경로 정책 유지 (`POST /logout` + CSRF)
- 엑셀 업로드 + 지오메트리 보강 잡 생성
- 통계 조회/CSV export
- 통계 탭 경계선 재수집 버튼 실행 + 완료 후 수치 갱신 확인
- 권장 실행: `pytest -q tests/test_security_regression.py tests/test_upload_service.py tests/test_geo_service.py tests/test_stats_api.py`

### 3. 프런트 핵심 UX
- 지역/면적 Enter 검색
- 리스트-지도 선택 동기화
- 다운로드 버튼 동작
- 실행 방식: 수동 회귀 + 선택적으로 `RUN_HTTP_E2E=1 pytest -m e2e -q`

### 4. 비기능 검증
- 동일 트래픽 기준 응답 시간 악화 여부(p95) 확인
- 오류율 증가 여부 확인
- 로그 관측성 확인(`X-Request-ID`, 구조화 로그 추적)
- 실행 명령:
  - `python scripts/run_nonfunctional_checks.py --samples 30`
  - 기준선 비교 시: `python scripts/run_nonfunctional_checks.py --samples 30 --baseline <baseline.json>`
- 기본 허용치(미합의 시):
  - p95 regression <= 10%
  - error rate <= 0.5%

## 장애 대응
### 로그인 실패/차단 급증
- `LOGIN_MAX_ATTEMPTS`, `LOGIN_COOLDOWN_SECONDS` 점검
- 내부 IP 허용 목록(`ALLOWED_IPS`) 확인
- 프록시 환경일 경우 `TRUST_PROXY_HEADERS`, `TRUSTED_PROXY_IPS` 설정 확인
- 현재 로그인 제한은 인메모리 상태이므로 멀티 인스턴스 환경에서는 공유 스토어 기반 대안 검토

### 업로드 실패
- 파일 타입/용량 제한 확인 (`MAX_UPLOAD_SIZE_MB`, `MAX_UPLOAD_ROWS`)
- 업로드 컬럼 스펙 및 시트명(`UPLOAD_SHEET_NAME`) 확인
- VWorld API 호출 상태 확인
- `geom_update_jobs` 상태 및 실패 원인 확인

### 공개 다운로드 실패
- `/admin/public-download/meta`로 메타 존재 여부 확인
- `PUBLIC_DOWNLOAD_ALLOWED_EXTS`, `PUBLIC_DOWNLOAD_MAX_SIZE_MB`, `PUBLIC_DOWNLOAD_DIR` 점검
- `data/public_download/current.*`와 `current.json` 파일 존재/권한 확인

### 통계/원시 로그 내보내기 실패
- `/admin/stats`, `/admin/stats/web`, `/admin/raw-queries/export` 응답 및 권한 확인
- `/admin/stats/web`의 breakdown(`channel/device/browser/page/referrer/utm`) 필드 누락 여부 확인
- CSV를 스프레드시트로 열 때 선두 `=`, `+`, `-`, `@` 값이 `'` 접두 처리되어 formula injection이 차단되는지 확인
- 경계선 재수집 상태 확인 시 `/admin/lands/geom-refresh/{job_id}` 응답 및 권한 확인
- `map_event_log`, `raw_query_log`, `web_visit_event` 테이블 상태 확인
- 로그 누락 시 클라이언트 이벤트(`/api/events`, `/api/web-events`) 수집 상태 확인

### `/api/v1` 관련 혼선/문의 증가
- `/api/v1/*`는 현재 폐기 대상이 아닌 호환성 경로임을 안내한다.
- 소비자에게 기본 경로는 `/api/*`임을 안내하고 마이그레이션 권장 공지를 병행한다.
- 폐기 계획이 확정되기 전에는 Deprecation/Sunset 헤더를 임의 적용하지 않는다.

### 설정/비밀번호 변경 후 반영 이슈
- 관리자 화면 변경은 `.env` 파일을 갱신한다.
- 실행 중 프로세스의 설정 객체는 자동 재로딩되지 않으므로 운영 절차에 재시작 단계를 포함한다.
- 변경 직후 로그인/관리자 기능 점검(재로그인 포함)을 수행한다.
- 동일 도메인 다중 앱 운영 시 `SECRET_KEY`, `SESSION_COOKIE_NAME`, `SESSION_NAMESPACE`가 앱별 고유값인지 점검한다.

### 지도 데이터 미표시
- `/api/lands` 응답 확인
- DB `poi.geom` 컬럼 상태 확인
- VWorld API 호출 로그 및 `geom_update_jobs` 실패 건 확인

## 백업/복구
- `data/database.db` 파일을 주기적으로 백업
- `data/public_download/` 디렉터리(`current.*`, `current.json`)를 함께 백업
- 복구 시 파일 권한 및 경로 확인
- 이벤트 로그 테이블 보존 기간(예: N일)과 정리 배치 주기를 운영 정책으로 확정

## 로그
- 요청 ID 및 구조화 필드(event/actor/ip/status)를 사용하여 장애 추적
- 관리자 업로드/로그인/설정변경 로그가 정상적으로 기록되는지 확인
- 이벤트 수집 API 호출량과 오류율을 주기적으로 확인

## 보안 운영
- 세션 시크릿(`SECRET_KEY`) 정기 교체
- VWorld 키(`VWORLD_WMTS_KEY`, `VWORLD_GEOCODER_KEY`) 사용량 모니터링 및 이상 징후 알림 점검
- `VWORLD_GEOCODER_KEY` 유출 의심 시 재발급/교체 런북에 따라 즉시 로테이션 수행
- 공개 데이터 필드 재검토
- 내부망 접근 정책 주기 점검
- 내보내기/다운로드 경로의 접근 통제 점검

## 코드 변경 가이드
- 상세 코딩 원칙/스타일/리뷰 체크리스트는 [`engineering-guidelines.md`](engineering-guidelines.md)를 따른다.
- 기능 변경 시 관련 문서(`architecture`, `maintenance`, `stride-lite`)를 함께 갱신한다.
