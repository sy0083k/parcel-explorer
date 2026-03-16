# OpenLayers Selection Style Porting Guide

프로젝트: 관심 필지 지도 (POI Map PNU)  
작성일: 2026-03-16  
최종 수정일: 2026-03-16

## 목적

* 이 문서는 `/siyu`의 MapLibre 선택 강조 레이어(`parcels-selected-\*`)를 자매 OpenLayers 웹앱에 이식할 때, CODEX CLI 또는 Claude Code가 구현 기준으로 직접 사용할 수 있는 작업 지시서이다.
* 목표는 선택된 필지가 기존 관리관 색을 유지하면서도, 흰 halo + 원색 inner line + pulse outline 조합으로 비선택 필지보다 우선적으로 보이게 만드는 것이다.

## 완료 조건

* 선택 필지는 비선택 하이라이트보다 항상 위에 렌더링된다.
* 선택 필지는 관리관별 기존 색을 유지한다.
* 선택 스타일은 `halo + inner line + pulse` 3중 조합으로 렌더링된다.
* `prefers-reduced-motion: reduce` 환경에서는 pulse 애니메이션이 완전히 꺼지고 정적 강조만 남는다.
* 선택 전환, 재조회, 0건 검색, 테마 변경 후에도 이전 pulse 잔상이나 중복 외곽선이 남지 않는다.

## 기준 구현

### 기준 소스

* MapLibre 레이어 정의: `poi-map-pnu/frontend/src/map/map-view-maplibre.ts`
* OpenLayers 현재 선택 스타일 참조: `frontend/src/map/map-view-styles.ts`
* OpenLayers 현재 선택 레이어/타이머 참조: `frontend/src/map/map-view-feature-layers.ts`

### MapLibre 기준 레이어 의미

* `parcels-selected-fill`: 선택 geometry용 source를 유지하는 보조 fill 레이어
* `parcels-selected-halo`: 선택 외곽의 흰 halo
* `parcels-selected-line`: 관리관 색을 유지하는 inner line
* `parcels-selected-pulse`: 관리관 색 pulse outline

### 고정 스타일 값

아래 값은 자매 OpenLayers 웹앱에서도 그대로 유지한다.

|항목|값|
|-|-|
|halo color|`rgba(255, 255, 255, 0.95)`|
|halo width|`8`|
|inner line width|`4`|
|pulse period|`1400ms`|
|pulse width|`4 -> 8`|
|pulse alpha|`0.2 -> 0.7`|

### 선택 fill 정책

* MapLibre 기준 구현에서 선택 fill은 `fill-opacity: 0`이다.
* OpenLayers 이식 시에도 선택 fill은 시각적 강조의 핵심이 아니다.
* 따라서 선택 스타일은 `halo + inner line + pulse`를 중심으로 구현하고, fill은 투명 또는 시각 영향이 없는 수준으로 유지한다.

## OpenLayers 구현 지시

### 레이어 구조

* 기본 하이라이트 레이어와 선택 하이라이트 레이어를 분리한다.
* 선택 레이어는 기본 레이어보다 높은 `zIndex`를 사용한다.
* 선택된 피처는 base source/source-equivalent에 남겨 두지 말고, 선택 전용 레이어(source-equivalent)로 이동시킨다.
* 목표는 선택 필지 경계선이 인접 필지 선에 가려지지 않게 만드는 것이다.

### 스타일 함수 계약

* 선택 레이어 스타일 함수는 단일 `Style`이 아니라 `Style\[]`를 반환한다.
* 반환 순서는 `halo`, `inner`, `pulse`로 고정한다.
* `property\_manager`를 읽어 색상을 결정한다.
* 비시유 테마가 있다면 기존 단일 선택 스타일을 유지해도 된다.
* 시유 테마(`city\_owned` 또는 동등 의미 테마)에서는 반드시 관리관별 색상 매핑을 적용한다.

### pulse 애니메이션

* pulse는 별도 캔버스 커스텀 렌더보다 기존 OpenLayers 선택 레이어 갱신 메커니즘을 우선 사용한다.
* 권장 구현은 선택 레이어에 대해 주기적으로 `changed()`를 호출해 pulse width/alpha를 재계산하는 방식이다.
* 애니메이션 상수는 다음으로 고정한다.

  * `periodMs = 1400`
  * `minWidth = 4`
  * `maxWidth = 8`
  * `minAlpha = 0.2`
  * `maxAlpha = 0.7`
* easing은 현재 기준 구현처럼 sine 기반 왕복 변화를 사용한다.

### 접근성 규칙

* `window.matchMedia("(prefers-reduced-motion: reduce)")`를 사용한다.
* reduced motion이 활성화되면 pulse timer 또는 render loop를 중지한다.
* reduced motion이 활성화되면 선택 스타일은 `halo + inner`만 반환하고 `pulse`는 제외하거나 완전히 투명 처리한다.
* OS 설정이 런타임 중 바뀌는 경우도 반영해야 한다.

### 상태 정리 규칙

* 선택 해제 시 pulse 업데이트를 즉시 중지한다.
* 재조회 결과에 현재 선택 피처가 사라지면 선택 상태를 제거하고 pulse를 중지한다.
* 0건 검색 시 선택 레이어를 비우고 pulse를 중지한다.
* 테마 전환 시 선택 스타일과 pulse 색상 계산 기준을 새 테마로 즉시 갱신한다.
* 뷰 언마운트 또는 페이지 종료 시 타이머를 정리한다.

## 자매 프로젝트 적용 절차

1. 현재 선택 스타일 구현 지점을 찾는다.
2. 기본 하이라이트 레이어와 선택 레이어가 분리되어 있는지 확인한다.
3. 분리되어 있지 않으면 선택 피처를 상위 레이어로 이동시키는 구조로 먼저 정리한다.
4. 선택 스타일 함수를 `Style\[]` 반환 구조로 바꾼다.
5. 관리관별 색상 매핑을 추가한다.
6. pulse 애니메이션 타이머 또는 동일 효과의 갱신 루프를 추가한다.
7. `prefers-reduced-motion` 감지와 정리 로직을 연결한다.
8. 선택 해제, 재조회, 0건 검색, 테마 전환 시 타이머 정리와 레이어 상태 정리가 맞는지 점검한다.

## 구현 체크리스트

* 기존 선택 스타일이 노란 단일 외곽선이면 제거 또는 대체했는가
* 선택 피처가 상위 레이어에만 존재하는가
* `property\_manager` 또는 동등 속성명을 실제 데이터에서 읽을 수 있는가
* 관리관 미일치 시 fallback 색을 사용하는가
* pulse가 선택 피처가 없을 때는 동작하지 않는가
* reduced motion에서 pulse가 완전히 비활성화되는가
* 재조회 후 중복 stroke 또는 잔상 없이 다시 렌더링되는가

## 검증 시나리오

### 시각 검증

* 인접 필지가 맞닿아 있는 구역에서 선택 필지 경계가 가려지지 않는지 확인한다.
* halo가 흰색 외곽선으로 확실히 구분되는지 확인한다.

### 동작 검증

* pulse가 약 `1.4초` 주기로 왕복하는지 확인한다.
* 다른 필지를 클릭했을 때 이전 선택 pulse가 즉시 사라지는지 확인한다.
* 목록 선택, 지도 클릭, 이전/다음 네비게이션 등 선택 경로가 여러 개여도 동일한 스타일이 적용되는지 확인한다.
* 0건 검색 후 이전 선택 스타일이 남지 않는지 확인한다.
* 데이터 재로딩 후에도 선택 레이어와 base 레이어 중복 렌더가 없는지 확인한다.

### 접근성 검증

* `prefers-reduced-motion: reduce` 환경에서 pulse가 보이지 않는지 확인한다.
* reduced motion on/off를 런타임에 바꿨을 때 타이머 상태와 스타일이 즉시 반영되는지 확인한다.

## 도구 지시 문구

아래 지시를 자매 프로젝트에서 그대로 사용할 수 있다.

> `/siyu`의 MapLibre `parcels-selected-\*` 스타일을 OpenLayers 선택 레이어에 이식하라. 선택 피처는 base 레이어보다 높은 zIndex의 전용 레이어에서 렌더링하고, 스타일 함수는 `halo + inner line + pulse` 3개 `Style\[]`를 반환해야 한다. halo는 `rgba(255,255,255,0.95)` width `8`, inner line은 관리관별 색 width `4`, pulse는 같은 색으로 width `4->8`, alpha `0.2->0.7`, period `1400ms` sine easing을 사용한다. `property\_manager` 값은 `도로과=#ff7f00`, `건설과=#377eb8`, `산림공원과=#4daf4a`, `회계과=#e41a1c`, fallback `#984ea3`를 사용한다. `prefers-reduced-motion: reduce`에서는 pulse를 끄고 halo + inner line만 유지하라. 선택 해제, 0건 검색, 데이터 재조회, 테마 전환, 언마운트 시 pulse timer와 선택 레이어 상태를 정리하라. 구현 후 색상 매핑, 렌더 우선순위, reduced motion, 재조회 잔상 유무를 검증하라.`

## 참고 경로

* `/home/ss2175/projects/poi-map-pnu/frontend/src/map/map-view-maplibre.ts`
* `/home/ss2175/projects/poi-map-pnu/frontend/src/map/map-view-styles.ts`
* `/home/ss2175/projects/poi-map-pnu/frontend/src/map/map-view-feature-layers.ts`

