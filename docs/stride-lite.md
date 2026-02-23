# STRIDE-lite 위협 모델

프로젝트: IdlePublicProperty  
작성일: 2026-02-11  
최종 수정일: 2026-02-22  
담당: Engineering

## 문서 진입점
- 문서 포털(한 페이지 허브): [`index.md`](index.md)
- 목표/범위: [`goals.md`](goals.md)
- 구조/흐름: [`architecture.md`](architecture.md)
- 엔지니어링 기준(Tech Stack/코딩 철학/스타일): [`engineering-guidelines.md`](engineering-guidelines.md)
- 운영/점검 절차: [`maintenance.md`](maintenance.md)

## 범위
- FastAPI 웹 애플리케이션
  - 공개 API: `/api/config`, `/api/lands`, `/api/events`, `/api/web-events`, `/api/public-download`, `/api/v1/*`
  - 관리자/인증 API: `/admin/login`, `/login`, `/admin/upload`, `/admin/public-download/*`, `/admin/stats*`, `/admin/raw-queries/export`
  - 헬스체크: `/health`
- SQLite 저장소 (`data/database.db`)
- 공개 다운로드 파일 저장소 (`data/public_download/current.*`, `current.json`)
- 외부 의존성: VWorld API (주소 지오코딩 + WFS)

## 자산
- 관리자 자격 증명 및 세션 쿠키
- 업로드된 엑셀 데이터(유휴 부지 목록)
- 지오메트리 및 파생 지도 데이터
- 공개 다운로드 배포 파일(`current.*`) 및 메타데이터
- 검색/클릭/웹 방문 이벤트 로그(`map_event_log`, `raw_query_log`, `web_visit_event`)
- VWorld WMTS 키
- VWorld Geocoder 키
- 애플리케이션 가용성과 무결성

## 신뢰 경계
- 공개 클라이언트 -> 애플리케이션 (비인증 요청)
- 내부/관리자 네트워크 -> 애플리케이션 (관리자 엔드포인트)
- 애플리케이션 -> SQLite DB
- 애플리케이션 -> 파일 시스템(public download 저장소)
- 애플리케이션 -> VWorld API

## 데이터 흐름(상위 수준)
1. 공개 사용자 -> `/api/config`, `/api/lands` -> SQLite 조회 -> JSON/GeoJSON 응답
2. 공개 사용자 -> `/api/public-download` -> 파일 시스템 조회 -> 파일 다운로드 응답
3. 공개 사용자 -> `/api/events`, `/api/web-events` -> 이벤트 로그 테이블 저장
4. 관리자 사용자 -> `/admin/login` -> 세션 + CSRF 토큰 발급
5. 관리자 사용자 -> `/login` -> 인증 + 레이트 리미팅 -> 세션 생성
6. 관리자 사용자 -> `/admin/upload` -> 엑셀 파싱 + 검증 -> SQLite 저장 -> 백그라운드 지오메트리 업데이트
7. 관리자 사용자 -> `/admin/public-download/upload` -> 파일 검증/원자적 교체 -> 메타 갱신
8. 관리자 사용자 -> `/admin/stats`, `/admin/stats/web` -> 집계 조회
9. 관리자 사용자 -> `/admin/raw-queries/export` -> 원시 로그 CSV 내보내기

## 가정
- 관리자 엔드포인트는 허용된 내부 IP 범위에서만 접근한다.
- 세션 미들웨어 시크릿은 충분히 강하며 비공개다.
- SQLite DB 파일과 공개 다운로드 디렉터리는 OS 권한으로 보호된다.
- VWorld API는 정상적으로 가용하며 올바른 응답을 반환한다.

## 현재 통제 vs 운영 의존 항목
| 항목 | 현재 통제 | 운영 의존/잔여 위험 |
|---|---|---|
| 관리자 보호 | 내부망 제한 + 세션 인증 적용, 상태 변경 관리자 요청에 CSRF 적용 | 프록시 신뢰 설정 오구성 시 우회 위험 |
| 로그인 시도 제한 | 인메모리 제한 적용 | 멀티 인스턴스 환경에서 상태 비공유 |
| 이벤트 수집 과다 요청 | `/api/events`(60/min), `/api/web-events`(120/min) 제한 | 분산 환경에서 전역 limit 부재 |
| 공개 다운로드 갱신 | 확장자/용량 검증 + 원자적 교체 | 파일 무결성(해시/서명) 운영 절차 미정 |
| 원시 로그 반출 | 관리자 경로 보호 | 반출 이후 2차 유출 통제는 운영 정책 의존 |

## STRIDE-lite 분석

### S: 스푸핑(Spoofing)
- 위험: 관리자 세션 쿠키 위조.
  - 현재: `SessionMiddleware`를 통한 서명된 세션 쿠키.
  - 공백: `SESSION_HTTPS_ONLY=false` 환경에서 세션 보호수준 저하 가능.
  - 완화: 운영 환경에서 HTTPS 강제 및 시크릿 로테이션.
- 위험: 내부망 체크 우회(IP 위조).
  - 현재: `ALLOWED_IPS` CIDR 허용 목록, 신뢰 프록시 설정 기반 IP 해석.
  - 공백: 프록시 구성 오류 시 우회 가능성.
  - 완화: `TRUST_PROXY_HEADERS`, `TRUSTED_PROXY_IPS` 운영 점검 자동화.

### T: 변조(Tampering)
- 위험: 악성 엑셀 업로드로 DB 내용 변조.
  - 현재: CSRF, 내부망, 파일형식/용량/행수 검증.
  - 공백: 데이터 의미 검증은 앱 로직 중심, DB 제약은 제한적.
  - 완화: 핵심 컬럼 제약 강화 및 업로드 검증 케이스 보강.
- 위험: 공개 다운로드 파일/메타 변조.
  - 현재: 관리자 인증 + 허용 확장자/용량 검증 + 원자적 교체.
  - 공백: 파일 무결성 점검 프로세스 부재.
  - 완화: 해시 기록 또는 배포 파일 무결성 점검 절차 추가.

### R: 부인(Repudiation)
- 위험: 관리자 설정 변경/내보내기 행위 추적 부족.
  - 현재: 구조화 로그 기록.
  - 공백: 영속 감사 로그 체계(누가 언제 무엇을 내보냈는지) 제한적.
  - 완화: 관리자 액션 감사 로그 항목 확장.

### I: 정보 노출(Information Disclosure)
- 위험: 공개용 WMTS 키(`VWORLD_WMTS_KEY`) 오남용(도메인/용도 제한 미흡, 비정상 사용량 급증).
  - 현재: 지도 렌더링 필요에 따라 `/api/config`에서 예외적으로 공개 제공.
  - 완화: 공개 제한 키 정책(도메인/용도 제한) 및 사용량 모니터링.
- 위험: `/admin/raw-queries/export`로 원시 검색 입력 노출.
  - 현재: 관리자 인증/내부망 보호.
  - 공백: CSV 재배포 시 2차 노출 위험.
  - 완화: 내보내기 접근 통제 강화, 보존 기간/마스킹 정책 수립.

### D: 서비스 거부(Denial of Service)
- 위험: 대용량 업로드/이벤트 과다 입력.
  - 현재: 업로드 용량/행 제한 + 이벤트 수집 API 레이트리밋 적용.
  - 공백: 인메모리 구현으로 멀티 인스턴스 전역 제한은 제공하지 않음.
  - 완화: 공유 스토어 기반 글로벌 레이트리밋 또는 게이트웨이 정책 검토.
- 위험: 반복 로그인 시도.
  - 현재: 인메모리 레이트 리미터.
  - 공백: 다중 인스턴스에서 무력화 가능.
  - 완화: 공유 스토어 기반 리미터로 확장.
- 위험: VWorld API 지연으로 백그라운드 작업 지연.
  - 현재: 타임아웃/재시도/백오프.
  - 완화: 작업 시간 상한/지연 경보 도입.

### E: 권한 상승(Elevation of Privilege)
- 위험: `/admin/upload`, `/admin/public-download/upload`, `/admin/raw-queries/export` 우회 접근.
  - 현재: 내부 IP + 세션 인증 조합, 상태 변경 관리자 요청에 CSRF 적용.
  - 공백: 세션 탈취 시 관리자 기능 전면 노출.
  - 완화: 세션 만료/재인증 정책 강화, 관리자 액션 모니터링.

## 잔여 위험
- 프록시 설정 오류 시 내부 IP 검사 우회 가능.
- 인메모리 레이트 리미팅은 수평 확장 환경에서 약함.
- 원시 로그 내보내기 데이터의 2차 유출 위험은 운영 통제에 의존.
- 공개 다운로드 파일 배포 프로세스의 무결성 검증 체계가 약함.

## 권장 후속 조치
1. 이벤트 수집 API 및 로그인에 대한 공통 rate limit 정책 수립.
2. 관리자 액션(업로드, 설정변경, 내보내기) 감사 로그 강화.
3. 공개 다운로드 파일 무결성 체크(해시/서명 또는 점검 절차) 도입.
4. raw query export 데이터 보존/마스킹/반출 정책 수립.
5. 프록시 신뢰 모델 운영 점검 자동화.

## 구현 규칙 참조
- 보안 관련 코딩 규칙은 [`engineering-guidelines.md`](engineering-guidelines.md)의 Security 섹션을 기준으로 유지한다.
