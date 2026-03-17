import { describe, expect, test, vi } from "vitest";

import { HttpError } from "../http";

import { bootstrapMapData } from "./map-bootstrap";
import type { MapConfig } from "./types";

const TEST_CONFIG: MapConfig = {
  vworldKey: "key",
  center: [126.5, 37.5],
  zoom: 10,
};

describe("bootstrapMapData", () => {
  test("renders first batch immediately and finalizes after all batches", async () => {
    const listPanel = { setStatus: vi.fn() };
    const mapView = { init: vi.fn() };
    const mobileUi = {
      initHistory: vi.fn(),
      isMobileViewport: vi.fn(() => true),
      setState: vi.fn(),
      syncDesktopToMobileInputs: vi.fn(),
    };
    const selectionController = {
      appendToOriginalData: vi.fn(),
      applyFilters: vi.fn(),
      getCurrentIndex: vi.fn(() => -1),
      setOriginalData: vi.fn(),
    };

    await bootstrapMapData({
      listPanel,
      mapView,
      mobileUi,
      selectionController,
      fetchConfig: vi.fn(async () => TEST_CONFIG),
      loadLandFeatures: async (onBatch) => {
        onBatch([{ type: "Feature", geometry: null, properties: { address: "a" } }]);
        onBatch([{ type: "Feature", geometry: null, properties: { address: "b" } }]);
      },
    });

    expect(listPanel.setStatus).toHaveBeenCalledWith("데이터를 불러오는 중입니다...");
    expect(mapView.init).toHaveBeenCalledTimes(1);
    expect(selectionController.setOriginalData).toHaveBeenNthCalledWith(1, {
      type: "FeatureCollection",
      features: [{ type: "Feature", geometry: null, properties: { address: "a" } }],
    });
    expect(selectionController.applyFilters).toHaveBeenNthCalledWith(1, false);
    expect(mobileUi.syncDesktopToMobileInputs).toHaveBeenCalledTimes(1);
    expect(mobileUi.initHistory).toHaveBeenCalledTimes(1);
    expect(mobileUi.setState).toHaveBeenCalledWith("home", false);
    expect(selectionController.appendToOriginalData).toHaveBeenCalledWith([
      { type: "Feature", geometry: null, properties: { address: "b" } },
    ]);
    expect(selectionController.setOriginalData).toHaveBeenNthCalledWith(2, {
      type: "FeatureCollection",
      features: [
        { type: "Feature", geometry: null, properties: { address: "a" } },
        { type: "Feature", geometry: null, properties: { address: "b" } },
      ],
    });
    expect(selectionController.applyFilters).toHaveBeenNthCalledWith(2, false);
  });

  test("shows normalized error message when bootstrap fails", async () => {
    const listPanel = { setStatus: vi.fn() };

    await bootstrapMapData({
      listPanel,
      mapView: { init: vi.fn() },
      mobileUi: {
        initHistory: vi.fn(),
        isMobileViewport: vi.fn(() => false),
        setState: vi.fn(),
        syncDesktopToMobileInputs: vi.fn(),
      },
      selectionController: {
        appendToOriginalData: vi.fn(),
        applyFilters: vi.fn(),
        getCurrentIndex: vi.fn(() => -1),
        setOriginalData: vi.fn(),
      },
      fetchConfig: vi.fn(async () => {
        throw new HttpError("config failed", 500);
      }),
    });

    expect(listPanel.setStatus).toHaveBeenLastCalledWith("config failed", "red");
  });
});
