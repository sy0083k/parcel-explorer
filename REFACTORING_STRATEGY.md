# IdlePublicProperty 리팩토링 전략

## 1. Introduction / Objective
본 전략 문서는 제공된 개선안(보안·재사용성·유지보수성 중심)을 기준으로 `IdlePublicProperty` 코드베이스를 실제 구조에 맞게 리팩토링하기 위한 실행 계획이다. 현재 프로젝트는 FastAPI + SQLite + Vanilla JS(OpenLayers)로 구성되어 있으며, 단기적으로는 **보안 리스크 완화**, 중기적으로는 **계층 분리 기반 재사용성 확보**, 장기적으로는 **테스트/운영 체계 내재화**를 목표로 한다.

핵심 목표:
- **Security**: 인증/권한, 입력 검증, XSS/CSRF 완화, 비밀정보 관리 강화
- **Reusability**: Router 중심 구조를 Service/Repository/Client로 분리
- **Maintainability**: 코드 규칙, 테스트, 에러/로깅 표준화로 변경 비용 절감

---

## 2. Current State Analysis (IdlePublicProperty)

### 2.1 Security aspects
현재 상태 요약:
- 세션 기반 인증을 사용하며, 로그인 검증은 bcrypt 해시를 활용한다.
- `SessionMiddleware`와 보안 헤더(CSP, X-Frame-Options 등)를 설정했다.
- 관리자 엔드포인트에 내부망 접근 제한 의존 구조가 있다.

주요 개선 필요 지점:
1. **환경변수/시크릿 관리**
   - 운영 민감값(`SECRET_KEY`, 관리자 계정/비밀번호 해시, API 키) 누락/약한 값에 대한 강제 정책이 필요하다.
2. **입력 검증**
   - 업로드 파일의 확장자/콘텐츠 타입/컬럼 스키마 검증을 현재보다 엄격히 적용해야 한다.
3. **XSS 가능성**
   - 프런트 렌더링에서 `innerHTML` 기반 출력이 남아 있으면 저장형 XSS 위험이 존재한다.
4. **CSRF 통제 부재**
   - 로그인/업로드 POST 흐름에서 CSRF 토큰 검증을 도입할 필요가 있다.
5. **오류 노출 최소화**
   - API 응답에서 내부 예외 문자열을 직접 노출하지 않고, 사용자 메시지와 서버 로그를 분리해야 한다.

### 2.2 Reusability aspects
현재 상태 요약:
- 라우터에 비즈니스 로직과 데이터 접근 코드가 혼재되어 있다.
- 엑셀 파싱/저장/백그라운드 갱신 로직이 단일 경로에 결합되어 재사용이 어렵다.
- 외부 API(VWorld) 호출 로직과 재시도 정책이 유틸리티 계층에 섞여 있다.

개선 필요 지점:
1. **책임 분리 미흡**: Router ↔ Service ↔ Repository 경계 수립 필요
2. **공통 인터페이스 부재**: 데이터 접근/외부 API 호출 규격화 필요
3. **프런트 단일 대형 파일**: 지도 초기화/필터/렌더링/요청 로직 분할 필요

### 2.3 Maintainability aspects
현재 상태 요약:
- 테스트는 최소 수준이며, 핵심 흐름(인증/업로드/지도 데이터 제공) 기준 커버리지가 부족하다.
- 일관된 코드 품질 체계(lint/format/type-check)가 약하다.
- 구조화 로깅, 오류 코드 체계, 운영 문서(런북) 보강 여지가 크다.

개선 필요 지점:
1. **테스트 전략**: 단위/통합/회귀 테스트 계층화
2. **코딩 표준화**: Ruff/Black, ESLint/Prettier 도입
3. **디버깅 용이성**: 요청 ID, 오류 등급, 외부 API 지연 로그 표준화

---

## 3. Proposed Improvements for IdlePublicProperty

### 3.1 Security Enhancements
1. **인증/권한 체계 강화**
   - 세션 기반 인증 정책 유지 + 관리자 권한 검사 일원화
   - 로그인 POST 포함 전체 인증 경로에 일관된 접근 제어 적용
2. **입력 데이터 검증 강화**
   - 업로드 파일 확장자/MIME/크기 제한
   - 필수 컬럼 스키마 검증(`주소`, `면적`, `지목`, `문의`) 및 타입 검사
3. **비밀정보 보호**
   - `.env` 필수값 누락 시 부팅 실패(fail fast)
   - 개발/운영 설정 분리 및 시크릿 로테이션 절차 문서화
4. **출력 보안/XSS 방어**
   - 프런트 `innerHTML` 제거, 안전한 DOM API(`textContent`) 사용
   - CSP 정책을 현재 사용 CDN/지도 API에 맞춰 최소 권한 원칙으로 재정비
5. **정기 점검**
   - 의존성 취약점 스캔 + 보안 점검 체크리스트를 릴리즈 게이트에 포함

### 3.2 Reusability Improvements
1. **백엔드 모듈 분리**
   - `routers`: 요청/응답/검증
   - `services`: 도메인 로직(인증, 업로드, 데이터 조합)
   - `repositories`: SQLite CRUD
   - `clients`: VWorld API 래퍼(타임아웃/재시도/예외 변환)
2. **공통 인터페이스 정의**
   - 서비스 입력/출력 DTO(또는 Pydantic 모델)로 API 계약 고정
   - 데이터 접근 함수 시그니처 표준화
3. **프런트 모듈화**
   - `map.js` 분리: map-init / filter / render / api-client
   - 렌더링 함수 재사용 가능 단위로 분해
4. **공용 유틸리티 패키지화**
   - 설정 로더, 로깅 유틸, 에러 매퍼를 공통 모듈로 구성

### 3.3 Maintainability Improvements
1. **코딩 규칙/품질 게이트**
   - Python: Ruff + Black
   - JS: ESLint + Prettier
   - CI에서 lint/test 실패 시 merge 차단
2. **문서화 보강**
   - 모듈별 책임과 호출 흐름 문서
   - 운영/장애 대응/배포 체크리스트 문서
3. **테스트 확장**
   - 단위 테스트: 인증, 권한, 업로드 검증
   - 통합 테스트: 업로드→저장→지도 반영 흐름
   - 회귀 테스트: XSS/CSRF/권한 우회 시나리오
4. **오류/로그 표준화**
   - 사용자 메시지와 내부 에러 분리
   - 구조화 로그 + 요청 추적 ID 도입

---

## 4. Success Metrics

### Security
- High/Critical 취약점 0건
- 시크릿 미설정/약한 설정 허용 0건
- CSRF/XSS 회귀 테스트 통과율 100%

### Reusability
- 라우터 내 직접 DB 접근 비율 지속 감소
- 공통 서비스/렌더링 모듈 재사용률 증가
- 신규 기능 개발 시 중복 코드 발생률 감소

### Maintainability
- 핵심 경로 테스트 커버리지 60% 이상(초기 목표)
- 평균 모듈 복잡도(순환 복잡도) 감소
- 신규 개발자 온보딩 시간 단축

---

## 5. Risks and Mitigation
1. **리팩토링 중 기능 회귀**
   - 대응: 기능 단위 점진 배포, 회귀 테스트 선행, 코드리뷰 강화
2. **과도한 추상화**
   - 대응: 변경 빈도가 높은 영역부터 분리, 불필요한 계층 추가 금지
3. **일정 지연**
   - 대응: 보안 이슈 우선순위(인증/입력검증/XSS) 고정, 범위 관리

---

## 6. Dependencies
- IdlePublicProperty 소스 접근 및 실행 환경
- 보안/백엔드/프런트/QA 역할의 최소 인력 확보
- 코딩 표준/아키텍처 결정에 대한 팀 합의
- 배포 파이프라인(CI) 수정 권한

---

## 7. Timeline (High-level)
- **Phase 1 (1주)**: 분석/품질 도구/기본 테스트 세팅
- **Phase 2 (2~3주)**: 인증·입력검증·XSS/CSRF 중심 보안 개선
- **Phase 3 (3~4주)**: 서비스·저장소 분리, 프런트 모듈화
- **Phase 4 (1~2주)**: 통합 테스트·회귀 검증·성능/안정성 확인
- **Phase 5 (1주)**: 배포, 모니터링, 운영 문서 확정

---

## 8. Team Roles & Responsibilities
- **Project Lead**: 우선순위 관리, 일정/리스크 관리, 대외 커뮤니케이션
- **Security Specialist**: 인증/권한/CSRF/XSS/시크릿 정책 설계 및 점검
- **Backend Developer**: 서비스·저장소·클라이언트 계층 리팩토링 및 테스트
- **Frontend Developer**: 지도 UI 모듈화, 안전 렌더링, 사용자 경험 개선
- **QA Engineer**: 테스트 시나리오 설계, 자동화, 릴리즈 품질 게이트 운영

---

## 9. Immediate 2-week Action Items
1. `SECRET_KEY` 필수화 및 약한 기본값 제거
2. 로그인/업로드 POST 경로 접근 정책 재점검 및 일원화
3. 업로드 파일/스키마 검증 로직 강화
4. `map.js`의 `innerHTML` 제거 및 안전 렌더링 적용
5. 표준 에러 응답 포맷 + 구조화 로깅 도입
6. 인증/업로드/권한 차단 최소 회귀 테스트 세트 구축
