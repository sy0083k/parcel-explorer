import type { DownloadClient } from "./download-client";
import type { Filters } from "./filters";
import type { ListPanel } from "./list-panel";
import type { BaseType } from "./types";
import type { MapView } from "./map-view";
import type { MobileMapUi } from "./mobile-map-ui";
import type { MapPageDomRefs } from "./page-dom";
import type { MapSelectionController } from "./selection-controller";
import type { SessionTracker } from "./session-tracker";

type MapPageEventOptions = {
  dom: MapPageDomRefs;
  downloadClient: DownloadClient;
  filters: Pick<Filters, "attachEnter">;
  listPanel: Pick<ListPanel, "bindNavigation" | "initBottomSheet">;
  mapView: Pick<MapView, "changeLayer">;
  mobileUi: Pick<
    MobileMapUi,
    "applyViewportState" | "handlePopState" | "isMobileViewport" | "setState" |
    "syncDesktopToMobileInputs" | "syncMobileToDesktopInputs"
  >;
  selectionController: Pick<MapSelectionController, "applyFilters" | "bindMapInteractions" | "navigateItem" | "resetFilters">;
  sessionTracker: Pick<SessionTracker, "mount">;
};

export function bindMapPageEvents(options: MapPageEventOptions): void {
  const closeLayerPopover = (): void => {
    if (!options.dom.layerPopover || !options.dom.layerToggleBtn) {
      return;
    }
    options.dom.layerPopover.classList.remove("open");
    options.dom.layerPopover.setAttribute("inert", "");
    options.dom.layerToggleBtn.setAttribute("aria-expanded", "false");
  };

  const changeLayerFromMobile = (type: BaseType): void => {
    options.mapView.changeLayer(type);
    closeLayerPopover();
  };

  options.selectionController.bindMapInteractions();

  options.dom.searchBtn?.addEventListener("click", () => options.selectionController.applyFilters(true));
  options.dom.resetFiltersBtn?.addEventListener("click", () => {
    options.selectionController.resetFilters();
    options.mobileUi.syncDesktopToMobileInputs();
  });
  options.dom.downloadAllBtn?.addEventListener("click", () => {
    void options.downloadClient.downloadPreparedFile();
  });
  options.dom.desktopInputs.rentOnlyFilter?.addEventListener("change", () => options.selectionController.applyFilters(false));

  options.dom.desktopBaseBtn?.addEventListener("click", () => options.mapView.changeLayer("Base"));
  options.dom.desktopSatelliteBtn?.addEventListener("click", () => options.mapView.changeLayer("Satellite"));
  options.dom.desktopHybridBtn?.addEventListener("click", () => options.mapView.changeLayer("Hybrid"));

  options.dom.layerToggleBtn?.addEventListener("click", (event) => {
    if (!options.dom.layerPopover || !options.dom.layerToggleBtn) {
      return;
    }
    event.stopPropagation();
    const willOpen = !options.dom.layerPopover.classList.contains("open");
    options.dom.layerPopover.classList.toggle("open", willOpen);
    if (willOpen) {
      options.dom.layerPopover.removeAttribute("inert");
    } else {
      options.dom.layerPopover.setAttribute("inert", "");
    }
    options.dom.layerToggleBtn.setAttribute("aria-expanded", willOpen ? "true" : "false");
  });

  options.dom.mobileBaseBtn?.addEventListener("click", () => changeLayerFromMobile("Base"));
  options.dom.mobileSatelliteBtn?.addEventListener("click", () => changeLayerFromMobile("Satellite"));
  options.dom.mobileHybridBtn?.addEventListener("click", () => changeLayerFromMobile("Hybrid"));

  document.addEventListener("click", (event) => {
    if (
      !options.dom.layerPopover ||
      !options.dom.layerToggleBtn ||
      !(event.target instanceof Node)
    ) {
      return;
    }
    if (!options.dom.layerPopover.contains(event.target) && !options.dom.layerToggleBtn.contains(event.target)) {
      closeLayerPopover();
    }
  });

  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") {
      closeLayerPopover();
    }
  });

  options.listPanel.bindNavigation(
    () => options.selectionController.navigateItem(-1),
    () => options.selectionController.navigateItem(1)
  );

  options.filters.attachEnter(() => options.selectionController.applyFilters(true));
  options.listPanel.initBottomSheet();
  options.sessionTracker.mount();

  options.dom.mobileSearchFab?.addEventListener("click", () => {
    if (!options.mobileUi.isMobileViewport()) {
      return;
    }
    options.mobileUi.syncDesktopToMobileInputs();
    options.mobileUi.setState("search", true);
  });

  options.dom.mobileSearchCloseBtn?.addEventListener("click", () => {
    if (!options.mobileUi.isMobileViewport()) {
      return;
    }
    history.back();
  });

  options.dom.mobileSearchBtn?.addEventListener("click", () => {
    if (!options.mobileUi.isMobileViewport()) {
      return;
    }
    options.mobileUi.syncMobileToDesktopInputs();
    options.selectionController.applyFilters(true);
    options.mobileUi.setState("results", true);
  });

  options.dom.mobileResetBtn?.addEventListener("click", () => {
    options.mobileUi.syncMobileToDesktopInputs();
    options.selectionController.resetFilters();
    options.mobileUi.syncDesktopToMobileInputs();
  });

  options.dom.mobileDownloadBtn?.addEventListener("click", () => {
    void options.downloadClient.downloadPreparedFile();
  });

  window.addEventListener("popstate", (event) => {
    options.mobileUi.handlePopState(event.state);
  });

  options.dom.mobileMediaQueryList.addEventListener("change", () => {
    options.mobileUi.applyViewportState();
  });
}
