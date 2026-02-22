import "ol/ol.css";

import { HttpError, fetchJson } from "./http";
import { createDownloadClient } from "./map/download-client";
import { createFilters } from "./map/filters";
import { loadAllLandFeatures } from "./map/lands-client";
import { createListPanel } from "./map/list-panel";
import { createMapView } from "./map/map-view";
import { createSessionTracker } from "./map/session-tracker";
import { createMapState } from "./map/state";
import { createTelemetry } from "./map/telemetry";

import type { LandClickSource, LandFeatureCollection, MapConfig } from "./map/types";

type SelectOptions = {
  shouldFit: boolean;
  clickSource?: LandClickSource;
  coordinateOverride?: number[];
  panIntoView?: boolean;
};

async function bootstrap(): Promise<void> {
  const regionSearchInput = document.getElementById("region-search") as HTMLInputElement | null;
  const minAreaInput = document.getElementById("min-area") as HTMLInputElement | null;
  const maxAreaInput = document.getElementById("max-area") as HTMLInputElement | null;
  const rentOnlyFilter = document.getElementById("rent-only-filter") as HTMLInputElement | null;

  const popupElement = document.getElementById("popup");
  const popupContent = document.getElementById("popup-content");
  const popupCloser = document.getElementById("popup-closer");

  if (!(popupElement instanceof HTMLElement) || !(popupContent instanceof HTMLElement)) {
    return;
  }

  const state = createMapState();
  const telemetry = createTelemetry();
  const sessionTracker = createSessionTracker({
    getOrCreateAnonId: telemetry.getOrCreateAnonId,
    postWebEvent: telemetry.postWebEvent
  });
  const mapView = createMapView({
    popupElement,
    popupContent,
    popupCloser: popupCloser instanceof HTMLElement ? popupCloser : null
  });
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
      panIntoView: options.panIntoView
    });

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
    mapView.clearPopup();
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

  mapView.setFeatureClickHandler(({ index, coordinate }) => {
    selectItem(index, {
      shouldFit: false,
      clickSource: "map_click",
      coordinateOverride: coordinate,
      panIntoView: true
    });
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

  listPanel.bindNavigation(
    () => navigateItem(-1),
    () => navigateItem(1)
  );

  filters.attachEnter(() => applyFilters(true));
  listPanel.initBottomSheet();
  sessionTracker.mount();

  try {
    listPanel.setStatus("데이터를 불러오는 중입니다...");
    const config = await fetchJson<MapConfig>("/api/config", { timeoutMs: 10000 });
    mapView.init(config);
    const features = await loadAllLandFeatures();
    state.setOriginalData({ type: "FeatureCollection", features });
    applyFilters(false);
  } catch (error) {
    const message = error instanceof HttpError ? error.message : "지도를 초기화하지 못했습니다.";
    listPanel.setStatus(message, "red");
  }
}

document.addEventListener("DOMContentLoaded", () => {
  void bootstrap();
});
