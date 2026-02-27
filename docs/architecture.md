# 아키텍처 및 흐름

프로젝트: 관심 필지 지도 (POI Map)  
작성일: 2026-02-11  
최종 수정일: 2026-02-27

## 문서 진입점
- 문서 포털(한 페이지 허브): [`index.md`](index.md)
- 먼저 읽기(왜 만드는가): [`goals.md`](goals.md)
- 다음 읽기(어떻게 동작하는가): [`architecture.md`](architecture.md)
- 엔지니어링 기준(Tech Stack/코딩 철학/스타일): [`engineering-guidelines.md`](engineering-guidelines.md)
- 운영/점검 절차: [`maintenance.md`](maintenance.md)

## 시스템 개요
관심 필지 지도 (POI Map)는 공공 지도 데이터를 제공하고, 관리자 전용 업로드 및 관리 워크플로를 지원하는 FastAPI 웹 애플리케이션이다. 데이터는 SQLite에 저장되며 VWorld API를 통해 지오메트리 정보를 보강한다.

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
  - `app/services/map_event_service.py`
  - `app/services/web_stats_service.py`
  - `app/services/raw_query_export_service.py`
  - `app/services/admin_settings_service.py`
  - `app/services/public_download_service.py`
- **리포지토리**: SQL 및 영속성 처리
  - `app/repositories/poi_repository.py` (Facade)
  - `app/repositories/land_repository.py`
  - `app/repositories/job_repository.py`
  - `app/repositories/event_repository.py`
  - `app/repositories/web_visit_repository.py`
- **클라이언트**: 외부 연동
  - `app/clients/vworld_client.py`
  - `app/clients/http_client.py`
- **검증기**: 업로드 정규화 및 검증
  - `app/validators/land_validators.py`

## 프런트엔드 구성
- **엔트리 포인트**
  - `frontend/src/map.ts`: 지도 페이지 오케스트레이션(모듈 조립/이벤트 바인딩)
  - `frontend/src/admin.ts`: 관리자 페이지 인터랙션
  - `frontend/src/login.ts`: 로그인 페이지 인터랙션
- **지도 기능 모듈(`frontend/src/map/`)**
  - `map-view.ts`: OpenLayers 초기화, 레이어 전환, 피처 렌더링/선택/팝업
  - `filters.ts`: 검색 입력값 수집, 필터 계산, 엔터 처리
  - `list-panel.ts`: 목록 렌더링, 선택/네비게이션, 모바일 바텀시트
  - `telemetry.ts`: 검색/클릭 이벤트 전송
  - `download-client.ts`: 공개 다운로드 API 호출 및 파일 저장
  - `session-tracker.ts`: 방문 세션 쿠키, heartbeat/pagehide 이벤트 전송
  - `lands-client.ts`: `/api/lands` 페이지네이션 로더
  - `state.ts`: 지도 화면 상태 저장소
  - `types.ts`: 지도 화면 공통 타입

## 주요 구성 요소
- **세션 + CSRF**: SessionMiddleware가 서명된 세션 쿠키를 관리한다. 관리자 보호 경로는 내부망 제한을 유지하며, 인증이 필요한 경로에는 세션 인증을 적용한다. CSRF 토큰은 세션에 저장되고 관리자 상태 변경 요청(POST/PUT/PATCH/DELETE)에서 검증한다.
- **레이트 리미팅**: 로그인 실패 제한 + 이벤트 수집 API(`POST /api/events`, `POST /api/web-events`)에 인메모리 슬라이딩 윈도우 제한을 적용한다.
- **데이터베이스**: `data/database.db`의 SQLite.
- **외부 API**: 지오코딩 및 WFS 조회를 위한 VWorld.
- **공개 다운로드 파일 관리**: 관리자 업로드 파일을 `data/public_download/current.*`와 메타(`current.json`)로 제공한다.
- **관측 데이터 수집**: 검색/클릭/웹 방문 이벤트를 저장하고 관리자 통계를 제공한다.

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
- 지도 검색/클릭 이벤트(집계용) 저장
- `event_type`, `anon_id`, `land_address`, `region_name`, `min_area_value`, `min_area_bucket`, `region_source`, `created_at`

### `raw_query_log`
- 검색/클릭의 원시 입력(payload 포함) 저장 및 내보내기 대상
- `event_type`, `anon_id`, 검색/필터 입력 원문 필드, `raw_payload_json`, `created_at`

### `web_visit_event`
- 웹 방문 이벤트(`visit_start`, `heartbeat`, `visit_end`) 저장
- `anon_id`, `session_id`, `event_type`, `page_path`, `occurred_at`, `client_tz`, `user_agent`, `is_bot`

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
- `POST /admin/lands/geom-refresh`
- `GET /admin/lands/geom-refresh/{job_id}`

## API 버전 정책
- 현재 정책: `/api/v1/*`는 **유지되는 호환성(alias) 경로**이며 `/api/*`와 동등 계약을 제공한다.
- 구현 방식: `app/routers/map_v1_router.py`는 `app/routers/map_router.py`의 `create_router()`를 재사용한다.
- 동등성 범위: 요청 파라미터 검증, 응답 필드/의미, 상태코드, 이벤트 레이트리밋 동작을 포함한다.
- 변경 원칙: 신규 기능/계약 변경은 `/api/*` 기준으로 반영하고 `/api/v1/*` 동등성을 함께 검증한다.
- 폐기 원칙(향후): Deprecation/Sunset 공지 절차와 관측 기간 후 제거한다(운영 절차는 `maintenance.md` 참조).

## 핵심 데이터 흐름
### 공개 지도 조회
1. 클라이언트가 `/api/config`로 지도 설정을 조회한다.
2. 클라이언트가 `/api/lands`로 GeoJSON 페이지 데이터를 조회한다.
3. 서버의 `land_service.get_public_land_features_page()`가 리포지토리에서 `geom` 있는 데이터만 읽어 GeoJSON으로 반환한다.
4. 프런트는 `frontend/src/map/lands-client.ts`가 모든 페이지를 수집하고, `filters.ts`/`map-view.ts`/`list-panel.ts`가 결과를 화면에 반영한다.

### 관리자 로그인
1. `GET /admin/login`이 세션에 CSRF 토큰을 발급하고 로그인 페이지를 렌더링한다.
2. `POST /login`이 CSRF 검증, 자격 증명 확인, 세션 갱신, 로그인 실패 제한을 수행한다.

### 관리자 업로드
1. `POST /admin/upload`에서 CSRF, 파일 타입, 파일 크기, 행 수를 검증한다.
2. 엑셀 행을 정규화/검증한 뒤 기존 `poi`를 교체 저장한다.
3. 백그라운드 작업으로 지오메트리 보강 잡을 실행한다.

### 지오메트리 보강
1. `geo_service.update_geoms()`가 `geom IS NULL` 행을 배치로 조회한다.
2. 각 행에 대해 `VWorldClient.get_parcel_geometry()`를 호출한다.
3. `geom` 컬럼 업데이트 후 커밋하고 작업 결과를 `geom_update_jobs`에 기록한다.

### 관리자 수동 경계선 재수집
1. 관리자가 통계 탭에서 경계선 재수집 버튼을 클릭하면 `POST /admin/lands/geom-refresh`가 잡을 생성한다.
2. 실행 중 잡이 이미 있으면 기존 `job_id`를 반환하고, 없으면 신규 잡을 백그라운드로 시작한다.
3. 프런트는 `GET /admin/lands/geom-refresh/{job_id}`를 폴링해 완료 상태를 확인한다.
4. 완료(`done`/`failed`) 시 통계(`전체 필지 수`, `경계선 없음 필지 수`)를 다시 조회한다.

### 공개 다운로드 파일 제공
1. 관리자가 `/admin/public-download/upload`로 파일을 업로드한다.
2. 서비스는 허용 확장자/용량 검증 후 `current.<ext>`를 원자적 교체하고 메타를 갱신한다.
3. 사용자는 `/api/public-download`로 최신 파일을 다운로드한다.

### 이벤트 수집/통계
1. 클라이언트가 `/api/events`, `/api/web-events`로 검색/클릭/방문 이벤트를 전송한다.
2. 서버는 레이트리밋을 적용한 뒤 `map_event_log`, `raw_query_log`, `web_visit_event`에 저장한다.
3. 관리자는 `/admin/stats`, `/admin/stats/web`에서 집계 지표를 조회하고, `/admin/raw-queries/export`로 원시 로그를 CSV로 다운로드한다.
4. `/admin/stats`에는 이벤트 통계와 함께 `poi` 기반 경계선 현황(전체/미수집 건수)이 포함된다.

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
- 관리자 보호 경로는 내부 IP 허용 목록으로 제한되며, 인증이 필요한 경로는 세션 인증으로 보호된다.
- 프록시 환경에서는 신뢰 프록시(`TRUSTED_PROXY_IPS`) 경유 요청에 한해 `X-Forwarded-For`를 사용한다.
- VWorld WMTS 키(`VWORLD_WMTS_KEY`)는 지도 렌더링을 위해 `/api/config`에서 예외적으로 제공되며, 운영에서 도메인/용도 제한 및 사용량 모니터링 정책을 유지한다. Geocoder 키(`VWORLD_GEOCODER_KEY`)는 관리자 보호 화면(`/admin`)에서 운영 목적으로 예외 공개를 허용하며, 공개 API 응답/로그 노출은 금지한다.
- 지오메트리 업데이트는 백그라운드 작업이며 VWorld 가용성에 의존한다.
- 관리자 화면에서 설정/비밀번호를 변경하면 `.env`는 갱신되지만, 실행 중 프로세스의 설정 객체는 자동 재로딩되지 않는다(운영 시 재시작 절차 필요).
- 이벤트 로그/원시 로그는 운영 중 누적되므로 보존 및 정리 정책을 별도로 관리해야 한다.

## 구현 규칙 참조
- 코딩 원칙/스타일/리뷰 기준은 [`engineering-guidelines.md`](engineering-guidelines.md)를 기준으로 한다.
