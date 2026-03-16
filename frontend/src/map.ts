import "ol/ol.css";

import { HttpError, fetchJson } from "./http";
import { createDetailPanel } from "./map/detail-panel";
import { createDetailPanelLayout } from "./map/detail-panel-layout";
import { createDownloadClient } from "./map/download-client";
import { createFilters } from "./map/filters";
import { streamLandFeatures } from "./map/lands-client";
import { createListPanel } from "./map/list-panel";
import { createMapView } from "./map/map-view";
import { createSessionTracker } from "./map/session-tracker";
import { createMapState } from "./map/state";
import { createTelemetry } from "./map/telemetry";

import type { BaseType, LandClickSource, LandFeature, LandFeatureCollection, MapConfig } from "./map/types";

type SelectOptions = {
  shouldFit: boolean;
  clickSource?: LandClickSource;
  coordinateOverride?: number[];
};

type MobileViewState = "home" | "search" | "results";
const MOBILE_MEDIA_QUERY = "(max-width: 768px)";
const MOBILE_HISTORY_KEY = "mobileMapViewState";
const MOBILE_SHEET_HEIGHT_VAR = "--mobile-sheet-height";
const MOBILE_RESULTS_DEFAULT_SHEET_HEIGHT = "25vh";

function isMobileViewport(): boolean {
  return window.matchMedia(MOBILE_MEDIA_QUERY).matches;
}

function readMobileViewState(value: unknown): MobileViewState | null {
  if (value === "home" || value === "search" || value === "results") {
    return value;
  }
  return null;
}

async function bootstrap(): Promise<void> {
  const regionSearchInput = document.getElementById("region-search") as HTMLInputElement | null;
  const minAreaInput = document.getElementById("min-area") as HTMLInputElement | null;
  const maxAreaInput = document.getElementById("max-area") as HTMLInputElement | null;
  const rentOnlyFilter = document.getElementById("rent-only-filter") as HTMLInputElement | null;

  const mobileRegionSearchInput = document.getElementById("mobile-region-search") as HTMLInputElement | null;
  const mobileMinAreaInput = document.getElementById("mobile-min-area") as HTMLInputElement | null;
  const mobileMaxAreaInput = document.getElementById("mobile-max-area") as HTMLInputElement | null;
  const mobileRentOnlyFilter = document.getElementById("mobile-rent-only-filter") as HTMLInputElement | null;
  const mobileSearchFab = document.getElementById("mobile-search-fab");
  const mobileSearchCloseBtn = document.getElementById("mobile-search-close");
  const mobileSearchBtn = document.getElementById("mobile-btn-search");
  const mobileResetBtn = document.getElementById("mobile-btn-reset-filters");
  const mobileDownloadBtn = document.getElementById("mobile-btn-download-all");

  const layerToggleBtn = document.getElementById("btn-layer-toggle");
  const layerPopover = document.getElementById("layer-popover");
  const mobileBaseBtn = document.getElementById("m-btn-Base");
  const mobileSatelliteBtn = document.getElementById("m-btn-Satellite");
  const mobileHybridBtn = document.getElementById("m-btn-Hybrid");

  const state = createMapState();
  const telemetry = createTelemetry();
  const sessionTracker = createSessionTracker({
    getOrCreateAnonId: telemetry.getOrCreateAnonId,
    postWebEvent: telemetry.postWebEvent
  });
  const mapView = createMapView();

  const panelEl = document.getElementById("land-info-panel");
  const panelContent = document.getElementById("land-info-content");
  const panelCloseBtn = document.getElementById("land-info-close");

  const detailPanel = createDetailPanel({
    panel: panelEl instanceof HTMLElement ? panelEl : document.createElement("aside"),
    content: panelContent instanceof HTMLElement ? panelContent : document.createElement("div"),
    closeBtn: panelCloseBtn instanceof HTMLElement ? panelCloseBtn : document.createElement("button"),
  });
  createDetailPanelLayout({ panel: panelEl instanceof HTMLElement ? panelEl : document.createElement("aside") });

  detailPanel.bindCloseButton(() => detailPanel.dismiss());
  const listPanel = createListPanel({
    listContainer: document.getElementById("list-container"),
    navInfo: document.getElementById("nav-info"),
    prevBtn: document.getElementById("prev-btn") as HTMLButtonElement | null,
    nextBtn: document.getElementById("next-btn") as HTMLButtonElement | null,
    sidebar: document.getElementById("sidebar"),
    handle: document.querySelector(".mobile-handle")
  });
  const filters = createFilters({
    regionSearchInput,
    minAreaInput,
    maxAreaInput,
    rentOnlyFilter
  });
  const downloadClient = createDownloadClient();

  let mobileState: MobileViewState = "home";
  const syncDesktopToMobileInputs = (): void => {
    if (
      !regionSearchInput ||
      !minAreaInput ||
      !maxAreaInput ||
      !rentOnlyFilter ||
      !mobileRegionSearchInput ||
      !mobileMinAreaInput ||
      !mobileMaxAreaInput ||
      !mobileRentOnlyFilter
    ) {
      return;
    }
    mobileRegionSearchInput.value = regionSearchInput.value;
    mobileMinAreaInput.value = minAreaInput.value;
    mobileMaxAreaInput.value = maxAreaInput.value;
    mobileRentOnlyFilter.checked = rentOnlyFilter.checked;
  };

  const syncMobileToDesktopInputs = (): void => {
    if (
      !regionSearchInput ||
      !minAreaInput ||
      !maxAreaInput ||
      !rentOnlyFilter ||
      !mobileRegionSearchInput ||
      !mobileMinAreaInput ||
      !mobileMaxAreaInput ||
      !mobileRentOnlyFilter
    ) {
      return;
    }
    regionSearchInput.value = mobileRegionSearchInput.value;
    minAreaInput.value = mobileMinAreaInput.value;
    maxAreaInput.value = mobileMaxAreaInput.value;
    rentOnlyFilter.checked = mobileRentOnlyFilter.checked;
  };

  const applyMobileClass = (): void => {
    document.body.classList.remove("mobile-home", "mobile-search", "mobile-results");
    if (!isMobileViewport()) {
      return;
    }
    document.body.classList.add(`mobile-${mobileState}`);

    const overlay = document.getElementById("mobile-search-overlay");
    if (overlay) {
      if (mobileState === "search") {
        overlay.removeAttribute("inert");
      } else {
        overlay.setAttribute("inert", "");
      }
    }
  };

  const setMobileState = (nextState: MobileViewState, pushHistory = true): void => {
    mobileState = nextState;
    applyMobileClass();
    if (!isMobileViewport()) {
      document.body.style.removeProperty(MOBILE_SHEET_HEIGHT_VAR);
    } else if (nextState === "results") {
      document.body.style.setProperty(MOBILE_SHEET_HEIGHT_VAR, MOBILE_RESULTS_DEFAULT_SHEET_HEIGHT);
    } else {
      document.body.style.removeProperty(MOBILE_SHEET_HEIGHT_VAR);
    }
    if (!isMobileViewport() || !pushHistory) {
      return;
    }
    const current = history.state && typeof history.state === "object" ? history.state : {};
    history.pushState({ ...current, [MOBILE_HISTORY_KEY]: nextState }, "");
  };

  const maybeInitMobileHistory = (): void => {
    if (!isMobileViewport()) {
      return;
    }
    const current = history.state && typeof history.state === "object" ? history.state : {};
    history.replaceState({ ...current, [MOBILE_HISTORY_KEY]: mobileState }, "");
    applyMobileClass();
  };

  const updateNavigation = (): void => {
    listPanel.updateNavigation(state.getCurrentIndex(), state.getCurrentFeatures().length);
  };

  const selectItem = (index: number, options: SelectOptions): void => {
    const currentFeatures = state.getCurrentFeatures();
    if (index < 0 || index >= currentFeatures.length) {
      return;
    }

    state.setCurrentIndex(index);

    if (options.clickSource) {
      const selected = currentFeatures[index];
      telemetry.trackLandClickEvent(
        selected?.properties.address || "",
        options.clickSource,
        selected?.properties.id
      );
    }

    mapView.selectFeatureByIndex(index, {
      shouldFit: options.shouldFit,
      coordinateOverride: options.coordinateOverride,
    });

    if (options.clickSource === "map_click") {
      const selected = currentFeatures[index];
      if (selected) {
        detailPanel.renderProperties(selected.properties);
        detailPanel.show();
      }
    } else if (options.clickSource === "nav_prev" || options.clickSource === "nav_next") {
      detailPanel.dismiss();
    }

    updateNavigation();
    listPanel.scrollTo(index);
  };

  const updateMapAndList = (data: LandFeatureCollection): void => {
    state.setCurrentFeatures(data.features);
    mapView.renderFeatures(data);
    listPanel.render(data.features, (idx) => {
      selectItem(idx, { shouldFit: true, clickSource: "list_click" });
    });

    if (data.features.length > 0) {
      mapView.fitToFeatures();
    }

    updateNavigation();
  };

  const applyFilters = (trackEvent = false): void => {
    const originalData = state.getOriginalData();
    if (!originalData) {
      return;
    }

    const values = filters.getValues();
    const filteredFeatures = filters.filterFeatures(originalData.features, values);

    if (trackEvent) {
      telemetry.trackSearchEvent(
        values.minArea,
        values.searchTerm,
        values.rawSearchTerm,
        values.rawMinAreaInput,
        values.rawMaxAreaInput,
        String(values.isRentOnly)
      );
    }

    updateMapAndList({ type: "FeatureCollection", features: filteredFeatures });
  };

  const resetFilters = (): void => {
    filters.reset();
    syncDesktopToMobileInputs();
    mapView.clearPopup();
    detailPanel.dismiss();
    applyFilters(false);
  };

  const navigateItem = (direction: number): void => {
    const nextIndex = state.getCurrentIndex() + direction;
    if (nextIndex < 0 || nextIndex >= state.getCurrentFeatures().length) {
      return;
    }

    selectItem(nextIndex, {
      shouldFit: true,
      clickSource: direction < 0 ? "nav_prev" : "nav_next"
    });
  };

  const closeLayerPopover = (): void => {
    if (!(layerPopover instanceof HTMLElement) || !(layerToggleBtn instanceof HTMLButtonElement)) {
      return;
    }
    layerPopover.classList.remove("open");
    layerPopover.setAttribute("inert", "");
    layerToggleBtn.setAttribute("aria-expanded", "false");
  };

  const changeLayerFromMobile = (type: BaseType): void => {
    mapView.changeLayer(type);
    closeLayerPopover();
  };

  mapView.setFeatureClickHandler(({ index, coordinate }) => {
    selectItem(index, {
      shouldFit: false,
      clickSource: "map_click",
      coordinateOverride: coordinate,
    });
  });

  mapView.setEmptyClickHandler(() => {
    detailPanel.dismiss();
  });

  document.getElementById("btn-search")?.addEventListener("click", () => applyFilters(true));
  document.getElementById("btn-reset-filters")?.addEventListener("click", resetFilters);
  document.getElementById("btn-download-all")?.addEventListener("click", () => {
    void downloadClient.downloadPreparedFile();
  });
  rentOnlyFilter?.addEventListener("change", () => applyFilters(false));

  document.getElementById("btn-Base")?.addEventListener("click", () => mapView.changeLayer("Base"));
  document.getElementById("btn-Satellite")?.addEventListener("click", () => mapView.changeLayer("Satellite"));
  document.getElementById("btn-Hybrid")?.addEventListener("click", () => mapView.changeLayer("Hybrid"));

  layerToggleBtn?.addEventListener("click", (event) => {
    if (!(layerPopover instanceof HTMLElement) || !(layerToggleBtn instanceof HTMLButtonElement)) {
      return;
    }
    event.stopPropagation();
    const willOpen = !layerPopover.classList.contains("open");
    layerPopover.classList.toggle("open", willOpen);
    if (willOpen) {
      layerPopover.removeAttribute("inert");
    } else {
      layerPopover.setAttribute("inert", "");
    }
    layerToggleBtn.setAttribute("aria-expanded", willOpen ? "true" : "false");
  });
  mobileBaseBtn?.addEventListener("click", () => changeLayerFromMobile("Base"));
  mobileSatelliteBtn?.addEventListener("click", () => changeLayerFromMobile("Satellite"));
  mobileHybridBtn?.addEventListener("click", () => changeLayerFromMobile("Hybrid"));
  document.addEventListener("click", (event) => {
    if (
      !(layerPopover instanceof HTMLElement) ||
      !(layerToggleBtn instanceof HTMLElement) ||
      !(event.target instanceof Node)
    ) {
      return;
    }
    if (!layerPopover.contains(event.target) && !layerToggleBtn.contains(event.target)) {
      closeLayerPopover();
    }
  });
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") {
      closeLayerPopover();
    }
  });

  listPanel.bindNavigation(
    () => navigateItem(-1),
    () => navigateItem(1)
  );

  filters.attachEnter(() => applyFilters(true));
  listPanel.initBottomSheet();
  sessionTracker.mount();

  mobileSearchFab?.addEventListener("click", () => {
    if (!isMobileViewport()) {
      return;
    }
    syncDesktopToMobileInputs();
    setMobileState("search", true);
  });
  mobileSearchCloseBtn?.addEventListener("click", () => {
    if (!isMobileViewport()) {
      return;
    }
    history.back();
  });
  mobileSearchBtn?.addEventListener("click", () => {
    if (!isMobileViewport()) {
      return;
    }
    syncMobileToDesktopInputs();
    applyFilters(true);
    setMobileState("results", true);
  });
  mobileResetBtn?.addEventListener("click", () => {
    syncMobileToDesktopInputs();
    resetFilters();
    syncDesktopToMobileInputs();
  });
  mobileDownloadBtn?.addEventListener("click", () => {
    void downloadClient.downloadPreparedFile();
  });

  window.addEventListener("popstate", (event) => {
    if (!isMobileViewport()) {
      return;
    }
    const nextState = readMobileViewState(
      event.state && typeof event.state === "object"
        ? (event.state as Record<string, unknown>)[MOBILE_HISTORY_KEY]
        : null
    );
    if (!nextState) {
      return;
    }
    setMobileState(nextState, false);
  });

  window.matchMedia(MOBILE_MEDIA_QUERY).addEventListener("change", () => {
    applyMobileClass();
  });

  try {
    listPanel.setStatus("데이터를 불러오는 중입니다...");
    const config = await fetchJson<MapConfig>("/api/config", { timeoutMs: 10000 });
    mapView.init(config);

    const accumulated: LandFeature[] = [];
    let initialRenderDone = false;

    await streamLandFeatures((batch) => {
      accumulated.push(...batch);

      if (!initialRenderDone) {
        initialRenderDone = true;
        state.setOriginalData({ type: "FeatureCollection", features: [...accumulated] });
        applyFilters(false);
        syncDesktopToMobileInputs();
        maybeInitMobileHistory();
        if (isMobileViewport()) {
          setMobileState("home", false);
        }
      } else {
        state.appendToOriginalData(batch);
      }
    });

    // 모든 배치 완료 후: 선택 항목이 없으면 전체 데이터로 최종 재렌더링
    if (state.getCurrentIndex() === -1) {
      state.setOriginalData({ type: "FeatureCollection", features: accumulated });
      applyFilters(false);
    }
  } catch (error) {
    const message = error instanceof HttpError ? error.message : "지도를 초기화하지 못했습니다.";
    listPanel.setStatus(message, "red");
  }
}

document.addEventListener("DOMContentLoaded", () => {
  void bootstrap();
});
