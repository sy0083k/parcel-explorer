# TODO 백로그 (Risk & Improvement Tracker)

프로젝트: 관심 필지 지도 (Parcel Explorer)  
작성일: 2026-02-23  
최종 수정일: 2026-03-13  
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
| RISK-003 | P1 | 업로드 후 지오메트리 작업 내구성 부족 | todo | unassigned | 2026-03-09 | 프로세스 재시작/장애 상황에서도 작업 유실 없이 재시도 가능한 백그라운드 처리 방식이 정의된다. | 관련: `app/services/upload_service.py`, `app/services/geo_service.py` |
| RISK-004 | P1 | 공개 다운로드 응답 메모리 사용량 리스크 | done | team | 2026-03-14 | 대용량 파일에서도 서버 메모리 급증 없이 다운로드를 처리하도록 스트리밍 응답 방식이 적용된다. | `Response(content=file.read_bytes())`를 `FileResponse`로 교체하여 청크 스트리밍 적용. 관련: `app/services/public_download_service.py` |
| RISK-005 | P1 | 프런트 전체 데이터 선적재로 인한 확장성 한계 | todo | unassigned | 2026-03-09 | 데이터 증가 시 초기 로딩 시간/브라우저 메모리 사용을 제어하는 점진 로딩 전략이 수립된다. | 관련: `frontend/src/map/lands-client.ts` |
| RISK-006 | P0 | 다중 앱 세션 교차 인식 위험 | done | team | 2026-03-03 | 동일 브라우저/도메인 운영 시 앱별 `SECRET_KEY`/`SESSION_COOKIE_NAME`/`SESSION_NAMESPACE` 분리와 인증 시 namespace 검증이 적용된다. | 관련: `app/main.py`, `app/dependencies.py`, `app/services/auth_service.py` |
| RISK-007 | P1 | 관리자 로그아웃 경로/CSV 내보내기 보안 정합성 | done | team | 2026-03-07 | 로그아웃 표준 경로를 `POST /logout`+CSRF로 정렬하고, raw query CSV 문자열 셀 formula injection 방어를 적용한다. | 관련: `app/routers/auth.py`, `app/services/auth_service.py`, `app/services/raw_query_export_service.py` |
| RISK-008 | P0 | 배포 파이프라인 미완성(deploy TODO) | done | team | 2026-03-07 | `deploy.yml`의 TODO를 제거하고 배포 전 품질 게이트 + SSH 원격 Docker Compose 재배포 + `/health` 검증이 자동화된다. | 관련: `.github/workflows/deploy.yml`, `README.MD`, `docs/maintenance.md` |
| RISK-009 | P1 | 웹 방문 유입 로그 분석 축 부족 | done | team | 2026-03-07 | `/api/web-events` 확장 필드(referrer/utm/context) 수집, UA 파생 분류 저장, `/admin/stats/web` breakdown(채널/디바이스/브라우저/페이지) 제공 및 `/api/v1/web-events` 호환 유지 | 관련: `app/services/web_stats_service.py`, `app/repositories/web_visit_repository.py`, `frontend/src/map/session-tracker.ts` |
| RISK-010 | P1 | SESSION_HTTPS_ONLY 핫리로드 불가 | todo | unassigned | 2026-04-10 | 운영자가 설정 변경 시 `SESSION_HTTPS_ONLY` 재시작 필요성을 명시적으로 인지할 수 있도록 관리자 설정 화면·운영 가이드에 경고가 추가된다. | `app/main.py` L90-97: `SessionMiddleware(https_only=…)`는 기동 시 고정. `rebuild_runtime_state()`로 `Set-Cookie: Secure` 변경 불가. 코드 수정보다 UX 경고·운영 절차 보완이 현실적. STRIDE §S 관련. |
| RISK-011 | P1 | 공개 다운로드 엔드포인트 레이트 리밋 없음 | done | team | 2026-04-10 | `/api/public-download`에 적절한 레이트 리밋이 적용되어 대역폭 소진 공격을 완화한다. | `PUBLIC_DOWNLOAD_RATE_LIMIT_PER_MINUTE`(기본 10/min) 도입, `GET /api/public-download` 및 `/api/v1/public-download`에 `429 + Retry-After` 적용. 관련: `app/routers/map_router.py`, `app/core/config.py`, `tests/test_public_download_api.py` |
| RISK-012 | P2 | 원시 로그 내보내기 쿼리 크기 상한 및 타임아웃 없음 | todo | unassigned | 2026-05-01 | export 쿼리에 실행 시간 상한 또는 SQLite `busy_timeout` 설정이 추가되고, limit 상한이 문서화된다. | `app/routers/admin.py` L201-216: 기본 `limit=10000`. `app/services/raw_query_export_service.py` L27: 100,000으로 클램프. 쿼리 실행 타임아웃 없음. 현재 SQLite 단일 인스턴스로 위험 낮음. STRIDE §D 관련. |
| RISK-013 | P1 | 관리자 액션 감사 로그 불완전 | done | team | 2026-04-10 | 업로드(파일명·행수·결과)와 export(요청자·조건·건수) 이벤트가 구조화 로그로 기록되어 사후 감사가 가능하다. | `admin.upload.*`, `admin.raw_queries_export.*` 감사 로그 추가. 업로드는 파일명/행수/실패사유/`geomJobId`, export는 필터/limit/건수/파일명을 기록. 관련: `app/services/upload_service.py`, `app/routers/admin.py`, `app/services/raw_query_export_service.py` |
| RISK-014 | P2 | 공개 다운로드 파일 무결성 검증 체계 없음 | todo | unassigned | 2026-05-01 | 파일 교체 시 SHA-256 해시가 메타데이터에 기록되고, 운영 점검 절차에 해시 검증 단계가 추가된다. | `app/services/public_download_service.py`: 원자적 파일 교체 수행 중이나 배포 후 무결성 검증 수단 없음. stride-lite §T 공백. 운영 절차·코드 양쪽 보완 필요. |
| RISK-015 | P2 | 파일 업로드 매직 바이트 검증 없음 | todo | unassigned | 2026-05-01 | 업로드 파일의 매직 바이트가 선언된 확장자와 일치하는지 검증하는 단계가 추가된다. | `app/services/upload_service.py` L34-38(확장자), L51-57(MIME): 매직 바이트 검사 없음. `openpyxl` 파싱 시 일부 검증 제공하나 명시적 방어 층 추가 권장. STRIDE §T 관련. |
| RISK-016 | P2 | CSV formula injection 방어 범위 불완전 | todo | unassigned | 2026-05-01 | 방어 대상 prefix 목록이 최신 OWASP CSV Injection 가이드라인 기준으로 검토되고, 필요 시 추가 prefix 또는 대체 직렬화 방식이 적용된다. | `app/services/raw_query_export_service.py` L14: `CSV_FORMULA_PREFIXES = ("=", "+", "-", "@")`. 일부 파서의 `\t`, `|` prefix 미포함. 현재 구현은 표준적이나 부분 구현 수준. STRIDE §I 관련. |
| RISK-017 | P2 | ALLOWED_WEB_TRACK_PATHS 오구성 시 과수집 위험 | todo | unassigned | 2026-05-01 | 허용 경로 최대 개수 상한, 기본값 변경 근거 문서화, 운영 가이드에 최소 경로 원칙이 명시된다. | `app/core/config.py` L157-168: `/` 접두사 검증만 수행, 최대 항목 수 제한·와일드카드 의미 문서 없음. 기본값 `"/"`는 전체 경로 수집에 해당하므로 재검토 필요. stride-lite §I 공백. |

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
