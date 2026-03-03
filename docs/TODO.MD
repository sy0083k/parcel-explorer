# TODO 백로그 (Risk & Improvement Tracker)

프로젝트: 관심 필지 지도 (POI Map Geo)  
작성일: 2026-02-23  
최종 수정일: 2026-03-03  
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
| RISK-001 | P0 | 설정 변경 즉시 반영 불가 | todo | unassigned | 2026-03-09 | 관리자 설정/비밀번호 변경 후 재시작 없이도 반영 전략이 문서화되고 구현/운영 절차가 확정된다. | 관련: `app/core/config.py`, `app/main.py` |
| RISK-002 | P0 | 인메모리 제한기 다중 인스턴스 한계 | todo | unassigned | 2026-03-09 | 로그인/이벤트 레이트리밋이 멀티 인스턴스 환경에서 일관 동작하도록 공유 스토어 전략이 확정된다. | 관련: `app/auth_security.py`, `app/rate_limit.py` |
| RISK-003 | P1 | 업로드 후 지오메트리 작업 내구성 부족 | todo | unassigned | 2026-03-09 | 프로세스 재시작/장애 상황에서도 작업 유실 없이 재시도 가능한 백그라운드 처리 방식이 정의된다. | 관련: `app/services/upload_service.py`, `app/services/geo_service.py` |
| RISK-004 | P1 | 공개 다운로드 응답 메모리 사용량 리스크 | todo | unassigned | 2026-03-09 | 대용량 파일에서도 서버 메모리 급증 없이 다운로드를 처리하도록 스트리밍 응답 방식이 적용된다. | 관련: `app/services/public_download_service.py` |
| RISK-005 | P1 | 프런트 전체 데이터 선적재로 인한 확장성 한계 | todo | unassigned | 2026-03-09 | 데이터 증가 시 초기 로딩 시간/브라우저 메모리 사용을 제어하는 점진 로딩 전략이 수립된다. | 관련: `frontend/src/map/lands-client.ts` |
| RISK-006 | P0 | 다중 앱 세션 교차 인식 위험 | done | team | 2026-03-03 | 동일 브라우저/도메인 운영 시 앱별 `SECRET_KEY`/`SESSION_COOKIE_NAME`/`SESSION_NAMESPACE` 분리와 인증 시 namespace 검증이 적용된다. | 관련: `app/main.py`, `app/dependencies.py`, `app/services/auth_service.py` |

## 주간 리뷰 로그
- 2026-02-23 | reviewer: team | 초기 백로그 문서 생성 및 5개 리스크 등록 | 다음 액션: RISK-001, RISK-002 우선 설계안 작성
- 2026-02-25 | reviewer: team | 관리자 통계 탭에 경계선 현황(전체/미수집) 및 수동 재수집(백그라운드 잡 + 상태 폴링) 기능 반영 | 다음 액션: RISK-003 내구성(프로세스 재시작 시 잡 지속성) 본 과제로 분리 검토
- 2026-02-27 | reviewer: team | 비아카이브 문서를 현재 코드 기준(POI 용어/품질 게이트/API 운영 정책)으로 동기화 | 다음 액션: RISK-001, RISK-002 설계안 확정
- 2026-03-03 | reviewer: team | 세션 교차 인식 방지를 위해 `SESSION_COOKIE_NAME`/`SESSION_NAMESPACE` 도입 및 인증 시 namespace 검증 반영 | 다음 액션: 다중 앱 운영 체크리스트 운영 프로세스에 정착
