# OpenLayers 자매 앱 `재산 상세 정보` 패널 이식 가이드

프로젝트: 관심 필지 지도 (POI Map PNU)  
작성일: 2026-03-16  
상태: 초안 (에이전트 작업 지시서)

## 1. 문서 목적
- 이 문서는 `'/siyu'` 화면의 `재산 상세 정보` 패널을 OpenLayers 기반 자매 웹앱에 이식할 때, CODEX CLI 또는 Claude Code가 바로 구현 작업을 수행할 수 있도록 작성한 작업 지시서다.
- 목표는 기존 지도 팝업을 우상단 고정 패널로 대체하고, `/siyu`와 거의 동일한 UI/상태 계약을 재현하는 것이다.
- 이 문서는 현행 강제 기준인 `docs/engineering-guidelines.md`를 따르며, `docs/refactoring-strategy.md`, `docs/reports/*`는 참고 대상으로 사용하지 않는다.

## 2. 준수 기준
### 가이드라인 준수 여부
- 준수: 지도 페이지 오케스트레이션과 기능 모듈을 분리한다.
- 준수: 네트워크 호출이 필요하면 공통 HTTP 유틸을 재사용한다.
- 준수: 상세 패널 렌더링, 지도 선택 상태, 레이아웃 겹침 계산을 별도 모듈로 분리한다.
- 준수: 기존 팝업 제거 후 패널 단일 경로만 유지한다. 팝업과 패널을 병행 유지하지 않는다.

### 충돌 지점과 대안
- 충돌 없음.
- 단, 자매 앱 저장소의 구조가 다르면 파일명/경로는 현지화하되 아래 계약과 동작은 그대로 유지한다.

## 3. 기준 구현과 근거 소스
- 패널 렌더러 기준: `frontend/src/map/map-view-info-panel.ts`
- OpenLayers 선택 흐름 기준: `frontend/src/map/map-view.ts`
- OpenLayers 사진 모드 패널 예시: `frontend/src/map/photo-mode-land.ts`
- 패널 제목/ARIA 정책 기준: `frontend/src/map/land-map-ui.ts`
- 패널 마크업 기준: `templates/index.html`
- 패널 겹침 방지 기준: `frontend/src/map/panel-overlap-guard.ts`
- 제품 계약 설명 기준: `docs/architecture.md`, `docs/maintenance.md`, `README.MD`

## 4. 구현 목표
- 사용자가 지도에서 필지를 클릭하면 기존 팝업 대신 우상단 상세 패널이 열린다.
- 패널은 2열 그리드(`속성` / `값`)로 렌더링한다.
- 패널 제목은 기본값으로 `재산 상세 정보`를 사용한다.
- 패널은 `X` 버튼으로 닫을 수 있다.
- 빈 영역 클릭 또는 선택 해제 시 패널은 닫히고, 내용은 기본 empty state로 초기화된다.
- 다른 우측 패널이 있으면 동적 높이 제한으로 겹침을 피한다.
- 접근성 속성(`aria-live`, 제목, 닫기 버튼 라벨)을 유지한다.

## 5. 고정 계약
### 5.1 DOM 계약
- 아래 식별자를 자매 앱에 동일하거나 대응 가능한 형태로 추가한다.

```html
<aside id="land-info-panel" class="is-hidden" aria-live="polite" aria-label="선택 토지 재산 상세 정보">
  <header class="land-info-header">
    <h3 id="land-info-title">재산 상세 정보</h3>
    <button id="land-info-close" class="land-info-close" type="button" aria-label="재산 상세 정보 닫기">✕</button>
  </header>
  <div id="land-info-content" class="land-info-content">
    <div class="land-info-empty">토지를 선택하면 상세 정보가 표시됩니다.</div>
  </div>
</aside>
```

### 5.2 데이터 계약
- 패널은 `source_fields` 배열이 있으면 이를 최우선으로 렌더링한다.
- `source_fields`가 없거나 비어 있으면 아래 fallback 순서를 사용한다.
  - `pnu`
  - `address`
  - `area` (`㎡` 접미사 포함)
  - `land_type`
  - `property_manager`
- 각 행은 `{ key: string, label: string, value: string }` 구조를 따른다.
- 줄바꿈, 탭, carriage return은 공백 1칸으로 정규화한다.
- 빈 값은 렌더하지 않는다.

### 5.3 상태 계약
- 초기 진입 시 패널은 숨김 상태다.
- 필지 클릭 시:
  - 선택 강조 갱신
  - 패널 내용 렌더
  - 패널 열기
- 빈 지도 클릭 시:
  - 선택 강조 해제
  - 패널 닫기
  - empty state 복원
- 사용자가 `X`로 닫은 뒤에도 선택 상태는 유지할 수 있지만, 패널은 다시 필지를 클릭할 때만 자동 재표시한다.
- 목록 클릭과 지도 클릭이 분리된 앱이라면 `/siyu` 계약을 우선한다.
  - 목록 클릭: 선택/이동만 수행, 패널 자동 오픈 금지
  - 지도 클릭: 패널 오픈 허용
- 이전/다음 네비게이션으로 선택이 바뀌는 UI가 있으면 열린 패널은 닫는다.

### 5.4 레이아웃 계약
- 상세 패널은 우상단 고정 배치다.
- 다른 우측 패널(예: 사진 미리보기)이 열려 있으면 해당 패널의 실측 높이와 하단 오프셋을 기준으로 상세 패널 최대 높이를 줄인다.
- 실측값은 `ResizeObserver` + `requestAnimationFrame` 기반 갱신을 권장한다.
- 모바일에서도 패널 내용 스크롤이 가능해야 한다.

### 5.5 접근성 계약
- `aria-live="polite"` 유지
- 패널 제목과 닫기 버튼 `aria-label` 동기화
- 패널을 숨길 때는 `is-hidden` 클래스로 비표시 처리

## 6. 권장 모듈 구성
- `detail-panel.ts`
  - 패널 DOM 조회
  - `renderRows`, `renderProperties`, `clear`, `dismiss`, `show`
- `detail-panel-layout.ts`
  - 다른 패널과의 겹침 방지
  - runtime CSS 변수 계산
- `map-selection-controller.ts`
  - OpenLayers `singleclick`와 선택 상태 연결
  - 빈 지도 클릭 시 clear 처리
- `map-page.ts`
  - 패널, 지도, 목록, 네비게이션 오케스트레이션

자매 앱 구조가 다르면 파일명은 바꿔도 된다. 다만 오케스트레이션 파일에서 DOM 조작과 패널 렌더링 로직을 뒤섞지 않는다.

## 7. 구현 절차
1. 현재 자매 앱의 팝업 구현 위치를 찾는다.
   - `Overlay`, `popup`, `singleclick`, `forEachFeatureAtPixel`, `selectedFeature` 관련 코드를 식별한다.
2. 팝업의 책임을 분해한다.
   - 선택 판정
   - 속성 추출
   - 화면 표시
   - 닫기
   - 지도 이동
3. 패널 마크업과 스타일을 추가한다.
   - 팝업용 DOM은 제거 대상이다.
4. 패널 렌더러 모듈을 만든다.
   - `source_fields` 우선, fallback 보조 규칙 구현
   - empty state와 dismiss 상태 구현
5. 지도 클릭 흐름을 패널로 연결한다.
   - 필지 클릭 시 패널 렌더
   - 빈 영역 클릭 시 패널 clear
6. 목록/네비게이션이 있으면 `/siyu` 기준으로 상호작용을 맞춘다.
7. 다른 우측 패널이 있으면 겹침 방지 가드를 붙인다.
8. 기존 팝업 DOM, 스타일, 이벤트 바인딩을 제거한다.
9. 테스트와 수동 검증을 수행한다.

## 8. 에이전트에게 줄 구체 지시
- 팝업 제거는 마지막 단계가 아니라, 패널 연결이 완료된 뒤 잔여 코드 제거까지 한 번에 마무리한다.
- 기존 OpenLayers feature 선택/강조 로직은 유지하고, 정보 표시 방식만 패널로 교체한다.
- 패널 렌더러는 지도 엔진 API에 직접 의존하지 않도록 작성한다. 입력은 `feature.properties` 또는 정규화된 land record여야 한다.
- `source_fields`가 이미 있으면 라벨명을 재해석하지 않는다.
- 패널 내용은 `textContent`로만 삽입한다. HTML 문자열을 직접 주입하지 않는다.
- 자매 앱에 사진 패널이 없으면 겹침 방지 모듈은 선택 구현으로 둘 수 있다. 단, 추후 패널 추가 가능성을 고려해 훅은 남긴다.

## 9. 금지 사항
- 지도 팝업과 우상단 패널을 동시에 유지하지 않는다.
- 지도 클릭 핸들러 내부에 긴 DOM 생성 코드를 직접 작성하지 않는다.
- 동일한 key/value 렌더링 로직을 목록 모드와 지도 모드에 중복 복사하지 않는다.
- empty state 없이 빈 패널을 노출하지 않는다.
- 서버 응답 계약을 임의 변경하지 않는다.

## 10. 수용 기준
- 필지 클릭 시 팝업이 아니라 우상단 패널이 열린다.
- 패널 제목은 `재산 상세 정보`다.
- `source_fields`가 있으면 해당 순서/라벨 그대로 렌더된다.
- `source_fields`가 없으면 fallback 필드가 정상 노출된다.
- 빈 지도 클릭 시 선택과 패널 상태가 함께 정리된다.
- `X` 버튼으로 패널을 닫을 수 있다.
- 목록 선택만으로는 패널이 자동 오픈되지 않는다.
- 우측 사진 패널 등 다른 패널과 동시에 열려도 겹치지 않는다.
- 모바일에서 긴 값이 있어도 패널이 깨지지 않고 스크롤 가능하다.

## 11. 테스트 시나리오
### 자동화 테스트 권장
- 패널 DOM 기본 렌더와 empty state 렌더
- `source_fields` 우선 렌더
- fallback 필드 렌더
- dismiss 후 재클릭 시 재오픈
- 빈 클릭 시 clear 처리

### 수동 검증
- 필지 클릭, 빈 영역 클릭, 다른 필지 재선택
- 목록 클릭 후 패널 미오픈 확인
- 이전/다음 네비게이션 사용 시 패널 닫힘 확인
- 긴 라벨/긴 값 조합 줄바꿈 확인
- 사진 패널 동시 노출 시 겹침 없음 확인
- 모바일 폭에서 최대 높이와 내부 스크롤 확인

## 12. 구현 후 보고 형식
- 가이드라인 준수 여부
- 변경한 진입점과 모듈
- 제거한 팝업 코드 위치
- 테스트 실행 결과
- 잔여 리스크

## 13. 자매 앱 구현자용 요약 프롬프트
아래 요약을 CODEX CLI 또는 Claude Code에 직접 전달할 수 있다.

```text
OpenLayers 기반 지도 앱에서 기존 토지 상세 popup을 제거하고, `/siyu`와 동일한 우상단 `재산 상세 정보` 패널로 교체하라.

요구사항:
- 필지 클릭 시 패널 오픈, 빈 지도 클릭 시 패널 닫기/초기화
- `source_fields` 우선 렌더, 없으면 pnu/address/area/land_type/property_manager fallback
- 제목은 `재산 상세 정보`
- `X` 닫기 버튼, `aria-live="polite"` 유지
- 목록 클릭만으로는 패널을 자동 오픈하지 말 것
- 다른 우측 패널이 있으면 높이 겹침 방지 적용
- 기존 popup DOM/style/event는 최종적으로 제거
- 패널 렌더링 로직은 지도 클릭 핸들러에서 분리된 모듈로 작성

완료 후에는 변경 파일, 테스트 결과, 잔여 리스크를 보고하라.
```
