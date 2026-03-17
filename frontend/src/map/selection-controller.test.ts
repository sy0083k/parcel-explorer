import { describe, expect, test, vi } from "vitest";

import { createMapSelectionController } from "./selection-controller";
import type { LandFeature, LandFeatureCollection } from "./types";

const FEATURE_A: LandFeature = { type: "Feature", geometry: null, properties: { address: "a" } };
const FEATURE_B: LandFeature = { type: "Feature", geometry: null, properties: { address: "b", id: 2 } };
const FEATURE_COLLECTION: LandFeatureCollection = {
  type: "FeatureCollection",
  features: [FEATURE_A],
};

describe("createMapSelectionController", () => {
  test("tracks search telemetry and renders filtered collection", () => {
    const listPanel = {
      bindNavigation: vi.fn(),
      initBottomSheet: vi.fn(),
      render: vi.fn(),
      scrollTo: vi.fn(),
      setStatus: vi.fn(),
      updateNavigation: vi.fn(),
    };
    const mapView = {
      changeLayer: vi.fn(),
      clearPopup: vi.fn(),
      fitToFeatures: vi.fn(),
      init: vi.fn(),
      renderFeatures: vi.fn(),
      selectFeatureByIndex: vi.fn(() => true),
      setEmptyClickHandler: vi.fn(),
      setFeatureClickHandler: vi.fn(),
    };
    const telemetry = {
      getOrCreateAnonId: vi.fn(),
      postWebEvent: vi.fn(),
      trackLandClickEvent: vi.fn(),
      trackSearchEvent: vi.fn(),
    };
    const controller = createMapSelectionController({
      detailPanel: {
        bindCloseButton: vi.fn(),
        clear: vi.fn(),
        dismiss: vi.fn(),
        renderProperties: vi.fn(),
        show: vi.fn(),
      },
      filters: {
        attachEnter: vi.fn(),
        filterFeatures: vi.fn(() => [FEATURE_A]),
        getValues: vi.fn(() => ({
          isRentOnly: true,
          maxArea: 100,
          minArea: 10,
          rawMaxAreaInput: "100",
          rawMinAreaInput: "10",
          rawSearchTerm: "대산읍",
          searchTerm: "대산읍",
        })),
        reset: vi.fn(),
      },
      listPanel,
      mapView,
      state: {
        appendToOriginalData: vi.fn(),
        getCurrentFeatures: vi.fn(() => []),
        getCurrentIndex: vi.fn(() => -1),
        getOriginalData: vi.fn(() => FEATURE_COLLECTION),
        setCurrentFeatures: vi.fn(),
        setCurrentIndex: vi.fn(),
        setOriginalData: vi.fn(),
      },
      telemetry,
    });

    controller.applyFilters(true);

    expect(telemetry.trackSearchEvent).toHaveBeenCalledWith(10, "대산읍", "대산읍", "10", "100", "true");
    expect(mapView.renderFeatures).toHaveBeenCalledWith(FEATURE_COLLECTION);
    expect(listPanel.render).toHaveBeenCalledTimes(1);
  });

  test("shows detail panel for map click and dismisses on nav", () => {
    const detailPanel = {
      bindCloseButton: vi.fn(),
      clear: vi.fn(),
      dismiss: vi.fn(),
      renderProperties: vi.fn(),
      show: vi.fn(),
    };
    const currentFeatures: LandFeature[] = [
      { type: "Feature", geometry: null, properties: { address: "a", id: 1 } },
      FEATURE_B,
    ];

    const controller = createMapSelectionController({
      detailPanel,
      filters: {
        attachEnter: vi.fn(),
        filterFeatures: vi.fn(),
        getValues: vi.fn(),
        reset: vi.fn(),
      },
      listPanel: {
        bindNavigation: vi.fn(),
        initBottomSheet: vi.fn(),
        render: vi.fn(),
        scrollTo: vi.fn(),
        setStatus: vi.fn(),
        updateNavigation: vi.fn(),
      },
      mapView: {
        changeLayer: vi.fn(),
        clearPopup: vi.fn(),
        fitToFeatures: vi.fn(),
        init: vi.fn(),
        renderFeatures: vi.fn(),
        selectFeatureByIndex: vi.fn(() => true),
        setEmptyClickHandler: vi.fn(),
        setFeatureClickHandler: vi.fn(),
      },
      state: {
        appendToOriginalData: vi.fn(),
        getCurrentFeatures: vi.fn(() => currentFeatures),
        getCurrentIndex: vi.fn(() => 1),
        getOriginalData: vi.fn(() => null),
        setCurrentFeatures: vi.fn(),
        setCurrentIndex: vi.fn(),
        setOriginalData: vi.fn(),
      },
      telemetry: {
        getOrCreateAnonId: vi.fn(),
        postWebEvent: vi.fn(),
        trackLandClickEvent: vi.fn(),
        trackSearchEvent: vi.fn(),
      },
    });

    controller.selectItem(0, { shouldFit: false, clickSource: "map_click", coordinateOverride: [1, 2] });
    controller.selectItem(1, { shouldFit: true, clickSource: "nav_next" });

    expect(detailPanel.renderProperties).toHaveBeenCalledWith(currentFeatures[0].properties);
    expect(detailPanel.show).toHaveBeenCalledTimes(1);
    expect(detailPanel.dismiss).toHaveBeenCalledTimes(1);
  });
});
