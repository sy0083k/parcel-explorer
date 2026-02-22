import type { LandFeature, LandFeatureCollection } from "./types";

type MapState = {
  originalData: LandFeatureCollection | null;
  currentFeatures: LandFeature[];
  currentIndex: number;
};

export function createMapState() {
  const state: MapState = {
    originalData: null,
    currentFeatures: [],
    currentIndex: -1
  };

  return {
    setOriginalData(data: LandFeatureCollection): void {
      state.originalData = data;
    },
    getOriginalData(): LandFeatureCollection | null {
      return state.originalData;
    },
    setCurrentFeatures(features: LandFeature[]): void {
      state.currentFeatures = features;
      state.currentIndex = -1;
    },
    getCurrentFeatures(): LandFeature[] {
      return state.currentFeatures;
    },
    setCurrentIndex(index: number): void {
      state.currentIndex = index;
    },
    getCurrentIndex(): number {
      return state.currentIndex;
    }
  };
}

export type MapStateStore = ReturnType<typeof createMapState>;
