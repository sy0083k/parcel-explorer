# 유지보수 가이드

프로젝트: 관심 필지 지도 (Parcel Explorer)  
작성일: 2026-02-11  
최종 수정일: 2026-03-16

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
- `PUBLIC_DOWNLOAD_RATE_LIMIT_PER_MINUTE`
- `PUBLIC_DOWNLOAD_ALLOWED_EXTS`
- `PUBLIC_DOWNLOAD_DIR`
- `RAW_QUERY_EXPORT_MAX_ROWS`
- `RAW_QUERY_EXPORT_TIMEOUT_S`

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
7. 배포 토폴로지가 단일 앱 인스턴스 1개인지 확인(멀티 인스턴스/replica 금지)
8. `data/database.db` 파일 권한 확인
9. `/health` 응답 정상 확인
10. `/api/config`, `/api/lands`, `/api/public-download` 응답 정상 확인
11. `/admin/stats`, `/admin/stats/web`, `/admin/raw-queries/export`, `/admin/lands/geom-refresh*` 권한/응답 정상 확인
12. `POST /logout`(내부망/인증/CSRF) 정상 동작 확인
13. 지도 화면 핵심 사용자 흐름 수동 회귀(검색/엔터/지도 클릭/다운로드/이전·다음/레이어 전환) 확인

## 첫 배포 전 실행 순서
첫 배포는 `GitHub Actions -> SSH -> Docker Compose -> 단일 app 인스턴스 1개`를 기준 경로로 고정한다.

### P0 배포 차단 항목
1. 문서 정합성
   - `README.MD`, `docs/architecture.md`, 본 문서의 로그아웃/설정 반영/단일 인스턴스 설명이 실제 코드와 일치해야 한다.
   - 통과 기준: `POST /logout`만 표기되고, 설정 핫리로드와 `SESSION_HTTPS_ONLY` 재시작 예외가 명시되어 있다.
2. 품질 게이트
   - `python -m compileall -q app tests`
   - `mypy app tests create_hash.py`
   - `ruff check app tests`
   - `scripts/check_quality_warnings.sh`
   - `cd frontend && npm ci && npm run typecheck && npm run build`
   - `pytest -m unit -q`
   - `pytest -m integration -q`
   - `pytest -m e2e -q`
   - `pytest -q`
   - 통과 기준: 실패/멈춤 없이 종료한다. 장시간 테스트가 있으면 원인과 허용 시간을 배포 기록에 남긴다.
3. 운영 환경 확정
   - `.env` 필수값(`VWORLD_*`, `ADMIN_*`, `SECRET_KEY`)과 선택값 중 `ALLOWED_IPS`, `SESSION_*`, `TRUST_PROXY_*`, `PUBLIC_DOWNLOAD_*`를 운영값으로 확정한다.
   - GitHub Secrets(`PROD_HOST`, `PROD_PORT`, `PROD_USER`, `PROD_SSH_KEY`, `PROD_DEPLOY_PATH`)를 등록한다.
   - 통과 기준: `.env`와 GitHub Actions secrets에 placeholder가 남아 있지 않다.

### P1 첫 배포 직후 리스크 저감 항목
1. 서버 리허설
   - `docker compose build`
   - `docker compose up -d`
   - `docker compose ps`
   - `curl http://127.0.0.1:8000/health`
2. 공개/관리자 smoke set
   - `GET /api/config`
   - `GET /api/lands`
   - `GET /api/public-download`
   - `GET /admin/login`
   - `GET /admin/stats`
   - `POST /logout`
   - 통과 기준: 공개 엔드포인트는 기대 상태코드, 관리자 엔드포인트는 내부망/세션 정책대로 응답한다.
3. 관리자 수동 회귀
   - 로그인
   - 업로드
   - 공개 다운로드 파일 업로드
   - 통계 조회
   - 경계선 재수집 시작/상태 조회
   - 로그아웃

### P2 배포 후 후속 개선
1. `scripts/run_nonfunctional_checks.py`로 성능 기준선 저장
2. DB/공개 다운로드 파일 백업 절차 자동화
3. `RISK-002`는 `blocked` 유지: 멀티 인스턴스 요구가 생길 때만 공유 스토어 limiter 작업 착수

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
- 단일 인스턴스 정책: `/api/*`, `/api/v1/*`의 레이트리밋은 단일 프로세스 기준으로만 보장되며, replica 2개 이상 운영은 `RISK-002` 해소 전 금지한다.
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
- `GET /api/public-download`: 파일 응답/부재 시 404 유지, 과다 요청 시 429 + `Retry-After`
- 권장 실행: `pytest -q tests/test_map_pagination.py tests/test_stats_api.py tests/test_public_download_api.py`

### 2. 관리자 핵심 흐름
- 로그인/CSRF/내부망 제한 유지
- 로그아웃 경로 정책 유지 (`POST /logout` + CSRF)
- 엑셀 업로드 + 지오메트리 보강 잡 생성
- 통계 조회/CSV export
- 업로드/CSV export 감사 로그(event/actor/ip/status/upload_filename 또는 export_filename/row_count 또는 exported_row_count) 확인
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

### 5. 성능 기준선 갱신

기준선 JSON 파일 경로: `.agent-memory/ops/baselines/nonfunctional-baseline.json`

기준선을 새로 측정하고 저장하려면 앱이 실행 중인 상태에서 아래 명령을 실행한다:

```bash
python scripts/run_nonfunctional_checks.py --samples 30 \
  | python -c "import sys,json; d=json.load(sys.stdin); print(json.dumps({k: v['p95_ms'] for k,v in d['results'].items()}, indent=2))" \
  > .agent-memory/ops/baselines/nonfunctional-baseline.json
```

이후 비교 시:
```bash
python scripts/run_nonfunctional_checks.py --samples 30 \
  --baseline .agent-memory/ops/baselines/nonfunctional-baseline.json
```

기준선은 주요 변경(성능에 영향을 줄 수 있는 미들웨어/DB/외부 클라이언트 수정) 후 갱신한다.

## 장애 대응
### 로그인 실패/차단 급증
- `LOGIN_MAX_ATTEMPTS`, `LOGIN_COOLDOWN_SECONDS` 점검
- 내부 IP 허용 목록(`ALLOWED_IPS`) 확인
- 프록시 환경일 경우 `TRUST_PROXY_HEADERS`, `TRUSTED_PROXY_IPS` 설정 확인
- 현재 로그인 제한은 인메모리 상태이며 운영 지원 범위는 단일 인스턴스다.
- 운영 중 replica/LB 확장 요구가 생기면 배포를 진행하지 말고 `RISK-002` 공유 스토어 기반 limiter 작업을 선행한다.

### 업로드 실패
- 파일 타입/용량 제한 확인 (`MAX_UPLOAD_SIZE_MB`, `MAX_UPLOAD_ROWS`)
- 업로드 컬럼 스펙 및 시트명(`UPLOAD_SHEET_NAME`) 확인
- VWorld API 호출 상태 확인
- `geom_update_jobs` 상태 및 실패 원인 확인

### 공개 다운로드 실패
- `/admin/public-download/meta`로 메타 존재 여부 확인
- `PUBLIC_DOWNLOAD_ALLOWED_EXTS`, `PUBLIC_DOWNLOAD_MAX_SIZE_MB`, `PUBLIC_DOWNLOAD_RATE_LIMIT_PER_MINUTE`, `PUBLIC_DOWNLOAD_DIR` 점검
- `data/public_download/current.*`와 `current.json` 파일 존재/권한 확인

### 공개 다운로드 파일 무결성 점검

업로드 시 SHA-256 해시가 `current.json`에 자동 기록된다.

**관리자 화면에서 확인:**
`GET /admin/public-download/meta` 응답의 `sha256` 필드를 확인한다.

**서버에서 직접 검증:**
```bash
sha256sum data/public_download/current.<ext>
# 출력값을 current.json의 sha256 필드와 대조한다.
```

배포 후 또는 이상 징후 감지 시 위 절차를 수행한다.

### 통계/원시 로그 내보내기 실패
- `/admin/stats`, `/admin/stats/web`, `/admin/raw-queries/export` 응답 및 권한 확인
- `/admin/stats/web`의 breakdown(`channel/device/browser/page/referrer/utm`) 필드 누락 여부 확인
- `RAW_QUERY_EXPORT_MAX_ROWS`, `RAW_QUERY_EXPORT_TIMEOUT_S` 설정값이 운영 기준에 맞는지 확인
- CSV를 스프레드시트로 열 때 선두 `=`, `+`, `-`, `@` 값이 `'` 접두 처리되어 formula injection이 차단되는지 확인
- 경계선 재수집 상태 확인 시 `/admin/lands/geom-refresh/{job_id}` 응답 및 권한 확인
- `map_event_log`, `raw_query_log`, `web_visit_event` 테이블 상태 확인
- 로그 누락 시 클라이언트 이벤트(`/api/events`, `/api/web-events`) 수집 상태 확인

### `/api/v1` 관련 혼선/문의 증가
- `/api/v1/*`는 현재 폐기 대상이 아닌 호환성 경로임을 안내한다.
- 소비자에게 기본 경로는 `/api/*`임을 안내하고 마이그레이션 권장 공지를 병행한다.
- 폐기 계획이 확정되기 전에는 Deprecation/Sunset 헤더를 임의 적용하지 않는다.

### 설정/비밀번호 변경 후 반영 이슈
- 관리자 화면에서 변경한 설정은 `.env` 파일을 갱신하고 `app.state.config`를 즉시 재로드한다(`rebuild_runtime_state()`).
- **예외 — `SESSION_HTTPS_ONLY`**: `SessionMiddleware(https_only=…)`는 앱 기동 시 고정되므로 이 값을 변경한 경우 반드시 서버를 재시작해야 `Set-Cookie: Secure` 속성이 반영된다. 재시작 없이는 변경 전 값으로 동작이 유지된다.
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
- 관리자 업로드와 raw query export는 감사 로그 필드(upload_filename/row_count/geom_job_id, event_type_filter/exported_row_count/export_filename)가 포함되는지 확인
- 이벤트 수집 API 호출량과 오류율을 주기적으로 확인

## 보안 운영

### 웹 방문 수집 경로 최소화

`ALLOWED_WEB_TRACK_PATHS`는 웹 방문 이벤트를 수집할 페이지 경로 허용 목록이다.

**최소 경로 원칙:** 실제 추적이 필요한 경로만 명시한다. 기본값 `"/"`는 모든 경로를 수집하므로
운영 환경에서는 구체적인 경로 목록으로 교체하는 것을 권장한다.

- 최대 20개 경로까지 등록 가능하다 (초과 시 시작 오류).
- `"/"` 포함 시 서버 시작 시 WARNING 로그가 기록된다.
- 변경 후 `rebuild_runtime_state()`로 즉시 반영되며 재시작이 필요 없다.

- 세션 시크릿(`SECRET_KEY`) 정기 교체
- VWorld 키(`VWORLD_WMTS_KEY`, `VWORLD_GEOCODER_KEY`) 사용량 모니터링 및 이상 징후 알림 점검
- `VWORLD_GEOCODER_KEY` 유출 의심 시 재발급/교체 런북에 따라 즉시 로테이션 수행
- 공개 데이터 필드 재검토
- 내부망 접근 정책 주기 점검
- 내보내기/다운로드 경로의 접근 통제 점검

## 코드 변경 가이드
- 상세 코딩 원칙/스타일/리뷰 체크리스트는 [`engineering-guidelines.md`](engineering-guidelines.md)를 따른다.
- 기능 변경 시 관련 문서(`architecture`, `maintenance`, `stride-lite`)를 함께 갱신한다.
