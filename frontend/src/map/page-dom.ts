type MapInputRefs = {
  regionSearchInput: HTMLInputElement | null;
  minAreaInput: HTMLInputElement | null;
  maxAreaInput: HTMLInputElement | null;
  rentOnlyFilter: HTMLInputElement | null;
};

export type MapPageDomRefs = {
  desktopInputs: MapInputRefs;
  mobileInputs: MapInputRefs;
  mobileSearchFab: HTMLElement | null;
  mobileSearchCloseBtn: HTMLElement | null;
  mobileSearchBtn: HTMLElement | null;
  mobileResetBtn: HTMLElement | null;
  mobileDownloadBtn: HTMLElement | null;
  mobileSearchOverlay: HTMLElement | null;
  layerToggleBtn: HTMLButtonElement | null;
  layerPopover: HTMLElement | null;
  desktopBaseBtn: HTMLElement | null;
  desktopSatelliteBtn: HTMLElement | null;
  desktopHybridBtn: HTMLElement | null;
  mobileBaseBtn: HTMLElement | null;
  mobileSatelliteBtn: HTMLElement | null;
  mobileHybridBtn: HTMLElement | null;
  listContainer: HTMLElement | null;
  navInfo: HTMLElement | null;
  prevBtn: HTMLButtonElement | null;
  nextBtn: HTMLButtonElement | null;
  sidebar: HTMLElement | null;
  handle: Element | null;
  panel: HTMLElement | null;
  panelContent: HTMLElement | null;
  panelCloseBtn: HTMLElement | null;
  searchBtn: HTMLElement | null;
  resetFiltersBtn: HTMLElement | null;
  downloadAllBtn: HTMLElement | null;
  mobileMediaQueryList: MediaQueryList;
};

function asElement<T extends Element>(
  value: Element | null,
  ctor: { new (): T }
): T | null {
  return value instanceof ctor ? value : null;
}

export function collectMapPageDom(
  mediaQueryList: MediaQueryList = window.matchMedia("(max-width: 768px)")
): MapPageDomRefs {
  return {
    desktopInputs: {
      regionSearchInput: asElement(document.getElementById("region-search"), HTMLInputElement),
      minAreaInput: asElement(document.getElementById("min-area"), HTMLInputElement),
      maxAreaInput: asElement(document.getElementById("max-area"), HTMLInputElement),
      rentOnlyFilter: asElement(document.getElementById("rent-only-filter"), HTMLInputElement),
    },
    mobileInputs: {
      regionSearchInput: asElement(document.getElementById("mobile-region-search"), HTMLInputElement),
      minAreaInput: asElement(document.getElementById("mobile-min-area"), HTMLInputElement),
      maxAreaInput: asElement(document.getElementById("mobile-max-area"), HTMLInputElement),
      rentOnlyFilter: asElement(document.getElementById("mobile-rent-only-filter"), HTMLInputElement),
    },
    mobileSearchFab: asElement(document.getElementById("mobile-search-fab"), HTMLElement),
    mobileSearchCloseBtn: asElement(document.getElementById("mobile-search-close"), HTMLElement),
    mobileSearchBtn: asElement(document.getElementById("mobile-btn-search"), HTMLElement),
    mobileResetBtn: asElement(document.getElementById("mobile-btn-reset-filters"), HTMLElement),
    mobileDownloadBtn: asElement(document.getElementById("mobile-btn-download-all"), HTMLElement),
    mobileSearchOverlay: asElement(document.getElementById("mobile-search-overlay"), HTMLElement),
    layerToggleBtn: asElement(document.getElementById("btn-layer-toggle"), HTMLButtonElement),
    layerPopover: asElement(document.getElementById("layer-popover"), HTMLElement),
    desktopBaseBtn: asElement(document.getElementById("btn-Base"), HTMLElement),
    desktopSatelliteBtn: asElement(document.getElementById("btn-Satellite"), HTMLElement),
    desktopHybridBtn: asElement(document.getElementById("btn-Hybrid"), HTMLElement),
    mobileBaseBtn: asElement(document.getElementById("m-btn-Base"), HTMLElement),
    mobileSatelliteBtn: asElement(document.getElementById("m-btn-Satellite"), HTMLElement),
    mobileHybridBtn: asElement(document.getElementById("m-btn-Hybrid"), HTMLElement),
    listContainer: asElement(document.getElementById("list-container"), HTMLElement),
    navInfo: asElement(document.getElementById("nav-info"), HTMLElement),
    prevBtn: asElement(document.getElementById("prev-btn"), HTMLButtonElement),
    nextBtn: asElement(document.getElementById("next-btn"), HTMLButtonElement),
    sidebar: asElement(document.getElementById("sidebar"), HTMLElement),
    handle: document.querySelector(".mobile-handle"),
    panel: asElement(document.getElementById("land-info-panel"), HTMLElement),
    panelContent: asElement(document.getElementById("land-info-content"), HTMLElement),
    panelCloseBtn: asElement(document.getElementById("land-info-close"), HTMLElement),
    searchBtn: asElement(document.getElementById("btn-search"), HTMLElement),
    resetFiltersBtn: asElement(document.getElementById("btn-reset-filters"), HTMLElement),
    downloadAllBtn: asElement(document.getElementById("btn-download-all"), HTMLElement),
    mobileMediaQueryList: mediaQueryList,
  };
}
