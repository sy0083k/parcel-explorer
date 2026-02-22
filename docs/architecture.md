# 아키텍처 및 흐름

프로젝트: IdlePublicProperty  
작성일: 2026-02-11  
최종 수정일: 2026-02-22

## 문서 진입점
- 문서 포털(한 페이지 허브): [`index.md`](index.md)
- 먼저 읽기(왜 만드는가): [`goals.md`](goals.md)
- 다음 읽기(어떻게 동작하는가): [`architecture.md`](architecture.md)
- 엔지니어링 기준(Tech Stack/코딩 철학/스타일): [`engineering-guidelines.md`](engineering-guidelines.md)
- 운영/점검 절차: [`maintenance.md`](maintenance.md)

## 시스템 개요
IdlePublicProperty는 공공 지도 데이터를 제공하고, 관리자 전용 업로드 및 관리 워크플로를 지원하는 FastAPI 웹 애플리케이션이다. 데이터는 SQLite에 저장되며 VWorld API를 통해 지오메트리 정보를 보강한다.

## 레이어 구성
- **라우터**: HTTP 엔드포인트, 요청/응답 매핑, 의존성 연결
  - `app/routers/auth.py`
  - `app/routers/admin.py`
  - `app/routers/map_router.py`
  - `app/routers/map_v1_router.py`
- **서비스**: 비즈니스 로직 및 오케스트레이션
  - `app/services/auth_service.py`
  - `app/services/upload_service.py`
  - `app/services/land_service.py`
  - `app/services/geo_service.py`
  - `app/services/stats_service.py`
  - `app/services/public_download_service.py`
- **리포지토리**: SQL 및 영속성 처리
  - `app/repositories/idle_land_repository.py`
- **클라이언트**: 외부 연동
  - `app/clients/vworld_client.py`
- **검증기**: 업로드 정규화 및 검증
  - `app/validators/land_validators.py`

## 주요 구성 요소
- **세션 + CSRF**: SessionMiddleware가 서명된 세션 쿠키를 관리한다. CSRF 토큰은 세션에 저장되며 관리자 POST 요청에서 검증한다.
- **레이트 리미팅**: 로그인 실패에 대해 인메모리 제한을 적용한다.
- **데이터베이스**: `data/database.db`의 SQLite.
- **외부 API**: 지오코딩 및 WFS 조회를 위한 VWorld.
- **공개 다운로드 파일 관리**: 관리자 업로드 파일을 `data/public_download/current.*`와 메타(`current.json`)로 제공한다.
- **관측 데이터 수집**: 검색/클릭/웹 방문 이벤트를 저장하고 관리자 통계를 제공한다.

## 데이터 모델 (SQLite)
### `idle_land`
- `id` (INTEGER, PK)
- `address` (TEXT)
- `land_type` (TEXT)
- `area` (REAL)
- `adm_property` (TEXT)
- `gen_property` (TEXT)
- `contact` (TEXT)
- `geom` (TEXT, GeoJSON)

### `geom_update_jobs`
- 업로드 이후 지오메트리 보강 작업의 상태/시도 횟수/실패 건수/오류 메시지 관리

### `map_event_log`
- 지도 검색/클릭 이벤트(집계용) 저장

### `raw_query_log`
- 검색/클릭의 원시 입력(payload 포함) 저장 및 내보내기 대상

### `web_visit_event`
- 웹 방문 이벤트(visit_start/heartbeat/visit_end), 세션/봇 여부/체류시간 계산용 데이터 저장

## 공개 엔드포인트
- `GET /`
- `GET /health`
- `GET /api/config`
- `GET /api/lands`
- `POST /api/events`
- `POST /api/web-events`
- `GET /api/public-download`
- `GET /api/v1/config`
- `GET /api/v1/lands`
- `POST /api/v1/events`
- `POST /api/v1/web-events`
- `GET /api/v1/public-download`

## 관리자/인증 엔드포인트
- `GET /admin/login`
- `POST /login`
- `POST /admin/login`
- `GET /logout`
- `GET /admin`
- `POST /admin/upload`
- `POST /admin/public-download/upload`
- `GET /admin/public-download/meta`
- `POST /admin/settings`
- `POST /admin/password`
- `GET /admin/stats`
- `GET /admin/stats/web`
- `GET /admin/raw-queries/export`

## 핵심 데이터 흐름
### 공개 지도 조회
1. 클라이언트가 `/api/config`로 지도 설정을 조회한다.
2. 클라이언트가 `/api/lands`로 GeoJSON 페이지 데이터를 조회한다.
3. `land_service.get_public_land_features_page()`가 리포지토리에서 `geom` 있는 데이터만 읽어 GeoJSON으로 반환한다.

### 관리자 로그인
1. `GET /admin/login`이 세션에 CSRF 토큰을 발급하고 로그인 페이지를 렌더링한다.
2. `POST /login`이 CSRF 검증, 자격 증명 확인, 세션 갱신, 로그인 실패 제한을 수행한다.

### 관리자 업로드
1. `POST /admin/upload`에서 CSRF, 파일 타입, 파일 크기, 행 수를 검증한다.
2. 엑셀 행을 정규화/검증한 뒤 기존 `idle_land`를 교체 저장한다.
3. 백그라운드 작업으로 지오메트리 보강 잡을 실행한다.

### 지오메트리 보강
1. `geo_service.update_geoms()`가 `geom IS NULL` 행을 배치로 조회한다.
2. 각 행에 대해 `VWorldClient.get_parcel_geometry()`를 호출한다.
3. `geom` 컬럼 업데이트 후 커밋하고 작업 결과를 `geom_update_jobs`에 기록한다.

### 공개 다운로드 파일 제공
1. 관리자가 `/admin/public-download/upload`로 파일을 업로드한다.
2. 서비스는 허용 확장자/용량 검증 후 `current.<ext>`를 원자적 교체하고 메타를 갱신한다.
3. 사용자는 `/api/public-download`로 최신 파일을 다운로드한다.

### 이벤트 수집/통계
1. 클라이언트가 `/api/events`, `/api/web-events`로 검색/클릭/방문 이벤트를 전송한다.
2. 서버는 `map_event_log`, `raw_query_log`, `web_visit_event`에 저장한다.
3. 관리자는 `/admin/stats`, `/admin/stats/web`에서 집계 지표를 조회하고, `/admin/raw-queries/export`로 원시 로그를 CSV로 다운로드한다.

## 설정
`app/core/config.py`가 환경변수에서 로드한다.

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

## 운영 참고
- 관리자 엔드포인트는 내부 IP 허용 목록과 세션 인증으로 보호된다.
- 프록시 환경에서는 신뢰 프록시(`TRUSTED_PROXY_IPS`) 경유 요청에 한해 `X-Forwarded-For`를 사용한다.
- VWorld WMTS 키는 지도 사용을 위해 `/api/config`에서 제공된다. Geocoder 키는 서버 전용이다.
- 지오메트리 업데이트는 백그라운드 작업이며 VWorld 가용성에 의존한다.
- 이벤트 로그/원시 로그는 운영 중 누적되므로 보존 및 정리 정책을 별도로 관리해야 한다.

## 구현 규칙 참조
- 코딩 원칙/스타일/리뷰 기준은 [`engineering-guidelines.md`](engineering-guidelines.md)를 기준으로 한다.
