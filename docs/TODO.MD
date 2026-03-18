# TODO 백로그 (Risk & Improvement Tracker)

프로젝트: 관심 필지 지도 (Parcel Explorer)  
작성일: 2026-02-23  
최종 수정일: 2026-03-19  
운영 주기: 매주 1회 (월요일 기준)

## 목적
- 코드베이스 주요 리스크와 개선 과제를 단일 문서에서 추적한다.
- 우선순위, 상태, 담당, 목표일, 완료 기준을 명시해 실행 가능성을 높인다.

## 운영 규칙
- 상태(`status`)
  - `todo`: 착수 전
  - `doing`: 진행 중
  - `blocked`: 차단 상태 (사유/해소 조건 필수)
  - `done`: 완료 (성공 기준 충족)
- 우선순위(`priority`)
  - `P0`: 서비스 안정성/보안/데이터 무결성에 즉시 영향
  - `P1`: 단기 개선 필요
  - `P2`: 중장기 개선
- 업데이트 규칙
  - 상태 변경 시 `최종 수정일` 및 리뷰 로그를 함께 갱신한다.
  - `doing` 항목은 최대 2개로 유지한다.
  - `blocked`는 `notes`에 차단 사유와 해소 조건을 반드시 기록한다.

## 우선순위 백로그
| id | priority | title | status | owner | target_date | success_criteria | notes |
|---|---|---|---|---|---|---|---|
| RISK-001 | P0 | 설정 변경 즉시 반영 불가 | done | team | 2026-03-13 | 관리자 설정/비밀번호 변경 후 재시작 없이도 반영 전략이 문서화되고 구현/운영 절차가 확정된다. | `app/core/runtime_config.py` 신규 도입, `RuntimeConfig` + `rebuild_runtime_state()` 구현. `SESSION_HTTPS_ONLY`의 `Set-Cookie` 반영은 재시작 필요(나머지 즉시 반영). |
| RISK-002 | P0 | 인메모리 제한기 다중 인스턴스 한계 | blocked | unassigned | 2026-03-09 | 현재 배포 정책이 단일 인스턴스로 고정되고, 멀티 인스턴스 전환 시 공유 스토어 기반 limiter 선행 도입이 필수 조건으로 문서화된다. | 관련: `app/auth_security.py`, `app/rate_limit.py`. 현재 결정: 미배포 상태 기준 단일 인스턴스만 지원. 차단 사유: 공유 스토어(예: Redis/Valkey) 미도입. 해소 조건: replica 2개 이상 또는 LB 도입 요구가 생기면 공유 스토어 기반 글로벌 limiter 작업 착수. |
| RISK-003 | P1 | 업로드 후 지오메트리 작업 내구성 부족 | done | team | 2026-03-14 | 프로세스 재시작 시 stale 작업(pending/running)을 failed로 처리하고, 누락 geom이 있으면 새 작업을 자동 재시도한다. | `job_repository.mark_stale_geom_jobs_interrupted`, `geo_service.recover_interrupted_geom_jobs`, `main.py` lifespan 연동. 관련: `app/services/geo_service.py`, `app/repositories/job_repository.py`, `app/main.py` |
| RISK-004 | P1 | 공개 다운로드 응답 메모리 사용량 리스크 | done | team | 2026-03-14 | 대용량 파일에서도 서버 메모리 급증 없이 다운로드를 처리하도록 스트리밍 응답 방식이 적용된다. | `Response(content=file.read_bytes())`를 `FileResponse`로 교체하여 청크 스트리밍 적용. 관련: `app/services/public_download_service.py` |
| RISK-005 | P1 | 프런트 전체 데이터 선적재로 인한 확장성 한계 | done | team | 2026-03-14 | 첫 배치(500건) 도착 즉시 지도·목록을 렌더링하고, 나머지 배치를 백그라운드에서 silently 축적한 뒤 완료 시 한 번 재렌더링한다. | `loadAllLandFeatures` → `streamLandFeatures(onBatch)` 교체, `state.appendToOriginalData` 추가, `map.ts` bootstrap 점진 로딩 로직 적용. 관련: `frontend/src/map/lands-client.ts`, `frontend/src/map/state.ts`, `frontend/src/map.ts` |
| RISK-006 | P0 | 다중 앱 세션 교차 인식 위험 | done | team | 2026-03-03 | 동일 브라우저/도메인 운영 시 앱별 `SECRET_KEY`/`SESSION_COOKIE_NAME`/`SESSION_NAMESPACE` 분리와 인증 시 namespace 검증이 적용된다. | 관련: `app/main.py`, `app/dependencies.py`, `app/services/auth_service.py` |
| RISK-007 | P1 | 관리자 로그아웃 경로/CSV 내보내기 보안 정합성 | done | team | 2026-03-07 | 로그아웃 표준 경로를 `POST /logout`+CSRF로 정렬하고, raw query CSV 문자열 셀 formula injection 방어를 적용한다. | 관련: `app/routers/auth.py`, `app/services/auth_service.py`, `app/services/raw_query_export_service.py` |
| RISK-008 | P0 | 배포 파이프라인 미완성(deploy TODO) | done | team | 2026-03-07 | `deploy.yml`의 TODO를 제거하고 배포 전 품질 게이트 + SSH 원격 Docker Compose 재배포 + `/health` 검증이 자동화된다. | 관련: `.github/workflows/deploy.yml`, `README.MD`, `docs/maintenance.md` |
| RISK-009 | P1 | 웹 방문 유입 로그 분석 축 부족 | done | team | 2026-03-07 | `/api/web-events` 확장 필드(referrer/utm/context) 수집, UA 파생 분류 저장, `/admin/stats/web` breakdown(채널/디바이스/브라우저/페이지) 제공 및 `/api/v1/web-events` 호환 유지 | 관련: `app/services/web_stats_service.py`, `app/repositories/web_visit_repository.py`, `frontend/src/map/session-tracker.ts` |
| RISK-010 | P1 | SESSION_HTTPS_ONLY 핫리로드 불가 | done | team | 2026-03-14 | 운영자가 설정 변경 시 `SESSION_HTTPS_ONLY` 재시작 필요성을 명시적으로 인지할 수 있도록 관리자 설정 화면·운영 가이드에 경고가 추가된다. | `app/main.py` L90-97: `SessionMiddleware(https_only=…)`는 기동 시 고정. `rebuild_runtime_state()`로 `Set-Cookie: Secure` 변경 불가. 코드 수정보다 UX 경고·운영 절차 보완이 현실적. STRIDE §S 관련. |
| RISK-011 | P1 | 공개 다운로드 엔드포인트 레이트 리밋 없음 | done | team | 2026-04-10 | `/api/public-download`에 적절한 레이트 리밋이 적용되어 대역폭 소진 공격을 완화한다. | `PUBLIC_DOWNLOAD_RATE_LIMIT_PER_MINUTE`(기본 10/min) 도입, `GET /api/public-download` 및 `/api/v1/public-download`에 `429 + Retry-After` 적용. 관련: `app/routers/map_router.py`, `app/core/config.py`, `tests/test_public_download_api.py` |
| RISK-012 | P2 | 원시 로그 내보내기 쿼리 크기 상한 및 타임아웃 없음 | done | team | 2026-03-15 | export 쿼리에 실행 시간 상한 또는 SQLite `busy_timeout` 설정이 추가되고, limit 상한이 문서화된다. | `app/core/config.py`: `RAW_QUERY_EXPORT_MAX_ROWS`(기본 100000), `RAW_QUERY_EXPORT_TIMEOUT_S`(기본 30.0) 환경변수 추가. `app/services/raw_query_export_service.py`: `threading.Timer` + `conn.interrupt()` 타임아웃 블록 삽입, 초과 시 HTTP 503. 현재 설정값 주입 경로는 `app/services/admin_stats_service.py`. busy_timeout은 Python sqlite3 기본값 5초로 이미 처리됨. STRIDE §D 관련. |
| RISK-013 | P1 | 관리자 액션 감사 로그 불완전 | done | team | 2026-04-10 | 업로드(파일명·행수·결과)와 export(요청자·조건·건수) 이벤트가 구조화 로그로 기록되어 사후 감사가 가능하다. | `admin.upload.*`, `admin.raw_queries_export.*` 감사 로그 추가. 업로드는 파일명/행수/실패사유/`geomJobId`, export는 필터/limit/건수/파일명을 기록. 관련: `app/services/upload_service.py`, `app/routers/admin.py`, `app/services/raw_query_export_service.py` |
| RISK-014 | P2 | 공개 다운로드 파일 무결성 검증 체계 없음 | done | team | 2026-03-15 | 파일 교체 시 SHA-256 해시가 메타데이터에 기록되고, 운영 점검 절차에 해시 검증 단계가 추가된다. | `app/services/public_download_service.py`: 청크 쓰기 루프에 sha256 누적 연산 추가, `current.json`에 `sha256` 필드 기록. `docs/maintenance.md`에 무결성 점검 절차 추가. stride-lite §T 공백 해소. |
| RISK-015 | P2 | 파일 업로드 매직 바이트 검증 없음 | done | team | 2026-03-15 | 업로드 파일의 매직 바이트가 선언된 확장자와 일치하는지 검증하는 단계가 추가된다. | `app/validators/land_validators.py`: `_MAGIC_BYTES` + `check_excel_magic_bytes()` 추가. `app/services/upload_service.py`: 크기 검사 직후 8바이트 매직 바이트 검증 삽입, 불일치 시 HTTP 400 + `reason=invalid_magic_bytes` 감사 로그. 신규 종속성 없음. STRIDE §T 관련. |
| RISK-016 | P2 | CSV formula injection 방어 범위 불완전 | done | team | 2026-03-15 | 방어 대상 prefix 목록이 최신 OWASP CSV Injection 가이드라인 기준으로 검토되고, 필요 시 추가 prefix 또는 대체 직렬화 방식이 적용된다. | `CSV_FORMULA_PREFIXES`에 `\t`(탭, 일부 파서 formula 해석 벡터)·`|`(파이프, LibreOffice Calc DDE 벡터) 추가. 상수 1줄 변경, `_safe_csv_string()` 함수 본체 무수정. 파이프라인 통합 테스트 1개 추가, pytest 전체 통과. STRIDE §I 관련. |
| RISK-017 | P2 | ALLOWED_WEB_TRACK_PATHS 오구성 시 과수집 위험 | done | team | 2026-03-15 | 허용 경로 최대 개수 상한, 기본값 변경 근거 문서화, 운영 가이드에 최소 경로 원칙이 명시된다. | `_MAX_ALLOWED_WEB_TRACK_PATHS=20` 상수 추가 및 중복 제거 후 상한 초과 시 `SettingsError` 발생(`config.py`). `"/"` 포함 시 lifespan 시작 WARNING 로그 추가(`main.py`). `.env.example` 주석에 과수집 위험 명시. `docs/maintenance.md` 최소 경로 원칙 섹션 추가. `stride-lite.md` §I 공백 해소. 신규 단위 테스트 1개(21개 경로 초과 거부), pytest 전체 통과. |
| RISK-018 | P1 | Admin 라우터 통합 테스트 보강 | done | team | 2026-03-18 | POST `/admin/settings`, POST `/admin/password`의 missing/invalid CSRF 거부(403) 시나리오를 HTTP 수준에서 커버하는 통합 테스트가 추가된다. | `tests/test_admin_settings_route.py`에 로그인된 관리자 세션 기준 missing/invalid CSRF 4건을 추가했다. 두 엔드포인트 모두 `403`과 공통 오류 메시지를 검증하고, 설정/비밀번호 변경 부작용이 발생하지 않음을 함께 확인한다. |
| RISK-019 | P1 | Land Service 단독 단위 테스트 부재 | done | team | 2026-03-18 | `land_service`의 빈 결과, `nextCursor` 경계, 공개 필드 필터링을 검증하는 서비스 단위 테스트가 추가된다. | `tests/test_services.py`에 빈 FeatureCollection, 공개 필드 화이트리스트, 페이지 full/partial 경계별 `nextCursor` 검증을 추가했다. API 레벨 페이지네이션 테스트와 역할을 분리해 서비스 계약을 직접 고정한다. |
| RISK-020 | P2 | Chart.js 타입 안전성 부재 | todo | unassigned | - | `frontend/src/admin/charts.ts`의 `any` 사용이 제거되고, 현재 로딩 방식에 맞는 타입 선언 또는 타입 가드가 추가되어 `npm run typecheck`가 통과한다. | `frontend/src/admin/charts.ts`는 `declare const Chart: any`와 차트 인스턴스 `any` 4개로 타입 검사를 우회한다. 현재 Chart.js는 `templates/admin.html`에서 CDN UMD 스크립트로 로드되므로, 해결책은 npm 타입 패키지 고정이 아니라 현 구조에 맞는 타입 보강이어야 한다. |
| RISK-021 | P2 | SQL 테이블명 f-string 보간 | done | team | 2026-03-19 | `app/repositories/land_repository.py`에서 f-string 식별자 보간이 제거되고, 정적 SQL로 동일 동작이 유지된다. | `land_repository.py`의 `TABLE_NAME` 상수를 제거하고 `poi` 테이블명을 정적 SQL 문자열로 직접 명시했다. 값 파라미터 바인딩(`?`)은 유지해 기존 동작/테스트와 정합성을 유지한다. |
| RISK-022 | P2 | .env.example 신규 설정 누락 | done | team | 2026-03-18 | RISK-012에서 추가된 두 설정이 기본값 및 용도 주석과 함께 `.env.example`에 반영된다. | `.env.example`에 `RAW_QUERY_EXPORT_MAX_ROWS=100000`, `RAW_QUERY_EXPORT_TIMEOUT_S=30.0` 및 용도 주석 추가. `app/core/config.py` 기본값과 일치하도록 정렬. `README.MD`, `docs/maintenance.md`, `docs/architecture.md`의 기존 언급과 정합성 확보. |
| RISK-023 | P2 | Admin 에러 메시지 포맷 중복 코드 | done | team | 2026-03-19 | Admin UI 내부의 `HttpError` 메시지 정규화 패턴이 공용 유틸로 정리되고, `npm run typecheck && npm run build`가 통과한다. | `frontend/src/admin/errors.ts`의 `resolveAdminErrorMessage()`로 admin 오류 표시를 단일화. `stats.ts`, `upload.ts`, `geom-refresh.ts`가 공통 유틸을 재사용하도록 정리하고, vitest 단위 테스트 1개 추가. |

## 주간 리뷰 로그
- 2026-02-23 | reviewer: team | 초기 백로그 문서 생성 및 5개 리스크 등록 | 다음 액션: RISK-001, RISK-002 우선 설계안 작성
- 2026-02-25 | reviewer: team | 관리자 통계 탭에 경계선 현황(전체/미수집) 및 수동 재수집(백그라운드 잡 + 상태 폴링) 기능 반영 | 다음 액션: RISK-003 내구성(프로세스 재시작 시 잡 지속성) 본 과제로 분리 검토
- 2026-02-27 | reviewer: team | 비아카이브 문서를 현재 코드 기준(POI 용어/품질 게이트/API 운영 정책)으로 동기화 | 다음 액션: RISK-001, RISK-002 설계안 확정
- 2026-03-03 | reviewer: team | 세션 교차 인식 방지를 위해 `SESSION_COOKIE_NAME`/`SESSION_NAMESPACE` 도입 및 인증 시 namespace 검증 반영 | 다음 액션: 다중 앱 운영 체크리스트 운영 프로세스에 정착
- 2026-03-07 | reviewer: team | `POST /logout`+CSRF 표준화(`GET /logout` 호환 유지) 및 `/admin/raw-queries/export` CSV formula injection 방어 적용 | 다음 액션: RISK-001, RISK-002 우선순위 유지
- 2026-03-13 | reviewer: team | 세션/인증 보안 감사 후속: `GET /logout` 호환 경로 제거(POST+CSRF만 유지), 세션 `max_age=3600` 적용으로 idle timeout 도입 | 다음 액션: RISK-002 공유 스토어 전략 설계
- 2026-03-07 | reviewer: team | `deploy.yml` TODO 제거, 배포 전 품질 게이트 + SSH 원격 Docker Compose 배포 + `/health` 검증 자동화 | 다음 액션: 운영 서버 secrets/environment 보호 규칙 검토
- 2026-03-07 | reviewer: team | 웹 방문 이벤트 확장(referrer/utm/context), UA 파생 분류, `/admin/stats/web` breakdown 지표 확장 반영 | 다음 액션: 로그 보존 주기/집계 고도화 운영 점검
- 2026-03-13 | reviewer: team | RISK-001 구현 완료: `app/core/runtime_config.py` 도입, 설정/비밀번호 변경 후 `app.state.config` 즉시 교체, `login_limiter` 조건부 재생성 | 다음 액션: RISK-002 공유 스토어 전략 설계
- 2026-03-13 | reviewer: team | 보안 감사 후속 백로그 8건 등록(RISK-010~017): SESSION_HTTPS_ONLY 핫리로드 한계 문서화, 공개 다운로드 레이트리밋, export 쿼리 타임아웃, 감사 로그 강화, 다운로드 파일 무결성, 매직 바이트 검증, CSV injection 범위, 웹 수집 경로 과수집 위험 | 다음 액션: RISK-011(레이트리밋), RISK-013(감사 로그) P1 항목 착수 검토
- 2026-03-13 | reviewer: team | RISK-002 운영 결정 확정: 아직 미배포 상태이므로 단일 인스턴스만 지원하고, 멀티 인스턴스 전환은 공유 스토어 기반 limiter 선행 도입 전까지 차단 | 다음 액션: 첫 운영 배포에서 replica/LB 요구 발생 시 Redis/Valkey 기반 글로벌 limiter 설계 재개
- 2026-03-13 | reviewer: team | RISK-011 구현 완료: `PUBLIC_DOWNLOAD_RATE_LIMIT_PER_MINUTE` 설정 도입, `/api/public-download` 및 `/api/v1/public-download`에 IP 기준 분당 제한과 `Retry-After` 적용 | 다음 액션: RISK-013(감사 로그), RISK-004(스트리밍 응답) 우선 검토
- 2026-03-13 | reviewer: team | RISK-013 구현 완료: 업로드와 raw query export에 요청자/조건/결과/실패 사유를 포함한 구조화 감사 로그 추가 | 다음 액션: RISK-004(스트리밍 응답), RISK-010(SESSION_HTTPS_ONLY 경고) 검토
- 2026-03-14 | reviewer: team | RISK-004 구현 완료: 공개 다운로드 응답을 `Response(read_bytes())`에서 `FileResponse`로 교체하여 청크 스트리밍 적용, 메모리 급증 위험 해소 | 다음 액션: RISK-010(SESSION_HTTPS_ONLY 경고) 검토
- 2026-03-14 | reviewer: team | RISK-010 구현 완료: 관리자 설정 화면에서 SESSION_HTTPS_ONLY 필드 옆 재시작 필요 경고 추가, 섹션 설명 및 저장 알림 메시지 정확성 개선, docs/maintenance.md에 예외 사항 명시 | 다음 액션: RISK-003(지오메트리 내구성) 검토
- 2026-03-14 | reviewer: team | RISK-003 구현 완료: 서버 재시작 시 stale 작업(pending/running)을 failed로 처리하고 누락 geom이 있으면 asyncio.to_thread로 신규 작업 자동 재시도. mark_stale_geom_jobs_interrupted 신규 추가, geo_service.recover_interrupted_geom_jobs lifespan 연동 | 다음 액션: RISK-005(프런트 점진 로딩) 또는 RISK-012(export 타임아웃) 검토
- 2026-03-14 | reviewer: team | RISK-005 구현 완료: loadAllLandFeatures를 streamLandFeatures(onBatch)로 교체하여 첫 배치 즉시 렌더링, 나머지 백그라운드 축적 후 최종 완료 시 한 번 재렌더링. state.appendToOriginalData 추가 | 다음 액션: RISK-012(export 타임아웃) 검토
- 2026-03-15 | reviewer: team | RISK-015 구현 완료: `check_excel_magic_bytes()` 추가(land_validators.py), 업로드 크기 검사 직후 8바이트 매직 바이트 대조 삽입, 불일치 시 HTTP 400 + 감사 로그. 신규 종속성 없음. 기존 테스트 매직 바이트 프리픽스 교체 + 신규 거부 테스트 2개 추가, pytest 전체 통과 | 다음 액션: RISK-012(export 쿼리 타임아웃) 검토
- 2026-03-15 | reviewer: team | RISK-012 구현 완료: `RAW_QUERY_EXPORT_MAX_ROWS`/`RAW_QUERY_EXPORT_TIMEOUT_S` 환경변수 도입(config.py), `threading.Timer`+`conn.interrupt()` 타임아웃 블록 추가(raw_query_export_service.py), 관리자 통계 계층에서 설정값 주입. 신규 단위 테스트 2개(max_rows 클램프, 503 타임아웃), pytest 전체 통과 | 다음 액션: 잔여 P2 항목 검토
- 2026-03-17 | reviewer: team | P1 stats 계층 정리 1차 완료: `app/services/stats_service.py` 제거, 공개 이벤트 라우터가 `map_event_service`/`web_stats_service`를 직접 호출하도록 재배선, 관리자 통계/웹 통계/export 설정 주입을 `admin_stats_service`로 분리. 관련 단위/통합 테스트 통과 | 다음 액션: `web_stats_service` 내부 분해(P1 다음 단계) 착수
- 2026-03-17 | reviewer: team | P1 웹 방문 통계 서비스 분해 1차 완료: `web_stats_service`를 facade로 유지한 채 ingest/normalizers/queries/presenter 모듈로 책임 분리. 기존 API 계약 유지, 새 단위 테스트 추가, 기존 facade 테스트 호환 유지 | 다음 액션: facade 재-export 축소 여부와 `web_visit_repository` 후속 분해 검토
- 2026-03-17 | reviewer: team | P1 공개 이벤트 transport 경계 정리 완료: `map_router`는 request primitive 추출·레이트리밋·HTTP 매핑만 유지하고, payload-to-command 조립을 `app/services/public_event_commands.py`로 이동. `WebVisitContext` 도입으로 서비스 입력명을 transport-neutral 하게 정리, `/api`·`/api/v1` 계약 및 기존 상태코드/429 동작 유지 | 다음 액션: `web_visit_repository` schema/write/query 후속 분해 검토
- 2026-03-18 | reviewer: team | P1 web visit repository 후속 분해 완료: `web_visit_repository`를 facade로 유지한 채 schema/write/query 모듈로 SQL 책임을 분리. 기존 서비스 import와 함수 시그니처는 유지했고, repository 테스트 호환과 문서 레이어 맵을 갱신 | 다음 액션: `session-tracker` 책임 분리 또는 `poi_repository` 사용 축소 검토
- 2026-03-18 | reviewer: team | P1 `poi_repository` 제거 완료: 앱 bootstrap은 `schema_repository.init_app_schema()`로 단일화했고, 서비스/테스트는 `land/job/event/web_visit` repository와 `tests/db_helpers.py`를 직접 사용하도록 전환했다. `app/repositories/poi_repository.py` 삭제, E2E/통합 테스트 시드 중복 제거, 구조 문서 갱신 | 다음 액션: `app/routers/admin.py` helper 경계 슬림화 검토
- 2026-03-18 | reviewer: team | P1 `admin.router` 슬림화 1차 완료: request context/logging/CSV 응답 생성 책임을 `app/routers/admin_support.py`로 분리하고, `admin.py`는 HTTP 매핑·command 조립·background task 등록 중심으로 축소했다. raw query export 감사 로그 필드와 관리자 보안 정책은 유지 | 다음 액션: 관리자 라우트 helper/서비스 경계 추가 단순화 필요 여부 추적
- 2026-03-15 | reviewer: team | RISK-016 구현 완료: `CSV_FORMULA_PREFIXES`에 `\t`(탭, 일부 파서 formula 해석 벡터)·`|`(파이프, LibreOffice Calc DDE 벡터) 추가. 상수 1줄 변경, `_safe_csv_string()` 함수 본체 무수정. 파이프라인 통합 테스트 1개 추가, pytest 전체 통과 | 다음 액션: RISK-014(다운로드 파일 무결성), RISK-017(웹 수집 경로 과수집) 잔여 P2 항목 검토
- 2026-03-15 | reviewer: team | RISK-014 구현 완료: 청크 쓰기 루프에 sha256 누적 연산 추가, `current.json`에 `sha256` 필드 기록. `docs/maintenance.md`에 무결성 점검 절차 추가, stride-lite §T 공백 해소 | 다음 액션: RISK-017(웹 수집 경로 과수집) 잔여 P2 항목 검토
- 2026-03-15 | reviewer: team | RISK-017 구현 완료: `ALLOWED_WEB_TRACK_PATHS` 최대 20개 상한 추가(초과 시 `SettingsError`), `"/"` 포함 시 시작 WARNING 로그, `.env.example` 주석 과수집 위험 명시, `docs/maintenance.md` 최소 경로 원칙 섹션, stride-lite §I 공백 해소. 신규 단위 테스트 1개, pytest 전체 통과 | 다음 액션: 잔여 P2 항목 없음 — P1 항목 검토
- 2026-03-16 | reviewer: team | 첫 배포 준비 기준을 문서화: `README.MD`/`docs/architecture.md`의 로그아웃·설정 반영 설명을 코드 기준으로 정정하고, `docs/maintenance.md`에 `첫 배포 전 실행 순서`(P0/P1/P2)를 추가 | 다음 액션: 전체 품질 게이트 종료 시간과 첫 배포 리허설 결과를 운영 기록으로 남김
- 2026-03-17 | reviewer: team | 코드베이스 진단 후속: 발견 이슈 6건을 RISK-018~023으로 등록 (Admin 라우터 테스트 미흡 P1, Land Service 테스트 부재 P1, Chart.js any 타입 P2, SQL f-string 보간 P2, .env.example 누락 P2, Admin 에러 포맷 중복 P2) | 다음 액션: RISK-018, RISK-019 P1 항목 우선 착수 검토
- 2026-03-18 | reviewer: team | RISK-018~023 진단 결과를 반영해 notes/success criteria 정정: 기존 성공 경로 테스트 존재 여부, land_service 커버 범위, Chart.js CDN 로딩 구조, `.env.example` 누락 근거, admin UI 에러 메시지 중복 범위를 실제 코드 상태와 일치하도록 보정 | 다음 액션: RISK-018, RISK-019 P1 항목 우선 착수 검토
- 2026-03-18 | reviewer: team | RISK-018 해결: `tests/test_admin_settings_route.py`에 `/admin/settings`, `/admin/password`의 missing/invalid CSRF 403 회귀 테스트 4건을 추가하고, 설정/비밀번호 갱신 부작용이 발생하지 않음을 함께 검증 | 다음 액션: RISK-019 P1 항목 검토
- 2026-03-18 | reviewer: team | RISK-019 해결: `tests/test_services.py`에 빈 FeatureCollection, 공개 필드 화이트리스트, 페이지 full/partial 경계별 `nextCursor` 검증을 추가해 `land_service` 계약을 단위 테스트로 고정 | 다음 액션: 잔여 P1 항목 없음 — RISK-020 P2 항목 검토
- 2026-03-18 | reviewer: team | RISK-022 해결: `.env.example`에 `RAW_QUERY_EXPORT_MAX_ROWS`, `RAW_QUERY_EXPORT_TIMEOUT_S`와 기본값/주석을 추가해 export 제한 설정의 초기 구성 가시성을 복구 | 다음 액션: 잔여 P2 항목(RISK-020, RISK-021, RISK-023) 검토
- 2026-03-19 | reviewer: team | RISK-023 해결: admin 프런트에 `resolveAdminErrorMessage()` 공통 유틸을 추가하고 `stats`/`upload`/`geom-refresh`의 중복 `HttpError` 표시 로직을 단일화. 프런트 단위 테스트 추가 후 typecheck/build 검증 예정 | 다음 액션: 잔여 P2 항목(RISK-020, RISK-021) 검토
- 2026-03-19 | reviewer: team | RISK-021 해결: `land_repository.py`의 `TABLE_NAME` 상수와 9개 f-string 식별자 보간 쿼리를 제거하고 `poi` 정적 SQL로 정리. repository 회귀 테스트로 동일 동작 확인 | 다음 액션: 잔여 P2 항목 RISK-020 검토
