# 🏠 관심 필지 지도 (Parcel Explorer)

브이월드(VWorld) API와 FastAPI 기반으로 관심 필지를 지도에 시각화하고,  
관리자가 엑셀 업로드로 데이터를 갱신할 수 있는 웹 애플리케이션입니다.

## 📌 활용 사례
- 충청남도 서산시: 유휴 공유재산 지도
  
## 🛠 핵심 기술 스택
- Backend: Python 3.12, FastAPI, SQLite
- Frontend: TypeScript, Vite, OpenLayers
- Data: pandas, openpyxl/xlrd
- External API: VWorld (WMTS/Geocoder/WFS)

세부 구현 원칙은 `docs/engineering-guidelines.md`를 기준으로 합니다.

## 🚀 빠른 시작

### 1) 사전 준비
- Python 3.12
- Node.js + npm (frontend 빌드용)
- VWorld API 키 (WMTS, Geocoder)

### 2) 환경 변수 설정
`.env.example`을 복사해 `.env`를 생성합니다.

```bash
cp .env.example .env
```

`.env`는 `KEY=value` 형식(등호 주변 공백 없음)으로 작성하세요. 값에 공백이 포함되면 따옴표를 사용하세요.
예: `APP_NAME="관심 필지 지도 (Parcel Explorer)"`, `SESSION_HTTPS_ONLY=false`

필수 환경 변수:
- `VWORLD_WMTS_KEY`
- `VWORLD_GEOCODER_KEY`
- `ADMIN_ID`
- `ADMIN_PW_HASH`
- `SECRET_KEY`

`ADMIN_PW_HASH`는 bcrypt 해시여야 하며, 아래 명령으로 생성할 수 있습니다.

```bash
python create_hash.py
```

선택 환경 변수(요약):
- `ALLOWED_IPS`, `SESSION_HTTPS_ONLY`
- `SESSION_COOKIE_NAME`, `SESSION_NAMESPACE`
- `MAX_UPLOAD_SIZE_MB`, `MAX_UPLOAD_ROWS`
- `LOGIN_MAX_ATTEMPTS`, `LOGIN_COOLDOWN_SECONDS`
- `VWORLD_TIMEOUT_S`, `VWORLD_RETRIES`, `VWORLD_BACKOFF_S`
- `TRUST_PROXY_HEADERS`, `TRUSTED_PROXY_IPS`
- `UPLOAD_SHEET_NAME`, `ALLOWED_WEB_TRACK_PATHS`
- `PUBLIC_DOWNLOAD_MAX_SIZE_MB`, `PUBLIC_DOWNLOAD_RATE_LIMIT_PER_MINUTE`, `PUBLIC_DOWNLOAD_ALLOWED_EXTS`, `PUBLIC_DOWNLOAD_DIR`

### 3) 의존성 설치
```bash
pip install -r requirements.txt
cd frontend
npm ci
cd ..
```

### 4) 프런트 빌드
```bash
cd frontend
npm run build
cd ..
```

### 5) 서버 실행
```bash
uvicorn app.main:app --reload
```

기본 접속 URL:
- 메인: `http://127.0.0.1:8000/`
- 관리자 로그인: `http://127.0.0.1:8000/admin/login`

## 🔐 관리자 사용 흐름
1. `/admin/login`에서 로그인
2. `/admin`에서 엑셀 업로드 (`/admin/upload`)
3. 업로드 후 지오메트리 보강 작업이 백그라운드로 실행됨
4. 공개 다운로드 파일은 `/admin/public-download/upload`로 갱신 가능
5. 통계 탭에서 `전체 필지 수/경계선 없음 필지 수` 확인 및 경계선 재수집 실행 가능

## 📱 모바일 화면 흐름
- 초기 화면: 지도 중심 화면 + 우하단 검색(돋보기) 버튼
- 검색 화면: 돋보기 버튼 클릭 시 전체화면 검색 입력 오버레이 + `조건에 맞는 토지 찾기`/`검색 조건 초기화`/`전체 목록 다운로드` 버튼 제공
- 결과 화면: 검색 실행 후 화면 하단 기본 25% 결과 패널 + 지도 연동 (핸들 드래그로 높이 조절 가능)
- 뒤로가기: 결과 → 검색 → 초기 화면 순으로 단계 복귀

## 🧭 API 개요

### 공개 API (`/api`)
- `GET /api/config`
- `GET /api/lands`
- `POST /api/events`
- `POST /api/web-events`
- `GET /api/public-download`

### 버전 경로 (`/api/v1`)
- `/api/v1/*`는 현재 **유지 중인 호환성(alias) 경로**입니다.
- `/api/v1/*`는 `/api/*`와 동일한 요청/응답 계약(필드 의미, 상태코드, 레이트리밋)을 제공합니다.
- 신규 기능/변경은 `/api/*`를 기준으로 적용하며 `/api/v1/*` 동등성을 유지합니다.
- 향후 폐기 시 사전 공지 + Deprecation/Sunset 헤더 + 관측 기간을 거친 뒤 제거합니다.

### 관리자/인증
- `GET /admin/login`
- `POST /login` (`POST /admin/login` alias 지원)
- `POST /logout` (권장)
- `GET /logout`
- `GET /admin`
- `POST /admin/upload`
- `POST /admin/public-download/upload`
- `GET /admin/public-download/meta`
- `POST /admin/settings`
- `POST /admin/password`
- `GET /admin/stats`
- `GET /admin/stats/web`
- `GET /admin/raw-queries/export`
- `POST /admin/lands/geom-refresh`
- `GET /admin/lands/geom-refresh/{job_id}`

### 상태 점검
- `GET /health`
- `GET /health?deep=1` (DB + 외부 API 확인)

## 🛡 보안/운영 포인트 (핵심)
- 관리자 보호 경로는 내부망 허용 IP(`ALLOWED_IPS`)와 세션 인증으로 보호되며, 상태 변경 요청에는 CSRF 검증을 적용합니다.
- 로그아웃은 `POST /logout`를 기본 경로로 사용하며 CSRF 검증을 적용합니다. `GET /logout`는 호환성 경로로만 유지됩니다.
- 동일 브라우저/도메인에서 여러 앱을 운영할 경우 `SECRET_KEY`, `SESSION_COOKIE_NAME`, `SESSION_NAMESPACE`를 앱별로 분리해야 세션 교차 인식을 방지할 수 있습니다.
- `VWORLD_WMTS_KEY`는 공개 지도 렌더링(`/api/config`)용 예외 공개 키입니다.
- `VWORLD_GEOCODER_KEY`는 관리자 보호 화면(`/admin`)에서 운영 편의를 위해 예외 공개될 수 있으며, 공개 API/로그 노출은 금지합니다.
- 프록시 환경에서는 `TRUST_PROXY_HEADERS`, `TRUSTED_PROXY_IPS`를 정확히 설정해야 합니다.
- 이벤트 수집 API는 레이트리밋이 적용됩니다.
  - `POST /api/events`: 60 req/min
  - `POST /api/web-events`: 120 req/min
  - 초과 시 `429 Too Many Requests`, `Retry-After` 헤더 반환
  - 현재 보장 범위는 단일 앱 인스턴스 1개 기준입니다.
- 공개 다운로드 API도 레이트리밋이 적용됩니다.
  - `GET /api/public-download`: 기본 10 req/min (`PUBLIC_DOWNLOAD_RATE_LIMIT_PER_MINUTE`)
  - `GET /api/v1/public-download`: `/api/public-download`와 동일
  - 초과 시 `429 Too Many Requests`, `Retry-After` 헤더 반환
- 웹 방문 이벤트는 referrer/utm/page query/클라이언트 컨텍스트(언어/플랫폼/화면크기) 수집을 지원하며,
  관리자 `/admin/stats/web`에서 채널/디바이스/브라우저/상위 페이지 분석 축을 제공합니다.

## ⚠️ 운영 주의사항
- 관리자 화면에서 `.env`를 갱신해도 실행 중 프로세스의 설정 객체는 즉시 교체되지 않습니다. 운영 환경에서는 설정/비밀번호 변경 후 앱 재시작 절차를 함께 운영하세요.
- `SESSION_COOKIE_NAME` 또는 `SESSION_NAMESPACE`를 변경하면 기존 세션이 무효화되므로 관리자 재로그인이 필요합니다.
- 로그인 실패 제한과 이벤트 레이트리밋은 현재 인메모리 구현이며, 지원 배포 형태는 단일 앱 인스턴스 1개입니다.
- 로드밸런서 뒤 다중 인스턴스, 다중 replica, 다중 호스트 배포는 `RISK-002` 해소 전까지 지원하지 않습니다.
- 수평 확장이 필요해지면 공유 스토어 기반 limiter를 선행 도입한 뒤 배포 절차를 다시 정의해야 합니다.
- API 버전 정책(`/api` vs `/api/v1`)의 운영 절차는 `docs/architecture.md`와 `docs/maintenance.md`를 기준으로 관리하세요.
- `/admin/raw-queries/export` CSV는 문자열 셀 선두 `=`, `+`, `-`, `@` 값에 `'` 접두를 추가해 formula injection을 완화합니다.

## ✅ 테스트 및 품질 체크
```bash
python -m compileall -q app tests
mypy app tests create_hash.py
ruff check app tests
scripts/check_quality_warnings.sh
cd frontend && npm run typecheck && npm run build
cd ..
pytest -m unit -q
pytest -m integration -q
pytest -m e2e -q
pytest -q
```

선택 실행:
```bash
RUN_HTTP_E2E=1 pytest -q tests/test_e2e_smoke.py
```

## ⚙️ CI/CD 워크플로
- CI: `.github/workflows/ci.yml`
  - frontend typecheck/build
  - Vite manifest 검증
  - `compileall`, `mypy`, `pytest`
- Deploy: `.github/workflows/deploy.yml`
  - `main` push 또는 수동 실행(`workflow_dispatch`) 시 실행
  - 배포 전 품질 게이트: frontend typecheck/build, `compileall`, `mypy`, `ruff`, `pytest`
  - SSH 원격 배포: 대상 서버에서 `git pull --ff-only` + `docker compose build --pull` + `docker compose up -d`
  - 배포 후 `curl http://127.0.0.1:8000/health` 헬스체크 확인

필수 GitHub Secrets:
- `PROD_HOST`
- `PROD_PORT` (미설정 시 `22`)
- `PROD_USER`
- `PROD_SSH_KEY`
- `PROD_DEPLOY_PATH` (미설정 시 `/opt/IdlePublicProperty`)

## 🐳 Docker 배포 (IP-only, no-domain)
도메인 없이 서버 IP로 직접 접속하는 운영을 가정합니다.

1. 환경 변수 파일 준비:
```bash
cp .env.example .env
```

2. 컨테이너 빌드/기동:
```bash
docker compose build
docker compose up -d
```

3. 상태 확인:
```bash
docker compose ps
curl http://127.0.0.1:8000/health
```

접속 URL:
- 메인: `http://<SERVER_IP>:8000/`
- 관리자 로그인: `http://<SERVER_IP>:8000/admin/login`

운영 메모:
- `docker-compose.yml`은 IP-only 환경을 위해 `SESSION_HTTPS_ONLY=false`, `TRUST_PROXY_HEADERS=false`를 기본값으로 사용합니다.
- SQLite 및 공개 다운로드 파일은 `./data` 볼륨으로 영속화됩니다.
- 현재 Compose 운영 기준은 단일 `app` 인스턴스 1개이며, scale-out은 지원하지 않습니다.

## 📂 디렉터리 구조
```text
project-root/
├─app/                    # FastAPI 애플리케이션
│  ├─routers/             # API 라우터
│  ├─services/            # 비즈니스 로직
│  ├─repositories/        # SQLite 접근
│  ├─clients/             # 외부 API 클라이언트
│  ├─validators/          # 업로드 검증/정규화
│  └─core/                # 설정 로딩
├─frontend/               # Vite + TypeScript 소스
│  └─src/map/             # 지도 화면 기능 모듈(map-view, filters, list-panel, telemetry, download-client, session-tracker 등)
├─templates/              # 서버 렌더링 템플릿
├─static/                 # 정적 파일 및 빌드 산출물(static/dist)
├─data/                   # SQLite DB 및 공개 다운로드 파일
│  └─public_download/
├─tests/                  # 테스트 코드
├─docs/                   # 운영/아키텍처/보안 문서
└─.github/workflows/      # CI/CD 워크플로
```

## 📚 문서
- 문서 포털: `docs/index.md`
- 아키텍처: `docs/architecture.md`
- 유지보수: `docs/maintenance.md`
- 보안 위협 모델: `docs/stride-lite.md`
- 엔지니어링 기준: `docs/engineering-guidelines.md`
- 리스크/개선 TODO: `docs/TODO.MD`

## 📄 라이선스
MIT License
