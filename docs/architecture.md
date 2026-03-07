# 아키텍처 및 흐름

프로젝트: 관심 필지 지도 (POI Map Geo)  
작성일: 2026-02-11  
최종 수정일: 2026-03-07

## 문서 진입점
- 문서 포털(한 페이지 허브): [`index.md`](index.md)
- 먼저 읽기(왜 만드는가): [`goals.md`](goals.md)
- 엔지니어링 기준(Tech Stack/코딩 철학/스타일): [`engineering-guidelines.md`](engineering-guidelines.md)
- 운영/점검 절차: [`maintenance.md`](maintenance.md)
- 보안 위협 모델: [`stride-lite.md`](stride-lite.md)

## 시스템 개요
관심 필지 지도(POI Map Geo)는 공공 지도 데이터를 제공하고, 관리자 전용 업로드/관리 워크플로를 지원하는 FastAPI 웹 애플리케이션이다. 데이터는 SQLite에 저장되며, VWorld API를 통해 지오메트리(경계선)를 보강한다.

## 런타임 구성
- 애플리케이션 시작 시 lifespan에서 DB 스키마를 초기화한다.
- 공통 미들웨어:
  - 요청 컨텍스트/`X-Request-ID` 부여 및 요청 완료 로그 기록
  - 보안 헤더(`X-Frame-Options`, `X-Content-Type-Options`, `Content-Security-Policy`) 부여
  - `SessionMiddleware` 기반 세션 쿠키 관리
- 라우터 마운트:
  - 인증: `auth.router`
  - 관리자: `admin.router` (`/admin`)
  - 공개 API: `map_router.router` (`/api`)
  - 호환 API alias: `map_v1_router.router` (`/api/v1`)

## 백엔드 레이어 맵
- **라우터**: HTTP 엔드포인트, 요청/응답 매핑, 의존성 연결
  - `app/routers/auth.py`
  - `app/routers/admin.py`
  - `app/routers/map_router.py`
  - `app/routers/map_v1_router.py`
- **서비스**: 비즈니스 로직/오케스트레이션
  - `app/services/auth_service.py`
  - `app/services/upload_service.py`
  - `app/services/land_service.py`
  - `app/services/geo_service.py`
  - `app/services/stats_service.py`
  - `app/services/map_event_service.py`
  - `app/services/web_stats_service.py`
  - `app/services/raw_query_export_service.py`
  - `app/services/admin_settings_service.py`
  - `app/services/public_download_service.py`
  - `app/services/health_service.py`
- **리포지토리**: SQL/영속성 처리
  - `app/repositories/poi_repository.py` (Facade)
  - `app/repositories/land_repository.py`
  - `app/repositories/job_repository.py`
  - `app/repositories/event_repository.py`
  - `app/repositories/web_visit_repository.py`
  - `app/repositories/health_repository.py`
- **클라이언트**: 외부 API 연동
  - `app/clients/vworld_client.py`
  - `app/clients/http_client.py`
- **검증기**: 업로드 정규화/검증
  - `app/validators/land_validators.py`

## 프런트엔드 구조
- **엔트리 포인트**
  - `frontend/src/map.ts`: 지도 페이지 오케스트레이션(모듈 조립/이벤트 바인딩)
  - `frontend/src/admin.ts`: 관리자 페이지 인터랙션
  - `frontend/src/login.ts`: 로그인 페이지 인터랙션
- **지도 기능 모듈(`frontend/src/map/`)**
  - `map-view.ts`: OpenLayers 초기화, 레이어 전환, 피처 렌더링/선택/팝업
  - `filters.ts`: 검색 입력값 수집, 필터 계산, 엔터 처리
  - `list-panel.ts`: 목록 렌더링, 선택/네비게이션, 모바일 바텀시트
  - `telemetry.ts`: 검색/클릭 이벤트 전송
  - `download-client.ts`: 공개 다운로드 API 호출/파일 저장
  - `session-tracker.ts`: 방문 세션 쿠키, heartbeat/pagehide 이벤트 전송
  - `lands-client.ts`: `/api/lands` 페이지네이션 로더(현재는 전체 페이지 선수집)
  - `state.ts`: 지도 화면 상태 저장소
  - `types.ts`: 지도 화면 공통 타입

## 핵심 보안/운영 구성 요소
- **세션 + CSRF**
  - 관리자 보호 경로는 내부망 제한을 유지한다.
  - 인증이 필요한 경로는 세션 인증(`user == ADMIN_ID` + `session_namespace == SESSION_NAMESPACE`)을 동시에 검증한다.
  - 관리자 상태 변경 요청(POST/PUT/PATCH/DELETE)은 CSRF 토큰을 검증한다.
- **레이트 리미팅**
  - 로그인 실패 제한(인메모리)
  - 이벤트 수집 API `POST /api/events`(60/min), `POST /api/web-events`(120/min) 인메모리 슬라이딩 윈도우 제한
- **데이터 저장소**
  - SQLite: `data/database.db`
  - 공개 다운로드 파일: `data/public_download/current.*` + `current.json`
- **외부 API**
  - VWorld (WMTS/Geocoder/WFS)

## 데이터 모델 (SQLite)
### `poi`
- `id` (INTEGER, PK)
- `address` (TEXT)
- `land_type` (TEXT)
- `area` (REAL)
- `adm_property` (TEXT)
- `gen_property` (TEXT)
- `contact` (TEXT)
- `geom` (TEXT, GeoJSON)

### `geom_update_jobs`
- `status` (TEXT: pending/running/done/failed)
- `attempts` (INTEGER)
- `updated_count` (INTEGER)
- `failed_count` (INTEGER)
- `error_message` (TEXT)
- `created_at`, `updated_at` (TEXT, timestamp)

### `map_event_log`
- 지도 검색/클릭 이벤트(집계용)
- `event_type`, `anon_id`, `land_address`, `region_name`, `min_area_value`, `min_area_bucket`, `region_source`, `created_at`

### `raw_query_log`
- 검색/클릭 원시 입력(payload 포함) 저장/내보내기 대상
- `event_type`, `anon_id`, 검색/필터 원문 필드, `raw_payload_json`, `created_at`

### `web_visit_event`
- 웹 방문 이벤트(`visit_start`, `heartbeat`, `visit_end`)
- `anon_id`, `session_id`, `event_type`, `page_path`, `occurred_at`, `client_tz`, `user_agent`, `is_bot`

## API 표
### 공개 엔드포인트
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

### 관리자/인증 엔드포인트
- `GET /admin/login`
- `POST /login`
- `POST /admin/login`
- `POST /logout`
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
- `POST /admin/lands/geom-refresh`
- `GET /admin/lands/geom-refresh/{job_id}`

### API 버전 정책 (`/api` vs `/api/v1`)
- `/api/v1/*`는 유지되는 호환성(alias) 경로이며 `/api/*`와 동등 계약을 제공한다.
- 구현은 `app/routers/map_v1_router.py`가 `app/routers/map_router.py`의 `create_router()`를 재사용한다.
- 동등성 범위는 요청 파라미터 검증, 응답 필드/의미, 상태코드, 이벤트 레이트리밋 동작을 포함한다.
- 신규 기능/계약 변경은 `/api/*` 기준으로 반영하고 `/api/v1/*` 동등성을 함께 검증한다.

## 핵심 흐름
### 공개 지도 조회
1. 클라이언트가 `/api/config`로 지도 설정을 조회한다.
2. 클라이언트가 `/api/lands`를 페이지네이션으로 조회한다.
3. 서버는 `land_service.get_public_land_features_page()`를 통해 `geom`이 있는 데이터만 GeoJSON으로 반환한다.
4. 프런트는 `lands-client.ts`로 페이지를 수집하고 `filters.ts`/`map-view.ts`/`list-panel.ts`에서 화면을 갱신한다.

### 관리자 로그인
1. `GET /admin/login`이 세션에 CSRF 토큰을 발급하고 로그인 페이지를 렌더링한다.
2. `POST /login`이 CSRF 검증, 자격 증명 검증, 세션 갱신, 로그인 실패 제한을 수행한다.

### 관리자 로그아웃
1. `POST /logout`가 내부망/세션 인증/CSRF 검증 후 세션을 종료한다.
2. `GET /logout`는 호환성 경로로 유지되며 내부망 제한을 적용한다.

### 관리자 업로드 및 지오메트리 보강
1. `POST /admin/upload`에서 CSRF, 파일 확장자/용량/행 수/필수 컬럼을 검증한다.
2. 정규화/검증된 행으로 `poi`를 교체 저장한다.
3. 백그라운드 작업으로 지오메트리 보강 잡을 실행한다.

### 관리자 수동 경계선 재수집
1. `POST /admin/lands/geom-refresh`가 활성 잡 존재 여부를 확인한다.
2. 활성 잡이 있으면 기존 `job_id`를 반환하고, 없으면 신규 잡을 백그라운드로 시작한다.
3. 프런트는 `GET /admin/lands/geom-refresh/{job_id}`를 폴링해 완료(`done`/`failed`) 상태를 확인한다.

### 공개 다운로드 파일 제공
1. 관리자가 `/admin/public-download/upload`로 파일을 업로드한다.
2. 서비스는 허용 확장자/용량 검증 후 임시파일 작성 뒤 `current.<ext>`로 원자적 교체하고 메타를 갱신한다.
3. 사용자는 `/api/public-download`로 최신 파일을 다운로드한다.
4. 현재 구현은 응답 시 파일 전체를 메모리로 읽는다(스트리밍 아님).

### 이벤트 수집/통계
1. 클라이언트가 `/api/events`, `/api/web-events`로 검색/클릭/방문 이벤트를 전송한다.
2. 서버는 레이트리밋 적용 후 `map_event_log`, `raw_query_log`, `web_visit_event`에 저장한다.
3. 관리자는 `/admin/stats`, `/admin/stats/web`에서 집계 지표를 조회하고, `/admin/raw-queries/export`로 원시 로그를 CSV 내보내기 한다.
4. CSV 내보내기 시 문자열 셀은 formula injection 방지를 위해 선두 `=`, `+`, `-`, `@` 값을 `'` 접두 처리한다.

### 헬스체크
1. `GET /health`는 DB ping 결과를 반환한다.
2. `GET /health?deep=1`은 DB ping + VWorld geocoder 상태 확인 결과를 함께 반환한다.

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
- `SESSION_COOKIE_NAME`
- `SESSION_NAMESPACE`
- `TRUST_PROXY_HEADERS`
- `TRUSTED_PROXY_IPS`
- `UPLOAD_SHEET_NAME`
- `PUBLIC_DOWNLOAD_MAX_SIZE_MB`
- `PUBLIC_DOWNLOAD_ALLOWED_EXTS`
- `PUBLIC_DOWNLOAD_DIR`

## 운영 참고 및 알려진 제약
- 관리자 보호 경로는 내부 IP 허용 목록으로 제한되며, 인증이 필요한 경로는 세션 인증으로 보호된다.
- 동일 브라우저/도메인에서 다중 앱 운영 시 `SECRET_KEY`, `SESSION_COOKIE_NAME`, `SESSION_NAMESPACE`를 앱별로 분리해야 세션 교차 인식을 방지할 수 있다.
- 프록시 환경에서는 신뢰 프록시(`TRUSTED_PROXY_IPS`) 경유 요청에 한해 `X-Forwarded-For`를 사용한다.
- `VWORLD_WMTS_KEY`는 지도 렌더링을 위해 `/api/config`에서 예외 공개되며, 도메인/용도 제한 및 사용량 모니터링 정책을 유지한다.
- `VWORLD_GEOCODER_KEY`는 관리자 보호 화면(`/admin`)에서 운영 목적으로 예외 공개할 수 있으며, 공개 API/로그 노출은 금지한다.
- 관리자 설정/비밀번호 변경은 `.env`를 갱신하지만 실행 중 설정 객체는 자동 재로딩되지 않는다(재시작 필요).  
  - 관련 TODO: `RISK-001`
- 로그인/이벤트 레이트리밋은 인메모리 구현이며 멀티 인스턴스에서 전역 일관성이 없다.  
  - 관련 TODO: `RISK-002`
- 지오메트리 보강 작업은 백그라운드 태스크 기반이며 프로세스 재시작 시 내구성 한계가 있다.  
  - 관련 TODO: `RISK-003`
- 공개 다운로드 응답은 현재 파일 전체를 메모리로 읽어 전달한다.  
  - 관련 TODO: `RISK-004`
- 지도 프런트는 현재 `/api/lands` 전체 페이지를 초기 로딩에 수집한다.  
  - 관련 TODO: `RISK-005`
- 이벤트 로그/원시 로그는 운영 중 누적되므로 보존/정리 정책을 별도로 운영한다.

## 구현 규칙 참조
- 코딩 원칙/스타일/리뷰 기준은 [`engineering-guidelines.md`](engineering-guidelines.md)를 기준으로 유지한다.
