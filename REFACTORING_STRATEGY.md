# IdlePublicProperty 리팩토링 전략 (보안·재사용성·유지보수성)

## 1) 목적과 접근 방식
본 문서는 제공된 개선안(Idle Land Map 개선 계획)을 바탕으로, 현재 `IdlePublicProperty` 코드베이스(`FastAPI + SQLite + Vanilla JS`)를 정적 분석하여 **실행 가능한 리팩토링 로드맵**으로 구체화한 전략이다.

핵심 목표:
1. **보안 강화**: 인증·권한·입력검증·비밀정보 관리 체계화
2. **재사용성 개선**: 라우터/서비스/저장소 계층 분리와 공통 모듈화
3. **유지보수성 향상**: 구조 개선, 테스트 자동화, 운영관측성(로깅) 확보

---

## 2) 현재 상태 요약 (코드 기반 진단)

### 2.1 보안
- 인증은 세션 기반(`SessionMiddleware`)이며, 로그인 시 bcrypt 해시 검증 사용 (`app/routers/auth.py`).
- 다만 다음 리스크가 존재:
  - 기본 시크릿 키 fallback (`app/main.py`의 `"your-secret-key"`) 존재
  - `/login` POST에 내부망 제한 미적용 (GET `/admin/login`만 내부망 제한)
  - CSRF 보호 부재 (로그인/엑셀 업로드 모두 토큰 검증 없음)
  - API 에러 메시지에 원문 예외 노출 (`str(e)`) 가능 (`app/routers/admin.py`)
  - 프런트에서 `innerHTML`로 DB 값 렌더링 (`static/js/map.js`) → 저장형 XSS 가능성

### 2.2 재사용성
- 현재 라우터에서 DB 접근/비즈니스 로직/외부 API 호출이 결합됨:
  - `admin.py`에서 엑셀 파싱 + DB 저장 + 백그라운드 작업 트리거
  - `utils.py`에서 DB 초기화 + 외부 API 호출 + 재시도 로직 혼재
- 설정/타입 경계가 약함:
  - `Config`는 환경변수 타입 변환·검증이 제한적
  - DB 경로/환경 접근이 모듈별로 분산

### 2.3 유지보수성
- 테스트 코드 및 lint/format 체계가 사실상 부재
- 예외 처리 정책이 일관되지 않고, 구조화된 로깅이 없음
- `static/js/map.js` 단일 파일에 지도 초기화/필터링/UI/팝업 로직이 집중되어 복잡도 증가

---

## 3) 목표 아키텍처

### 3.1 백엔드 계층화
- `app/routers/*`: 요청/응답·검증만 담당
- `app/services/*`: 도메인 로직 (인증, 엑셀 ingest, 지도 데이터 조합)
- `app/repositories/*`: SQLite 접근 전담
- `app/clients/vworld.py`: 외부 API 호출 추상화
- `app/core/config.py`: 환경변수 로딩/검증(Pydantic Settings)

### 3.2 프런트엔드 모듈화
- `static/js/map.js` 분리:
  - `map-init.js` (지도 생성/레이어)
  - `land-filter.js` (필터/검색)
  - `land-render.js` (목록/팝업 렌더링, XSS-safe)
  - `api-client.js` (`/api/config`, `/api/lands` 호출)

### 3.3 운영 기본기
- 구조화 로깅(JSON 또는 key-value)
- 공통 예외 핸들러 + 사용자 친화 메시지
- 검증 실패/권한 실패/외부 API 실패를 구분한 에러 코드 체계

---

## 4) 단계별 실행 계획

## Phase 1. 분석·기반 정비 (1주)
1. 환경변수 표준화
   - 필수값: `SECRET_KEY`, `ADMIN_ID`, `ADMIN_PW_HASH`, `VWORLD_KEY`
   - 숫자형: 지도 center/zoom 타입 검증
2. 코드 규칙 도입
   - Python: Ruff/Black, JS: ESLint/Prettier
3. 최소 테스트 골격 추가
   - FastAPI TestClient 기반 smoke test

**산출물**: `core/config.py`, CI lint 파이프라인, 기본 테스트 실행 가능 상태

## Phase 2. 보안 개선 (2~3주)
1. 인증·권한
   - `/login` POST에도 내부망 제한 적용 (또는 reverse proxy ACL과 일관화)
   - 세션 쿠키 보안 속성 명시 (`secure`, `httponly`, `samesite`)
2. CSRF 방어
   - 로그인/업로드 엔드포인트에 CSRF 토큰 도입
3. 입력·출력 보안
   - 업로드 파일 확장자/콘텐츠타입/컬럼 스키마 검증
   - 프런트 `innerHTML` 제거, 텍스트 노드 렌더링으로 변경
4. 비밀정보 관리
   - 기본 시크릿 fallback 제거, 누락 시 부팅 실패

**성공 기준**: 주요 취약점(XSS/CSRF/비밀정보 오구성) 제거, 보안 점검 체크리스트 통과

## Phase 3. 재사용성·구조 리팩토링 (3~4주)
1. DB 접근 분리
   - `idle_land` CRUD를 Repository로 이동
2. 엑셀 ingest 서비스화
   - 업로드/파싱/검증/저장을 `LandImportService`로 분리
3. VWorld 클라이언트 분리
   - 요청 재시도/타임아웃/예외 변환 통합
4. 프런트 모듈화
   - 지도/필터/UI 렌더링 파일 분리

**성공 기준**: 라우터 코드량 축소, 로직 재사용 지점 확대, 기능 추가 시 변경 파일 수 감소

## Phase 4. 테스트·검증 (1~2주)
1. 백엔드 단위 테스트
   - 인증 성공/실패, 권한 차단, 업로드 검증 실패 케이스
2. 통합 테스트
   - `/admin/upload` 후 백그라운드 갱신 플로우 검증
3. 프런트 핵심 로직 테스트
   - 필터 조건 조합, DOM 렌더링 안전성

**성공 기준**: 핵심 경로 커버리지 확보(우선 60%→점진 상향)

## Phase 5. 배포·운영 (1주)
1. 관측성
   - 요청 ID, 에러 등급, 외부 API 지연시간 로깅
2. 운영 문서화
   - 장애 대응 가이드, 환경변수 가이드, 업로드 템플릿 규약

---

## 5) 파일/모듈 단위 우선 리팩토링 대상

1. `app/main.py`
- 설정/미들웨어/라우터 등록 책임 분리
- `create_app()` 팩토리 패턴 전환

2. `app/routers/admin.py`
- 업로드 처리에서 파싱/검증/저장/응답 분리
- 예외 원문 노출 금지

3. `app/utils.py`
- DB 초기화와 VWorld API 로직 분리
- 네트워크 타임아웃·재시도 정책 명시

4. `static/js/map.js`
- `innerHTML` 기반 렌더링 제거
- 필터/지도/리스트 모듈 분리

5. `app/dependencies.py`, `app/routers/auth.py`
- 인증/내부망 정책 일관화
- 로그인 라우트 보호 정책 재정의

---

## 6) KPI (측정 지표)

### 보안
- 정적 점검에서 High 취약점 0건
- 기본 시크릿/누락 환경변수 허용 0건
- CSRF/XSS 회귀 테스트 통과율 100%

### 재사용성
- 라우터에서 서비스 호출 비율 증가 (직접 SQL 감소)
- 중복 로직(환경 접근/DB경로/응답 포맷) 제거율

### 유지보수성
- 테스트 커버리지 단계적 상향
- 파일당 평균 복잡도 감소
- 신규 기능 개발 시 리드타임 단축

---

## 7) 리스크와 대응
- 리팩토링 중 동작 회귀 위험
  - 대응: 기능 플래그, 단계적 배포, 회귀 테스트 우선 구축
- 과도한 추상화 위험
  - 대응: 실제 중복/변경 빈도 높은 영역부터 분리
- 일정 지연 위험
  - 대응: 보안 우선순위(인증/입력검증/XSS) 먼저 완료 후 구조개선 확장

---

## 8) 팀 역할 제안
- Project Lead: 우선순위/릴리즈 관리
- Security 담당: 인증/CSRF/XSS/비밀정보 정책
- Backend 담당: 서비스·저장소 분리, 테스트
- Frontend 담당: 렌더링 안전화, 모듈화
- QA 담당: 회귀/보안 시나리오 자동화

---

## 9) 즉시 실행 가능한 2주 액션 아이템
1. `SECRET_KEY` 기본값 제거 및 필수화
2. `/login` POST 내부망 제한 정책 확정·적용
3. 업로드 API 파일/스키마 검증 추가
4. `map.js`의 `innerHTML` 제거(목록/팝업)
5. 에러 응답 표준화(사용자 메시지 + 서버 로그 분리)
6. 인증/업로드 경로 테스트 최소셋 작성