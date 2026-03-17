import { beforeEach, describe, expect, test, vi } from "vitest";

import { bindMapPageEvents } from "./map-page-events";

function createButton(): HTMLButtonElement {
  return document.createElement("button");
}

function createDiv(): HTMLDivElement {
  return document.createElement("div");
}

function createMediaQueryList(): MediaQueryList {
  return {
    matches: true,
    media: "(max-width: 768px)",
    onchange: null,
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    addListener: vi.fn(),
    removeListener: vi.fn(),
    dispatchEvent: vi.fn(),
  } as unknown as MediaQueryList;
}

describe("bindMapPageEvents", () => {
  beforeEach(() => {
    document.body.className = "";
    document.body.innerHTML = "";
    document.body.style.cssText = "";
  });

  test("binds desktop and mobile actions to controller and clients", async () => {
    const searchBtn = createButton();
    const resetFiltersBtn = createButton();
    const downloadAllBtn = createButton();
    const mobileSearchFab = createButton();
    const mobileSearchCloseBtn = createButton();
    const mobileSearchBtn = createButton();
    const mobileResetBtn = createButton();
    const mobileDownloadBtn = createButton();
    const desktopRentOnly = document.createElement("input");
    desktopRentOnly.type = "checkbox";
    const layerToggleBtn = createButton();
    const layerPopover = createDiv();
    layerPopover.classList.add("open");
    const mobileMediaQueryList = createMediaQueryList();

    const selectionController = {
      applyFilters: vi.fn(),
      bindMapInteractions: vi.fn(),
      navigateItem: vi.fn(),
      resetFilters: vi.fn(),
    };
    const mobileUi = {
      applyViewportState: vi.fn(),
      handlePopState: vi.fn(),
      isMobileViewport: vi.fn(() => true),
      setState: vi.fn(),
      syncDesktopToMobileInputs: vi.fn(),
      syncMobileToDesktopInputs: vi.fn(),
    };
    const downloadClient = {
      downloadPreparedFile: vi.fn(async () => undefined),
    };
    const listPanel = {
      bindNavigation: vi.fn((prev: () => void, next: () => void) => {
        prev();
        next();
      }),
      initBottomSheet: vi.fn(),
    };
    const filters = {
      attachEnter: vi.fn((handler: () => void) => {
        handler();
      }),
    };
    const mapView = {
      changeLayer: vi.fn(),
    };
    const sessionTracker = {
      mount: vi.fn(),
    };

    const historyBackSpy = vi.spyOn(window.history, "back").mockImplementation(() => undefined);

    bindMapPageEvents({
      dom: {
        desktopInputs: {
          regionSearchInput: null,
          minAreaInput: null,
          maxAreaInput: null,
          rentOnlyFilter: desktopRentOnly,
        },
        mobileInputs: {
          regionSearchInput: null,
          minAreaInput: null,
          maxAreaInput: null,
          rentOnlyFilter: null,
        },
        mobileSearchFab,
        mobileSearchCloseBtn,
        mobileSearchBtn,
        mobileResetBtn,
        mobileDownloadBtn,
        mobileSearchOverlay: null,
        layerToggleBtn,
        layerPopover,
        desktopBaseBtn: createButton(),
        desktopSatelliteBtn: createButton(),
        desktopHybridBtn: createButton(),
        mobileBaseBtn: createButton(),
        mobileSatelliteBtn: createButton(),
        mobileHybridBtn: createButton(),
        listContainer: null,
        navInfo: null,
        prevBtn: createButton(),
        nextBtn: createButton(),
        sidebar: null,
        handle: null,
        panel: null,
        panelContent: null,
        panelCloseBtn: null,
        searchBtn,
        resetFiltersBtn,
        downloadAllBtn,
        mobileMediaQueryList,
      },
      downloadClient,
      filters,
      listPanel,
      mapView,
      mobileUi,
      selectionController,
      sessionTracker,
    });

    searchBtn.click();
    resetFiltersBtn.click();
    downloadAllBtn.click();
    desktopRentOnly.dispatchEvent(new Event("change"));
    mobileSearchFab.click();
    mobileSearchBtn.click();
    mobileResetBtn.click();
    mobileDownloadBtn.click();
    mobileSearchCloseBtn.click();
    window.dispatchEvent(new PopStateEvent("popstate", { state: { mobileMapViewState: "home" } }));
    const mediaChangeHandler = vi.mocked(mobileMediaQueryList.addEventListener).mock.calls[0]?.[1];
    if (typeof mediaChangeHandler === "function") {
      mediaChangeHandler(new Event("change"));
    }

    expect(selectionController.bindMapInteractions).toHaveBeenCalledTimes(1);
    expect(selectionController.applyFilters).toHaveBeenCalledWith(true);
    expect(selectionController.applyFilters).toHaveBeenCalledWith(false);
    expect(selectionController.resetFilters).toHaveBeenCalledTimes(2);
    expect(selectionController.navigateItem).toHaveBeenCalledWith(-1);
    expect(selectionController.navigateItem).toHaveBeenCalledWith(1);
    expect(downloadClient.downloadPreparedFile).toHaveBeenCalledTimes(2);
    expect(mobileUi.syncDesktopToMobileInputs).toHaveBeenCalledTimes(3);
    expect(mobileUi.syncMobileToDesktopInputs).toHaveBeenCalledTimes(2);
    expect(mobileUi.setState).toHaveBeenCalledWith("search", true);
    expect(mobileUi.setState).toHaveBeenCalledWith("results", true);
    expect(mobileUi.handlePopState).toHaveBeenCalledWith({ mobileMapViewState: "home" });
    expect(mobileUi.applyViewportState).toHaveBeenCalledTimes(1);
    expect(sessionTracker.mount).toHaveBeenCalledTimes(1);
    expect(historyBackSpy).toHaveBeenCalledTimes(1);
  });
});
