import Feature from "ol/Feature";
import type Geometry from "ol/geom/Geometry";
import VectorLayer from "ol/layer/Vector";
import type Map from "ol/Map";
import VectorSource from "ol/source/Vector";
import type Style from "ol/style/Style";

type LayerDeps = {
  map: Map;
  defaultStyleSelector: (feature: Feature<Geometry>) => Style;
  selectedStyleSelector: (feature: Feature<Geometry>) => Style[];
};

const selectionPulseTickMs = 100;

export function createMapViewFeatureLayers(deps: LayerDeps) {
  let parcels: VectorLayer<VectorSource<Feature<Geometry>>> | null = null;
  let parcelsSelected: VectorLayer<VectorSource<Feature<Geometry>>> | null = null;
  let selectedFeatureId: number | null = null;
  let featuresById = new globalThis.Map<number, Feature<Geometry>>();
  let selectionPulseTimerId: number | null = null;
  const reducedMotionMedia = window.matchMedia("(prefers-reduced-motion: reduce)");

  const stopSelectionPulse = (): void => {
    if (selectionPulseTimerId === null) {
      return;
    }
    window.clearInterval(selectionPulseTimerId);
    selectionPulseTimerId = null;
  };

  const startSelectionPulse = (): void => {
    if (selectionPulseTimerId !== null || !parcelsSelected) {
      return;
    }
    selectionPulseTimerId = window.setInterval(() => {
      parcelsSelected?.changed();
    }, selectionPulseTickMs);
  };

  const syncSelectionPulseState = (): void => {
    if (selectedFeatureId === null || reducedMotionMedia.matches) {
      stopSelectionPulse();
      return;
    }
    startSelectionPulse();
  };

  const ensureLayers = (): void => {
    if (!parcels) {
      parcels = new VectorLayer({
        properties: { name: 'parcels' },
        source: new VectorSource<Feature<Geometry>>(),
        zIndex: 10,
        style: deps.defaultStyleSelector
      });
      deps.map.addLayer(parcels);
    }
    if (!parcelsSelected) {
      parcelsSelected = new VectorLayer({
        properties: { name: 'parcels-selected' },
        source: new VectorSource<Feature<Geometry>>(),
        zIndex: 11,
        style: deps.selectedStyleSelector
      });
      deps.map.addLayer(parcelsSelected);
    }
  };

  const getSources = ():
    | {
        baseSource: VectorSource<Feature<Geometry>>;
        selectedSource: VectorSource<Feature<Geometry>>;
      }
    | null => {
    ensureLayers();
    const baseSource = parcels?.getSource();
    const selectedSource = parcelsSelected?.getSource();
    if (!baseSource || !selectedSource) {
      return null;
    }
    return { baseSource, selectedSource };
  };

  const addFeatureToActiveSource = (
    featureId: number,
    feature: Feature<Geometry>,
    sources: {
      baseSource: VectorSource<Feature<Geometry>>;
      selectedSource: VectorSource<Feature<Geometry>>;
    }
  ): void => {
    if (selectedFeatureId !== null && featureId === selectedFeatureId) {
      sources.selectedSource.addFeature(feature);
      return;
    }
    sources.baseSource.addFeature(feature);
  };

  const removeFeatureFromSources = (
    feature: Feature<Geometry>,
    sources: {
      baseSource: VectorSource<Feature<Geometry>>;
      selectedSource: VectorSource<Feature<Geometry>>;
    }
  ): void => {
    sources.baseSource.removeFeature(feature);
    sources.selectedSource.removeFeature(feature);
  };

  const setFeatures = (next: globalThis.Map<number, Feature<Geometry>>): void => {
    const sources = getSources();
    if (!sources) {
      featuresById = next;
      return;
    }

    for (const [featureId, existingFeature] of featuresById.entries()) {
      const nextFeature = next.get(featureId);
      if (!nextFeature || nextFeature !== existingFeature) {
        removeFeatureFromSources(existingFeature, sources);
      }
    }

    for (const [featureId, nextFeature] of next.entries()) {
      const existingFeature = featuresById.get(featureId);
      if (!existingFeature || existingFeature !== nextFeature) {
        addFeatureToActiveSource(featureId, nextFeature, sources);
      }
    }

    featuresById = next;
    if (selectedFeatureId !== null && !featuresById.has(selectedFeatureId)) {
      selectedFeatureId = null;
    }
    syncSelectionPulseState();
  };

  const selectFeatureId = (featureId: number | null): void => {
    if (selectedFeatureId === featureId) {
      return;
    }
    const sources = getSources();
    if (!sources) {
      selectedFeatureId = featureId;
      return;
    }

    if (selectedFeatureId !== null) {
      const previousFeature = featuresById.get(selectedFeatureId);
      if (previousFeature) {
        sources.selectedSource.removeFeature(previousFeature);
        sources.baseSource.addFeature(previousFeature);
      }
    }

    selectedFeatureId = featureId;
    if (selectedFeatureId !== null) {
      const nextFeature = featuresById.get(selectedFeatureId);
      if (nextFeature) {
        sources.baseSource.removeFeature(nextFeature);
        sources.selectedSource.addFeature(nextFeature);
      } else {
        selectedFeatureId = null;
      }
    }
    syncSelectionPulseState();
  };

  const getFeatureById = (id: number): Feature<Geometry> | null =>
    featuresById.get(id) ?? null;

  const getAllFeatures = (): Iterable<Feature<Geometry>> => featuresById.values();

  const refreshTheme = (): void => {
    parcels?.changed();
    parcelsSelected?.changed();
  };

  ensureLayers();
  reducedMotionMedia.addEventListener("change", () => syncSelectionPulseState());

  return {
    getAllFeatures,
    getFeatureById,
    refreshTheme,
    selectFeatureId,
    setFeatures
  };
}
