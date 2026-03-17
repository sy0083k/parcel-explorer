import type { DetailPanel } from "./detail-panel";
import type { Filters } from "./filters";
import type { ListPanel } from "./list-panel";
import type { MapView } from "./map-view";
import type { MapStateStore } from "./state";
import type { Telemetry } from "./telemetry";
import type { LandClickSource, LandFeatureCollection } from "./types";

type SelectOptions = {
  shouldFit: boolean;
  clickSource?: LandClickSource;
  coordinateOverride?: number[];
};

type SelectionControllerOptions = {
  detailPanel: DetailPanel;
  filters: Filters;
  listPanel: ListPanel;
  mapView: MapView;
  state: MapStateStore;
  telemetry: Telemetry;
};

export function createMapSelectionController(options: SelectionControllerOptions) {
  const updateNavigation = (): void => {
    options.listPanel.updateNavigation(
      options.state.getCurrentIndex(),
      options.state.getCurrentFeatures().length
    );
  };

  const selectItem = (index: number, selection: SelectOptions): void => {
    const currentFeatures = options.state.getCurrentFeatures();
    if (index < 0 || index >= currentFeatures.length) {
      return;
    }

    options.state.setCurrentIndex(index);

    if (selection.clickSource) {
      const selected = currentFeatures[index];
      options.telemetry.trackLandClickEvent(
        selected?.properties.address || "",
        selection.clickSource,
        selected?.properties.id
      );
    }

    options.mapView.selectFeatureByIndex(index, {
      shouldFit: selection.shouldFit,
      coordinateOverride: selection.coordinateOverride,
    });

    if (selection.clickSource === "map_click") {
      const selected = currentFeatures[index];
      if (selected) {
        options.detailPanel.renderProperties(selected.properties);
        options.detailPanel.show();
      }
    } else if (selection.clickSource === "nav_prev" || selection.clickSource === "nav_next") {
      options.detailPanel.dismiss();
    }

    updateNavigation();
    options.listPanel.scrollTo(index);
  };

  const renderCollection = (data: LandFeatureCollection): void => {
    options.state.setCurrentFeatures(data.features);
    options.mapView.renderFeatures(data);
    options.listPanel.render(data.features, (idx) => {
      selectItem(idx, { shouldFit: true, clickSource: "list_click" });
    });

    if (data.features.length > 0) {
      options.mapView.fitToFeatures();
    }

    updateNavigation();
  };

  const applyFilters = (trackEvent = false): void => {
    const originalData = options.state.getOriginalData();
    if (!originalData) {
      return;
    }

    const values = options.filters.getValues();
    const filteredFeatures = options.filters.filterFeatures(originalData.features, values);

    if (trackEvent) {
      options.telemetry.trackSearchEvent(
        values.minArea,
        values.searchTerm,
        values.rawSearchTerm,
        values.rawMinAreaInput,
        values.rawMaxAreaInput,
        String(values.isRentOnly)
      );
    }

    renderCollection({ type: "FeatureCollection", features: filteredFeatures });
  };

  const resetFilters = (): void => {
    options.filters.reset();
    options.mapView.clearPopup();
    options.detailPanel.dismiss();
    applyFilters(false);
  };

  const navigateItem = (direction: number): void => {
    const nextIndex = options.state.getCurrentIndex() + direction;
    if (nextIndex < 0 || nextIndex >= options.state.getCurrentFeatures().length) {
      return;
    }

    selectItem(nextIndex, {
      shouldFit: true,
      clickSource: direction < 0 ? "nav_prev" : "nav_next",
    });
  };

  const bindMapInteractions = (): void => {
    options.mapView.setFeatureClickHandler(({ index, coordinate }) => {
      selectItem(index, {
        shouldFit: false,
        clickSource: "map_click",
        coordinateOverride: coordinate,
      });
    });

    options.mapView.setEmptyClickHandler(() => {
      options.detailPanel.dismiss();
    });
  };

  return {
    appendToOriginalData(features: LandFeatureCollection["features"]): void {
      options.state.appendToOriginalData(features);
    },
    applyFilters,
    bindMapInteractions,
    getCurrentIndex(): number {
      return options.state.getCurrentIndex();
    },
    navigateItem,
    renderCollection,
    resetFilters,
    selectItem,
    setOriginalData(data: LandFeatureCollection): void {
      options.state.setOriginalData(data);
    },
  };
}

export type MapSelectionController = ReturnType<typeof createMapSelectionController>;
