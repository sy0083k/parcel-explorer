# Phase 0 Invariant Contract Checklist

프로젝트: IdlePublicProperty  
작성일: 2026-02-22  
목적: 리팩토링 중 "동작 불변"을 판정하기 위한 계약 체크리스트

## 1) 공통 불변 규칙
- 공개 API 기본 경로는 `/api/*`로 유지한다.
- `/api/v1/*`는 `/api/*`와 동등한 alias 동작을 유지한다.
- 관리자 기능은 내부망 제한 + 세션 인증 + CSRF 조합을 유지한다.
- 기존 에러 의미(예: 인증 실패 401, 내부망 차단 403, 검증 실패 400)를 바꾸지 않는다.
- 보안 헤더와 `X-Request-ID` 응답 헤더를 유지한다.

## 2) 공개 API 계약
### `GET /api/config`
- 상태코드: 200
- 응답 필드: `vworldKey`, `center`, `zoom`

### `GET /api/lands`
- 상태코드: 200 (잘못된 cursor는 400)
- 응답 형식: GeoJSON FeatureCollection
- 필드: `type`, `features`, `nextCursor`
- 페이지네이션 동작:
  - `limit`는 서버에서 최소/최대 범위로 보정
  - `nextCursor`가 `null`이면 마지막 페이지

### `POST /api/events`
- 상태코드:
  - 정상: 200 (`{"success": true}`)
  - 입력 오류: 400
  - 레이트리밋: 429 + `Retry-After` 헤더
- 지원 `eventType`: `search`, `land_click`

### `POST /api/web-events`
- 상태코드:
  - 정상: 200 (`{"success": true}`)
  - 입력 오류: 400
  - 레이트리밋: 429 + `Retry-After` 헤더
- 지원 `eventType`: `visit_start`, `heartbeat`, `visit_end`
- `pagePath`는 `/`만 허용

### `GET /api/public-download`
- 파일이 존재하면 파일 다운로드 응답(attachment)
- 메타/파일 부재 시 404 유지

## 3) 관리자/인증 계약
### 인증 경로
- `GET /admin/login`: 로그인 페이지 + CSRF 토큰 제공
- `POST /login`: 성공 시 `{"success": true}` / 실패 시 401 / 차단 시 429
- `POST /admin/login`: `/login` alias 동작 유지
- `POST /logout`: CSRF 검증 후 세션 정리 및 로그인 페이지로 리다이렉트

### 관리자 페이지/기능
- `GET /admin`: 미인증 시 `/admin/login`으로 303 redirect
- `POST /admin/upload`:
  - 인증/내부망/CSRF 실패 시 차단
  - 성공 시 업로드 결과 + geom job id 반환
- `POST /admin/public-download/upload`:
  - 허용 확장자/용량 검증 실패 시 400
  - 성공 시 파일 교체 성공 응답
- `GET /admin/public-download/meta`: 업로드 파일 메타 반환

### 관리자 통계/내보내기
- `GET /admin/stats`: 검색/클릭/상위 항목/추이
- `GET /admin/stats/web`: 방문 통계/체류시간 추이
- `GET /admin/raw-queries/export`: CSV 파일 응답
- 공통: 인증/내부망 조건 미충족 시 접근 불가

## 4) 보안/권한 불변
- 내부망 제한: `ALLOWED_IPS` 기준 유지
- 프록시 신뢰: `TRUST_PROXY_HEADERS`, `TRUSTED_PROXY_IPS` 정책 유지
- 세션 쿠키: `SESSION_HTTPS_ONLY`, `SameSite=lax`, `HttpOnly` 동작 유지
- CSRF 토큰:
  - 세션 저장/폼 제출 검증 경로 유지
  - 관리자 쓰기 작업에서 검증 필수

## 5) 운영/관측 불변
- `GET /health`: DB 확인 포함
- `GET /health?deep=1`: 외부 API(degraded/ok) 체크 유지
- 요청 로그:
  - `request_id`, `event`, `actor`, `ip`, `status`, `latency_ms` 필드 유지

## 6) 테스트 게이트 (리팩토링 PR 공통)
- `python -m compileall -q app tests` 통과
- `pytest -q` 통과
- 프런트 변경 포함 시 `cd frontend && npm run typecheck && npm run build` 통과
- 아래 대표 회귀 테스트는 유지:
  - 인증/접근제어
  - 업로드 플로우
  - 통계 API
  - 공개 다운로드 API
  - 레이트리밋 동작

## 7) 회귀 판정 규칙
- 아래 중 1개라도 발생하면 "동작 회귀"로 판정:
  - 상태코드 계약 변경(의도 없는 2xx/4xx/5xx 변화)
  - 필수 응답 필드 누락/이름 변경
  - 관리자 권한 우회 또는 과차단
  - 레이트리밋 헤더/동작 누락
  - 기존 테스트 실패(의도 없는 경우)
