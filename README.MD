# 🏠 서산시 유휴공유재산 관리 시스템 (Idle Land Map)

브이월드(V-World) API를 활용하여 서산시의 유휴 공유재산 데이터를 지도 위에 시각화하고, 관리자가 엑셀 업로드를 통해 데이터를 손쉽게 업데이트할 수 있는 웹 애플리케이션입니다.

---

## 📌 1. 프로젝트 개요

### 🎯 용도 및 목적

* **공공데이터 시각화:** 복잡한 주소로 된 공유재산 목록을 지도 상의 필지 경계선(Polygon)으로 시각화하여 한눈에 파악할 수 있게 합니다.
* **간편한 데이터 관리:** 개발 지식이 없는 담당자도 엑셀 파일 업로드만으로 DB를 최신화할 수 있도록 설계되었습니다.
* **정보 접근성 향상:** 면적, 지목, 연락처 등의 정보를 클릭 한 번으로 확인할 수 있습니다.

### 💪 프로젝트의 강점 (Strengths)

* **정확한 필지 시각화:** 단순 마커 표시가 아니라, 브이월드 API를 통해 실제 토지의 경계선을 정확히 그려줍니다.
* **보안성:** 관리자 전용 세션 기반 로그인 시스템을 통해 보안을 강화했습니다.
* **사용자 친화적:** 엑셀 파일을 업로드하면 백그라운드에서 필지별 경계선 정보를 취득합니다.

### ⚠️ 프로젝트의 약점 (Weaknesses)

* **API 의존성:** 브이월드 API 상태에 따라 필지 경계선 로딩 속도가 달라질 수 있습니다.
* **데이터 정제 필요:** 엑셀 내 주소 형식이 올바르지 않으면(예: 오타) 지적 정보를 불러오지 못할 수 있습니다.

---

## 🛠 2. 사용 기술 (Tech Stack)

* **Backend:** Python 3.10+, FastAPI
* **Frontend:** Vanilla JS, OpenLayers (지도 라이브러리)
* **Database:** SQLite3 (파일 기반 경량 DB)
* **API:** V-World 요청 API (주소 검색 및 Feature 서비스)

---

## 🚀 3. 시작하기 (사용 방법)

초보자도 따라 할 수 있도록 순서대로 설명합니다.

### 1단계: 필수 소프트웨어 설치

1. **Python 설치:** `https://www.python.org/`에서 최신 버전을 설치합니다. (설치 시 'Add Python to PATH' 체크 필수)
2. **V-World API 키 발급:** `https://www.vworld.kr/`에서 인증키를 발급받습니다.

### 2단계: 프로젝트 설정

프로젝트 폴더 안에 `.env` 파일을 만들고 아래 내용을 입력합니다.

```env
VWORLD_KEY=여기에_발급받은_키_입력
ADMIN_ID=admin
ADMIN_PW_HASH=여기에_bcrypt_해시값_입력
SECRET_KEY=충분히_긴_랜덤_문자열
ALLOWED_IPS=127.0.0.1/32,::1/128
SESSION_HTTPS_ONLY=false
```

`ADMIN_PW_HASH`는 평문 비밀번호가 아니라 bcrypt 해시값이어야 합니다.  
해시는 `python create_hash.py`로 생성할 수 있습니다.

### 3단계: 라이브러리 설치

터미널(또는 CMD)을 열고 아래 명령어를 입력하여 필요한 도구들을 설치합니다.

```bash
pip install -r requirements.txt
```

### 4단계: 서버 실행

```bash
uvicorn app.main:app --reload
```

서버가 실행되면 웹 브라우저 주소창에 `http://127.0.0.1:8000`을 입력합니다.

API 버전 스캐폴딩은 `/api`와 동일 응답을 제공하는 `/api/v1` 경로를 추가로 제공합니다.

### 5단계: 관리자 기능 사용

1. `http://127.0.0.1:8000/admin/login`으로 접속합니다.
2. 설정한 아이디/비밀번호로 로그인합니다.
3. 관리자 페이지에서 **'주소, 면적, 지목, 문의'** 컬럼이 포함된 엑셀 파일을 업로드합니다.
4. 업로드가 완료되면 메인 지도 화면에서 데이터가 시각화되는 것을 확인합니다.

---

## 📂 4. 폴더 구조

```text
project-root/
│  .env               # API 키 및 로그인 정보
│  requirements.txt   # Python 의존성 목록
│
├─app/
│  ├─main.py          # FastAPI 엔트리포인트
│  ├─routers/         # 라우터 (얇은 컨트롤러)
│  ├─services/        # 서비스 계층
│  ├─repositories/    # DB 접근 계층
│  ├─clients/         # 외부 API 클라이언트
│  └─validators/      # 업로드 검증/정규화
│
├─data/
│  └─database.db      # 데이터 저장소 (자동 생성)
│
├─templates/          # HTML 파일 보관함
│      index.html     # 메인 지도 화면
│      login.html     # 로그인 화면
│      admin.html     # 관리자 업로드 화면
│
└─static/             # CSS, 이미지 등
```

---

## 📚 6. 문서

- 아키텍처/흐름: `docs/architecture.md`
- 보안(STRIDE-lite): `docs/stride-lite.md`
- 유지보수: `docs/maintenance.md`

---

## 📄 5. 라이선스

이 프로젝트는 MIT 라이선스를 따릅니다. 누구나 자유롭게 수정하고 배포할 수 있습니다.

---

**도움이 필요하신가요?** 이 프로젝트의 개선 사항이나 버그 발견 시 Issues 탭에 남겨주세요!
