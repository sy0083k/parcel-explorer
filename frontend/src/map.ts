import "ol/ol.css";

import { createDetailPanel } from "./map/detail-panel";
import { createDetailPanelLayout } from "./map/detail-panel-layout";
import { createDownloadClient } from "./map/download-client";
import { createFilters } from "./map/filters";
import { createListPanel } from "./map/list-panel";
import { bootstrapMapData } from "./map/map-bootstrap";
import { bindMapPageEvents } from "./map/map-page-events";
import { createMapView } from "./map/map-view";
import { createMobileMapUi } from "./map/mobile-map-ui";
import { collectMapPageDom } from "./map/page-dom";
import { createMapSelectionController } from "./map/selection-controller";
import { createSessionTracker } from "./map/session-tracker";
import { createMapState } from "./map/state";
import { createTelemetry } from "./map/telemetry";

async function bootstrap(): Promise<void> {
  const dom = collectMapPageDom();
  const state = createMapState();
  const telemetry = createTelemetry();
  const sessionTracker = createSessionTracker({
    getOrCreateAnonId: telemetry.getOrCreateAnonId,
    postWebEvent: telemetry.postWebEvent
  });
  const mapView = createMapView();

  const detailPanel = createDetailPanel({
    panel: dom.panel ?? document.createElement("aside"),
    content: dom.panelContent ?? document.createElement("div"),
    closeBtn: dom.panelCloseBtn ?? document.createElement("button"),
  });
  createDetailPanelLayout({ panel: dom.panel ?? document.createElement("aside") });

  detailPanel.bindCloseButton(() => detailPanel.dismiss());
  const listPanel = createListPanel({
    listContainer: dom.listContainer,
    navInfo: dom.navInfo,
    prevBtn: dom.prevBtn,
    nextBtn: dom.nextBtn,
    sidebar: dom.sidebar,
    handle: dom.handle
  });
  const filters = createFilters({
    regionSearchInput: dom.desktopInputs.regionSearchInput,
    minAreaInput: dom.desktopInputs.minAreaInput,
    maxAreaInput: dom.desktopInputs.maxAreaInput,
    rentOnlyFilter: dom.desktopInputs.rentOnlyFilter
  });
  const downloadClient = createDownloadClient();
  const mobileUi = createMobileMapUi({
    desktopInputs: dom.desktopInputs,
    mobileInputs: dom.mobileInputs,
    body: document.body,
    overlay: dom.mobileSearchOverlay,
    history: window.history,
    mediaQueryList: dom.mobileMediaQueryList,
  });
  const selectionController = createMapSelectionController({
    detailPanel,
    filters,
    listPanel,
    mapView,
    state,
    telemetry,
  });

  bindMapPageEvents({
    dom,
    downloadClient,
    filters,
    listPanel,
    mapView,
    mobileUi,
    selectionController,
    sessionTracker,
  });

  await bootstrapMapData({
    listPanel,
    mapView,
    mobileUi,
    selectionController,
  });
}

document.addEventListener("DOMContentLoaded", () => {
  void bootstrap();
});
