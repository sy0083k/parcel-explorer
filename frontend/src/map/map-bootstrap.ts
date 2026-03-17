import { HttpError, fetchJson } from "../http";

import { streamLandFeatures } from "./lands-client";

import type { ListPanel } from "./list-panel";
import type { MapView } from "./map-view";
import type { MobileMapUi } from "./mobile-map-ui";
import type { MapSelectionController } from "./selection-controller";
import type { LandFeature, MapConfig } from "./types";

type BootstrapOptions = {
  listPanel: Pick<ListPanel, "setStatus">;
  mapView: Pick<MapView, "init">;
  mobileUi: Pick<
    MobileMapUi,
    "initHistory" | "isMobileViewport" | "setState" | "syncDesktopToMobileInputs"
  >;
  selectionController: Pick<
    MapSelectionController,
    "appendToOriginalData" | "applyFilters" | "getCurrentIndex" | "setOriginalData"
  >;
  fetchConfig?: () => Promise<MapConfig>;
  loadLandFeatures?: (onBatch: (features: LandFeature[]) => void) => Promise<void>;
};

export async function bootstrapMapData(options: BootstrapOptions): Promise<void> {
  const fetchConfig = options.fetchConfig ?? (() => fetchJson<MapConfig>("/api/config", { timeoutMs: 10000 }));
  const loadLandFeatures = options.loadLandFeatures ?? streamLandFeatures;

  try {
    options.listPanel.setStatus("데이터를 불러오는 중입니다...");
    const config = await fetchConfig();
    options.mapView.init(config);

    const accumulated: LandFeature[] = [];
    let initialRenderDone = false;

    await loadLandFeatures((batch) => {
      accumulated.push(...batch);

      if (!initialRenderDone) {
        initialRenderDone = true;
        options.selectionController.setOriginalData({
          type: "FeatureCollection",
          features: [...accumulated],
        });
        options.selectionController.applyFilters(false);
        options.mobileUi.syncDesktopToMobileInputs();
        options.mobileUi.initHistory();
        if (options.mobileUi.isMobileViewport()) {
          options.mobileUi.setState("home", false);
        }
        return;
      }

      options.selectionController.appendToOriginalData(batch);
    });

    if (options.selectionController.getCurrentIndex() === -1) {
      options.selectionController.setOriginalData({
        type: "FeatureCollection",
        features: accumulated,
      });
      options.selectionController.applyFilters(false);
    }
  } catch (error) {
    const message = error instanceof HttpError ? error.message : "지도를 초기화하지 못했습니다.";
    options.listPanel.setStatus(message, "red");
  }
}
