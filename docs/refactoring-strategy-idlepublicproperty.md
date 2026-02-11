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
- [ ] V-World 호출 timeout/retry 공통화
- [ ] `map_router` 응답 필드 화이트리스트 적용
- [x] 구조화 로깅 + 요청 ID 도입
- [ ] 보안 회귀 테스트 5개 추가(CSRF, 인증, 내부망, 파일검증, 권한)
- [ ] CI에 `ruff`, `black --check`, `pytest`, `pip-audit` 추가


## 9) Phase 1 실행 결과 (이번 변경)

- [x] 업로드 파일 크기 제한(`MAX_UPLOAD_SIZE_MB`, 기본 10MB) 적용
- [x] 업로드 최대 행 수 제한(`MAX_UPLOAD_ROWS`, 기본 5000행) 적용
- [x] 공통 로깅 골격(`logging_utils`) 및 Request ID 추적(`X-Request-ID`) 도입
- [x] 공통 예외 핸들러 골격(`exceptions`) 도입
- [ ] 위협 모델링(STRIDE-lite) 산출물 문서화

