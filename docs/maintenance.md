# 유지보수 가이드

프로젝트: IdlePublicProperty  
작성일: 2026-02-11

## 목적
운영 중인 서비스의 안정성과 보안을 유지하기 위해 필요한 점검, 변경, 장애 대응 절차를 정의한다.

## 환경 변수
필수:
- `VWORLD_KEY`
- `ADMIN_ID`
- `ADMIN_PW_HASH`
- `SECRET_KEY`

선택:
- `ALLOWED_IPS`
- `MAX_UPLOAD_SIZE_MB`
- `MAX_UPLOAD_ROWS`
- `LOGIN_MAX_ATTEMPTS`
- `LOGIN_COOLDOWN_SECONDS`
- `VWORLD_TIMEOUT_S`
- `VWORLD_RETRIES`
- `VWORLD_BACKOFF_S`
- `SESSION_HTTPS_ONLY`

## 주기적 점검
- VWorld API 키 유효성 확인
- 관리자 계정 비밀번호 해시 갱신
- 업로드 템플릿 변경 여부 확인(컬럼 스펙)
- DB 파일 권한 및 백업 상태 점검
- 로그 용량 및 저장 기간 점검

## 배포 전 체크리스트
1. `python -m compileall -q app tests`
2. `pytest -q`
3. 환경 변수 설정 확인
4. `data/database.db` 파일 권한 확인
5. `/api/config` 및 `/api/lands` 응답 정상 확인

## CI/테스트 명령
- `python -m compileall -q app tests`
- `pytest -q`
- `coverage run -m pytest`
- `coverage report -m`

### 선택 실행
- HTTP E2E 스모크: `RUN_HTTP_E2E=1 pytest -q tests/test_e2e_smoke.py`

## 장애 대응
### 로그인 실패/차단 급증
- `LOGIN_MAX_ATTEMPTS`, `LOGIN_COOLDOWN_SECONDS` 점검
- 내부 IP 허용 목록(`ALLOWED_IPS`) 확인
- 프록시 환경일 경우 클라이언트 IP 인식 방식 검토

### 업로드 실패
- 파일 타입 및 크기 제한 확인
- 업로드 컬럼명 스펙 확인
- `MAX_UPLOAD_ROWS` 제한 확인
- VWorld API 호출 상태 확인

### 지도 데이터 미표시
- `/api/lands` 응답 확인
- DB `idle_land.geom` 컬럼 상태 확인
- VWorld API 호출 로그 확인

## 백업/복구
- `data/database.db` 파일을 주기적으로 백업
- 복구 시 파일 권한 및 경로 확인

## 로그
- 요청 ID가 포함된 로그를 사용하여 장애 추적
- 관리자 업로드/로그인 로그가 정상적으로 기록되는지 확인

## 보안 운영
- 세션 시크릿(SECRET_KEY) 정기 교체
- 공개 데이터 필드 재검토
- 내부망 접근 정책 주기 점검

## 코드 변경 가이드
- 라우터에는 비즈니스 로직을 추가하지 않는다.
- DB 접근은 리포지토리 계층을 통해서만 수행한다.
- 외부 API 호출은 클라이언트 계층에만 구현한다.
