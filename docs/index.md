# 문서 포털 (Documentation Hub)

프로젝트: 관심 필지 지도 (Parcel Explorer)  
작성일: 2026-02-22  
최종 수정일: 2026-03-13

## 빠른 시작 경로
1. 왜 만드는가: [`goals.md`](goals.md)
2. 어떻게 동작하는가: [`architecture.md`](architecture.md)
3. 어떤 기준으로 구현하는가: [`engineering-guidelines.md`](engineering-guidelines.md)
4. 어떻게 운영하는가: [`maintenance.md`](maintenance.md)
5. 어떤 보안 위협을 관리하는가: [`stride-lite.md`](stride-lite.md)
6. 어떤 리스크를 우선 개선하는가: [`TODO.MD`](TODO.MD)

## 현행 기준 문서
- `goals.md`
  - 제품/업무 목표, 비목표, 로드맵 후보
- `architecture.md`
  - 시스템 구조, 데이터 흐름, 엔드포인트/설정 요약
- `engineering-guidelines.md`
  - Canonical Tech Stack, 코딩 철학, 코딩 스타일, DoD/리뷰 기준
- `maintenance.md`
  - 운영 점검, 배포 전 체크리스트, 장애 대응, 백업/복구
- `stride-lite.md`
  - STRIDE-lite 기반 위협 모델 및 권장 통제
- `TODO.MD`
  - 우선순위 리스크/개선 백로그, 주간 상태 추적

## 운영 참고 / 콘텐츠 문서
- `video-intro-shotlist.md`
  - 지자체/공공 실무자 대상 소개 영상 샷리스트와 편집 검수 기준

## Archive / 참고 문서
- `refactoring-strategy.md`
  - 리팩토링 단계 전략 및 추진 이력 참고용 문서(현행 운영 기준 아님)
- `reports/*`
  - 단계별 점검 보고서 보관용 문서(현행 운영 기준 아님)

## 기능 변경 시 동시 갱신 대상
| 변경 유형 | 필수 갱신 문서 | 비고 |
|---|---|---|
| API 경로/요청/응답 변경 | `README.MD`, `docs/architecture.md` | 공개/관리자 엔드포인트 표 동기화 |
| 인증/권한/보안 헤더/레이트리밋 변경 | `docs/stride-lite.md`, `docs/maintenance.md`, `README.MD` | 운영 통제와 잔여 위험을 분리 기재 |
| 환경변수/운영 파라미터 변경 | `README.MD`, `docs/architecture.md`, `docs/maintenance.md` | 필수/선택 변수 목록 일치 |
| 품질 게이트/개발 규칙 변경 | `docs/engineering-guidelines.md`, `docs/maintenance.md` | 실행 명령과 DoD 동기화 |
| 제품 목적/범위 변경 | `docs/goals.md`, `docs/index.md` | 비목표 및 로드맵 후보 포함 |

## 문서 운영 원칙
- 코딩 원칙/스타일 변경은 `engineering-guidelines.md`를 먼저 갱신한다.
- 목표/구조/운영/보안 문서는 본인 역할 범위만 유지하고 중복 규칙을 복제하지 않는다.
- 기능 변경 시 해당 문서(구조/운영/보안)를 동시 갱신한다.
- 주요 릴리스 전 문서 링크와 내용 최신성을 점검한다.

## 최신 반영 메모
- 모바일 지도 UX를 단계형 플로우(초기/검색/결과)로 개편한 경우, 사용자 흐름 설명은 `README.MD`에 우선 반영한다.
- VWorld 키 공개 정책은 문서 기준으로 분리 관리한다(`VWORLD_WMTS_KEY`: 공개 지도 렌더링 예외, `VWORLD_GEOCODER_KEY`: 관리자 보호 화면 예외 공개).
- 관리자 통계 탭에 `poi` 경계선 현황(전체/미수집) 및 수동 재수집(잡 시작/상태 폴링) 기능을 반영한 경우, `architecture.md`와 `maintenance.md`를 함께 갱신한다.
- 동일 브라우저/도메인 다중 앱 운영 시 세션 교차 인식을 방지하려면 앱별 `SECRET_KEY`, `SESSION_COOKIE_NAME`, `SESSION_NAMESPACE` 분리를 유지한다.
- 로그아웃은 `POST /logout` + CSRF로만 처리한다.
- `/admin/raw-queries/export` CSV는 문자열 셀 formula injection 완화(`=`, `+`, `-`, `@` 선두 차단)를 유지한다.
- GitHub Deploy 워크플로는 SSH + Docker Compose 재배포(`deploy.yml`)로 운영 기준을 확정했다.
- 웹 방문 이벤트는 referrer/utm/context 확장 수집을 지원하며 `ALLOWED_WEB_TRACK_PATHS` 허용 경로 정책을 유지한다.
- 레거시 `idle_land` 용어/테이블 전환 로직은 제거 완료 상태를 기준으로 문서를 유지한다.
- `RISK-002` 기준으로 현재 배포 정책은 단일 앱 인스턴스만 지원하며, 멀티 인스턴스 전환은 공유 스토어 기반 limiter 도입 전까지 보류한다.
