# IdlePublicProperty 리팩토링 전략

## 1) 목표와 범위
본 문서는 현재 `IdlePublicProperty` 코드베이스를 기준으로 **보안(Security)**, **재사용성(Reusability)**, **유지보수성(Maintainability)** 관점의 리팩토링 전략을 정의한다. 최종 목표는 다음과 같다.

- 보안 사고 가능성을 낮추고 운영 안전성을 높인다.
- 기능 추가 시 중복 구현을 줄이고 개발 속도를 개선한다.
- 장애 대응/수정 비용을 낮추고 온보딩을 단순화한다.

---

## 2) 현재 상태 진단 (코드 기반)

### 2.1 Security 관점

#### 강점
- 세션 기반 인증이 적용되어 있고, 비밀번호 해시(`bcrypt`) 비교를 사용한다. (`auth.py`) 
- 로그인/업로드 요청에 CSRF 토큰 검증 로직이 존재한다. (`dependencies.py`, `auth.py`, `admin.py`)
- 보안 헤더(`X-Frame-Options`, `X-Content-Type-Options`, `CSP`)를 미들웨어에서 설정한다. (`main.py`)
- 관리자 경로 접근 시 내부망 IP prefix 제한이 적용된다. (`dependencies.py`)

#### 리스크
- `SessionMiddleware`가 `https_only=True`로 설정되어 있으나, `same_site`, `session cookie` 수명/재발급 정책 등 세부 통제가 명시적이지 않다. (`main.py`)
- 업로드 파일 검증이 확장자/Content-Type 중심이라 매직바이트 검사, 파일 크기 제한, 행 수 제한 등의 방어가 부족하다. (`admin.py`)
- 엑셀 파싱 시 값 정규화/검증 정책(주소 포맷, 연락처 포맷, 결측/비정상 수치 처리)이 느슨하다. (`admin.py`)
- 외부 API 호출(`requests.get`)에 timeout/retry/backoff 표준화가 없다. 장애 시 응답 지연/블로킹 가능성이 있다. (`utils.py`)
- `map_router`에서 전체 row를 그대로 반환하여 민감정보 최소화 원칙(need-to-know) 관점에서 개선 여지가 있다. (`map_router.py`)
- 예외 처리에서 `print` 기반 로그가 사용되고 구조화된 감사 로그가 없다. (`utils.py`)

### 2.2 Reusability 관점

#### 강점
- 라우터가 기능별(`auth`, `admin`, `map`)로 분리되어 초기 모듈 경계가 존재한다. (`app/routers/*`)
- 공통 의존성(인증, CSRF, 내부망 체크)이 별도 파일로 분리되어 있다. (`dependencies.py`)

#### 리스크
- DB 접근이 라우터/유틸에 산재되어 Repository 계층이 없다(직접 sqlite3 호출 반복). (`admin.py`, `map_router.py`, `utils.py`)
- 설정 객체와 전역 환경변수 접근이 혼재되어 일관성이 떨어진다. (`core/config.py` vs `utils.py`의 module-level `os.getenv`)
- 외부 API 연동 로직(브이월드)과 영속화 로직이 결합되어 단위 테스트/재사용이 어렵다. (`utils.py`)

### 2.3 Maintainability 관점

#### 강점
- 환경변수를 dataclass 기반 `Settings`로 관리하고 필수 값 누락 시 예외를 발생시킨다. (`core/config.py`)
- 기본 테스트 파일이 존재하며 접근 정책/스모크 테스트의 시작점이 있다. (`tests/*`)

#### 리스크
- 계층형 구조(routers/services/repositories/schemas)가 미완성이라 책임 분리가 약하다.
- Pydantic 응답 모델이 없어 API 계약이 문서/검증 레벨에서 약하다.
- 예외 처리 정책(HTTPException 매핑, 에러 코드 표준, 사용자 메시지)이 라우터별로 상이하다.
- 로깅, 메트릭, 트레이싱 부재로 운영 중 원인 분석이 어렵다.
- 테스트가 환경 의존적이고 E2E/통합/보안 테스트가 부족하다.

---

## 3) 개선 전략 (idle-land-map 적용 가능)

## 3.1 Security 개선 전략

### A. 인증/세션 강화
1. 세션 쿠키 정책 명시: `Secure`, `HttpOnly`, `SameSite=Lax/Strict`, session rotation(로그인 성공 시 재발급).
2. 로그인 시도 제한(rate limit) + 계정 잠금(짧은 cool-down).
3. 관리자 권한 체크를 Role 기반으로 확장(향후 운영자/조회자 분리 대비).

### B. 입력/파일/출력 검증 강화
1. 업로드 파일 크기, 최대 행 수, 허용 시트명/컬럼 스키마 고정.
2. 주소/면적/연락처의 정규화 함수 도입(`validators.py`), 실패 건은 사유와 함께 리포트.
3. 프론트로 내보내는 속성 화이트리스트 적용(필요 필드만 반환).

### C. 외부 연동 및 비밀 관리
1. `requests` timeout/retry/backoff/circuit-breaker 정책을 공통 HTTP 클라이언트로 통일.
2. `.env` 의존을 줄이고 운영 환경에서는 Secret Manager 또는 환경 주입만 허용.
3. SAST/Dependency scan(예: `pip-audit`, `bandit`)을 CI 파이프라인에 포함.

## 3.2 Reusability 개선 전략

### A. 계층 분리
- `routers`(입출력) → `services`(업무 로직) → `repositories`(DB)로 분리.
- 브이월드 연동은 `clients/vworld_client.py`로 추출해 다른 배치/서비스에서 재사용 가능하게 설계.

### B. 공통 모듈화
- 공통 DTO/Pydantic schema(`schemas/`) 도입.
- 입력 검증기(`validators/`), 예외 타입(`exceptions/`), 응답 포맷(`responses/`) 표준화.

### C. 계약 기반 개발
- OpenAPI 스키마를 기준으로 API 계약 고정.
- 프론트-백엔드 간 `config`, `lands` 응답의 버전 관리(`v1`, `v2`) 도입.

## 3.3 Maintainability 개선 전략

### A. 코드 품질 체계
1. `ruff + black + isort + mypy`를 pre-commit 및 CI에 적용.
2. 파일/함수별 복잡도 기준(cyclomatic complexity threshold) 설정.

### B. 테스트 피라미드 구축
1. 단위 테스트: validators, services, repositories mocking.
2. 통합 테스트: sqlite 임시 DB + TestClient.
3. 보안 회귀 테스트: CSRF 누락, 내부망 우회, 인증 실패 시나리오.
4. E2E 스모크: 로그인 → 업로드 → 지도 조회 흐름 자동화.

### C. 운영 가시성
1. 구조화 로깅(JSON) + 요청 ID(trace id) + 민감정보 마스킹.
2. 주요 메트릭: 로그인 실패율, 업로드 성공률, 지오메트리 생성 실패율, 외부 API latency.
3. 장애 대응 런북(runbook)과 배치 재시도 정책 문서화.

---

## 4) 실행 로드맵 (점진적)

### Phase 1 (1주): 분석/안전장치
- 코드 인벤토리, 데이터 흐름/위협 모델링(STRIDE-lite).
- 업로드 제한(파일 크기/행 수/스키마) 즉시 반영.
- 공통 예외/로깅 골격 도입.

### Phase 2 (2~3주): 보안 우선 리팩토링
- 세션/인증 강화, rate-limit, 감사 로그.
- 출력 필드 화이트리스트 적용.
- 외부 API 호출 공통 클라이언트화(timeout/retry).

### Phase 3 (3~4주): 재사용성/구조 개선
- 서비스/리포지토리/스키마 계층 분리.
- 브이월드 클라이언트 및 주소 정규화 모듈 재사용화.

### Phase 4 (1~2주): 테스트/검증
- 단위/통합/보안/E2E 테스트 확장.
- 커버리지 기준(예: 70%+) 합의 및 달성.

### Phase 5 (1주): 배포/모니터링
- 블루그린 또는 단계적 배포.
- 모니터링 알람 튜닝, 회고 및 개선 backlog 확정.

---

## 5) 성공 지표 (KPI)

### Security
- 취약점 스캔 High/Critical 건수 0.
- 무작위 업로드 오류/공격 시나리오 차단율 95%+.
- 관리자 인증 실패 로그의 탐지/알림 지연 5분 이내.

### Reusability
- 신규 기능에서 기존 서비스/컴포넌트 재사용 비율 40%+.
- 중복 코드(유사 로직) 30% 이상 감소.

### Maintainability
- 테스트 커버리지 70%+, 핵심 모듈 85%+.
- 평균 버그 수정 lead time 30% 단축.
- 신규 개발자 온보딩 기간 20% 단축.

---

## 6) 리스크와 대응
- **리팩토링 중 회귀 버그**: 기능 플래그, 단계 배포, 회귀 테스트 자동화.
- **과도한 추상화**: 도메인 반복 패턴이 확인된 모듈만 공통화.
- **일정 압박**: 보안 관련 변경 우선순위 최상위 유지, Nice-to-have 후순위.
- **외부 API 불안정**: 캐시/재시도/지수백오프 + 실패 시 폴백 데이터 정책.

---

## 7) 팀 역할 제안
- **Tech Lead**: 단계별 품질 게이트/우선순위 관리.
- **Security 담당**: 위협 모델링, 보안 테스트, 정책 검토.
- **Backend 담당**: 계층 분리, API/DB 리팩토링.
- **Frontend 담당**: API 계약 반영, 에러 UX 표준화.
- **QA 담당**: 회귀 자동화 및 릴리즈 검증.

---

## 8) 즉시 실행 가능한 체크리스트 (2주)
- [x] 업로드 파일 크기/행 수 제한 구현
- [x] V-World 호출 timeout/retry 공통화
- [x] `map_router` 응답 필드 화이트리스트 적용
- [x] 구조화 로깅 + 요청 ID 도입
- [ ] 보안 회귀 테스트 5개 추가(CSRF, 인증, 내부망, 파일검증, 권한)
- [ ] CI에 `ruff`, `black --check`, `pytest`, `pip-audit` 추가


## 9) Phase 1 실행 결과 (이번 변경)

- [x] 업로드 파일 크기 제한(`MAX_UPLOAD_SIZE_MB`, 기본 10MB) 적용
- [x] 업로드 최대 행 수 제한(`MAX_UPLOAD_ROWS`, 기본 5000행) 적용
- [x] 공통 로깅 골격(`logging_utils`) 및 Request ID 추적(`X-Request-ID`) 도입
- [x] 공통 예외 핸들러 골격(`exceptions`) 도입
- [ ] 위협 모델링(STRIDE-lite) 산출물 문서화


## 10) Phase 2 실행 결과 (이번 변경)

- [x] 로그인 시도 제한(실패 누적 기반 쿨다운) 적용
- [x] 로그인 성공 시 세션 초기화 후 재생성(session clear 후 user/csrf 재설정)
- [x] 지도 데이터 응답 속성 화이트리스트 적용(`contact`, `geom` 제외)
- [x] V-World API 호출 공통 클라이언트화(timeout/retry/backoff)
- [x] 인증 성공/실패/차단 감사 로그 추가(request-id 포함)


## 11) Phase 3 실행 트래커 (3~4주)

### 목표
- [ ] 라우터-서비스-리포지토리 계층 분리 완료
- [ ] 브이월드 연동과 주소/데이터 정규화 모듈 재사용화


## 12) Phase 4 설계 (1~2주): 테스트/검증

### 목적
- 핵심 기능의 회귀 방지와 보안/운영 리스크 감소를 위한 테스트 체계 확립
- 기능 확장 시 안정적인 배포를 보장하는 품질 게이트 정착

### 범위
- 단위 테스트: validators, services, repositories
- 통합 테스트: FastAPI ASGI 앱 + sqlite 테스트 DB
- 보안 회귀 테스트: CSRF, 내부망 제한, 인증 실패 처리
- E2E 스모크: 로그인 → 업로드 → 지도 조회

### 산출물
- 테스트 스위트 확장
  - `tests/test_validators.py`
  - `tests/test_services.py`
  - `tests/test_repositories.py`
  - `tests/test_security_regression.py`
  - `tests/test_e2e_smoke.py`
- 테스트 실행 가이드 및 실패 대응 문서
- 커버리지 리포트 기준 합의(예: 전체 70%+)

### 테스트 설계(요약)
- Validators
  - 필수 컬럼 누락 감지
  - 면적 파싱 실패/결측 처리
  - 에러 리포트 상한(MAX_ERROR_REPORT) 확인
- Services
  - 로그인 성공/실패/차단 흐름
  - 업로드 성공/실패/행 제한 검증
  - 지도 GeoJSON 반환 형식 확인
- Repositories
  - 삽입/삭제/조회/업데이트 경로
  - `geom` 누락 집계 정확성
- Security regression
  - CSRF 누락 시 403
  - 내부망 이외 접근 시 403
  - 인증 없이 업로드 시 401
- E2E smoke
  - 로그인 → 업로드 → `/api/lands`에 데이터 반영 확인

### 품질 게이트
- `python -m compileall -q app tests`
- `pytest -q`
- 커버리지 기준 충족 시 통과

### 리스크/대응
- 외부 API 의존 테스트 불안정
  - VWorld 호출은 테스트에서 mock 처리
- TestClient hang
  - `httpx.AsyncClient` + `ASGITransport` 사용 유지

### 완료 기준(DoD)
- 테스트 스위트 확장 항목 80% 이상 구현
- 보안 회귀 테스트 5개 이상 추가
- 스모크 테스트 1개 이상 자동화

### 작업 목록(체크리스트)
- [ ] 테스트 실행 환경 정리
- [ ] 테스트 전용 환경변수/헬퍼 추가(`tests/helpers.py`)
- [ ] sqlite 테스트 DB 생성/정리 유틸 추가
- [ ] httpx ASGI 테스트 클라이언트 공통 픽스처
- [ ] validators 단위 테스트 작성
- [ ] services 단위 테스트 작성
- [ ] repositories 단위 테스트 작성
- [ ] 보안 회귀 테스트 추가(최소 5개)
- [ ] E2E 스모크 테스트 추가(로그인→업로드→지도 조회)
- [ ] VWorld 호출 mock/fixture 추가
- [ ] 커버리지 기준 문서화 및 목표 수치 확정
- [ ] CI 명령어 정리(compileall, pytest, coverage)
- [ ] 기존 API 동작/응답 호환성 유지

### PR-1: Foundation and Contracts (Week 1)
- [x] `app/schemas/` 도입 (요청/응답 DTO 골격)
- [x] `app/db/connection.py` 도입 (공통 sqlite connection/context helper)
- [x] 기존 라우터 동작 변경 없음(무중단 스캐폴딩)
- [x] `python -m compileall -q app tests` 통과

Definition of Done:
- [x] 스키마/DB 헬퍼 모듈이 생성되어 import 가능
- [x] 기존 엔드포인트 기능 회귀 없음

### PR-2: Repository Extraction (Week 1~2)
- [x] `app/repositories/idle_land_repository.py` 추가
- [x] 라우터/유틸의 직접 SQL 로직을 리포지토리로 이동
- [x] 리포지토리 메서드 기준 트랜잭션 경계 정의
- [x] 라우터에서 raw SQL 제거

Definition of Done:
- [x] DB 접근 경로가 리포지토리로 일원화
- [x] 핵심 조회/저장 경로 테스트 통과

### PR-3: VWorld Client + Validators (Week 2)
- [x] `app/clients/vworld_client.py`로 브이월드 연동 이관
- [x] `app/validators/land_validators.py` 추가
- [x] 업로드 데이터 정규화/검증 실패 사유 표준화
- [x] 실패 항목 리포트 구조 정의

Definition of Done:
- [x] 브이월드 호출은 단일 클라이언트 경유
- [x] 업로드 검증 로직이 재사용 가능한 함수로 분리

### PR-4: Service Layer Introduction (Week 2~3)
- [x] `app/services/auth_service.py` 추가
- [x] `app/services/upload_service.py` 추가
- [x] `app/services/land_service.py` 추가
- [x] 라우터에서 비즈니스 로직 제거(서비스 호출만 유지)

Definition of Done:
- [x] 라우터는 입출력/상태코드 매핑 책임만 보유
- [x] 도메인 로직은 서비스 계층으로 이동 완료

### PR-5: Router Migration + Compatibility (Week 3)
- [x] `auth/admin/map_router`를 서비스 기반으로 전환
- [x] 기존 프론트와 응답 계약 호환성 유지
- [x] 필요 시 API 응답 버전 스캐폴딩(v1) 도입

Definition of Done:
- [x] 프론트엔드 수정 없이 주요 플로우 동작
- [x] 회귀 테스트/스모크 테스트 통과

### PR-6: Cleanup and Boundary Hardening (Week 3~4)
- [x] `app/utils.py`의 잔여 레거시 로직 정리
- [x] 중복/미사용 모듈 제거
- [x] 아키텍처/흐름 문서 업데이트

Definition of Done:
- [x] 레이어 경계 위반 import/호출 제거
- [x] 유지보수 문서 최신화

### 공통 품질 게이트 (각 PR마다)
- [x] `python -m compileall -q app tests`
- [x] `python -m pytest -q tests`
- [x] 라우터에 신규 raw SQL 추가 금지
- [x] 브이월드 직접 호출 위치 표준 준수(클라이언트 계층)
