type LayoutOptions = {
  panel: HTMLElement;
  // 향후: siblingPanel?: HTMLElement
};

export function createDetailPanelLayout(_options: LayoutOptions) {
  // 현재 우측 패널 없음 → no-op
  // 향후: ResizeObserver로 --land-info-panel-max-height CSS 변수를 동적 갱신
  return {
    destroy(): void {
      // 향후: observer.disconnect()
    },
  };
}
