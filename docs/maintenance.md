# 유지보수 가이드

프로젝트: IdlePublicProperty  
작성일: 2026-02-11  
최종 수정일: 2026-02-22

## 목적
운영 중인 서비스의 안정성과 보안을 유지하기 위해 필요한 점검, 변경, 장애 대응 절차를 정의한다.

## 문서 진입점
- 문서 포털(한 페이지 허브): [`index.md`](index.md)
- 목표/범위: [`goals.md`](goals.md)
- 구조/흐름: [`architecture.md`](architecture.md)
- 엔지니어링 기준(Tech Stack/코딩 철학/스타일): [`engineering-guidelines.md`](engineering-guidelines.md)
- 보안 위협 모델: [`stride-lite.md`](stride-lite.md)

## 환경 변수
### 필수
- `VWORLD_WMTS_KEY`
- `VWORLD_GEOCODER_KEY`
- `ADMIN_ID`
- `ADMIN_PW_HASH`
- `SECRET_KEY`

### 선택
- `ALLOWED_IPS`
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
- `PUBLIC_DOWNLOAD_MAX_SIZE_MB`
- `PUBLIC_DOWNLOAD_ALLOWED_EXTS`
- `PUBLIC_DOWNLOAD_DIR`

## 주기적 점검
- VWorld API 키 유효성 확인
- 관리자 계정 비밀번호 해시 갱신
- 업로드 템플릿 변경 여부 확인(컬럼 스펙)
- DB 파일 권한 및 백업 상태 점검
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
10. `/admin/stats`, `/admin/stats/web`, `/admin/raw-queries/export` 권한/응답 정상 확인

## CI/테스트 명령
- `python -m compileall -q app tests`
- `mypy app tests create_hash.py`
- `cd frontend && npm run typecheck`
- `cd frontend && npm run build`
- `pytest -q`
- `coverage run -m pytest`
- `coverage report -m`

### 선택 실행
- HTTP E2E 스모크: `RUN_HTTP_E2E=1 pytest -q tests/test_e2e_smoke.py`

## 장애 대응
### 로그인 실패/차단 급증
- `LOGIN_MAX_ATTEMPTS`, `LOGIN_COOLDOWN_SECONDS` 점검
- 내부 IP 허용 목록(`ALLOWED_IPS`) 확인
- 프록시 환경일 경우 `TRUST_PROXY_HEADERS`, `TRUSTED_PROXY_IPS` 설정 확인

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
- `map_event_log`, `raw_query_log`, `web_visit_event` 테이블 상태 확인
- 로그 누락 시 클라이언트 이벤트(`/api/events`, `/api/web-events`) 수집 상태 확인

### 지도 데이터 미표시
- `/api/lands` 응답 확인
- DB `idle_land.geom` 컬럼 상태 확인
- VWorld API 호출 로그 및 `geom_update_jobs` 실패 건 확인

## 백업/복구
- `data/database.db` 파일을 주기적으로 백업
- `data/public_download/` 디렉터리(`current.*`, `current.json`)를 함께 백업
- 복구 시 파일 권한 및 경로 확인

## 로그
- 요청 ID 및 구조화 필드(event/actor/ip/status)를 사용하여 장애 추적
- 관리자 업로드/로그인/설정변경 로그가 정상적으로 기록되는지 확인
- 이벤트 수집 API 호출량과 오류율을 주기적으로 확인

## 보안 운영
- 세션 시크릿(`SECRET_KEY`) 정기 교체
- 공개 데이터 필드 재검토
- 내부망 접근 정책 주기 점검
- 내보내기/다운로드 경로의 접근 통제 점검

## 코드 변경 가이드
- 상세 코딩 원칙/스타일/리뷰 체크리스트는 [`engineering-guidelines.md`](engineering-guidelines.md)를 따른다.
- 기능 변경 시 관련 문서(`architecture`, `maintenance`, `stride-lite`)를 함께 갱신한다.
