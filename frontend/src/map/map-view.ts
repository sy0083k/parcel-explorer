import Feature from "ol/Feature";
import GeoJSON from "ol/format/GeoJSON";
import type Geometry from "ol/geom/Geometry";
import { createEmpty, extend, getCenter } from "ol/extent";
import TileLayer from "ol/layer/Tile";
import Map from "ol/Map";
import View from "ol/View";
import { fromLonLat } from "ol/proj";
import XYZ from "ol/source/XYZ";

import type { BaseType, LandFeatureCollection, MapConfig } from "./types";
import { createMapViewStyles } from "./map-view-styles";
import { createMapViewFeatureLayers } from "./map-view-feature-layers";

type FeatureClickPayload = {
  index: number;
  coordinate: number[];
};

type SelectOptions = {
  shouldFit: boolean;
  coordinateOverride?: number[];
};

function asVectorFeature(feature: unknown): Feature<Geometry> | null {
  return feature instanceof Feature ? feature : null;
}

export function createMapView() {
  let map: Map | null = null;
  let baseLayer: TileLayer<XYZ> | null = null;
  let satLayer: TileLayer<XYZ> | null = null;
  let hybLayer: TileLayer<XYZ> | null = null;
  let featureLayers: ReturnType<typeof createMapViewFeatureLayers> | null = null;
  let onFeatureClick: ((payload: FeatureClickPayload) => void) | null = null;
  let onEmptyClick: (() => void) | null = null;

  const init = (config: MapConfig): void => {
    const commonSource = (type: BaseType) =>
      new XYZ({
        url: `https://api.vworld.kr/req/wmts/1.0.0/${config.vworldKey}/${type}/{z}/{y}/{x}.${type === "Satellite" ? "jpeg" : "png"}`,
        crossOrigin: "anonymous"
      });

    baseLayer = new TileLayer({ source: commonSource("Base"), visible: true, zIndex: 0 });
    satLayer = new TileLayer({ source: commonSource("Satellite"), visible: false, zIndex: 0 });
    hybLayer = new TileLayer({ source: commonSource("Hybrid"), visible: false, zIndex: 1 });

    map = new Map({
      target: "map",
      layers: [baseLayer, satLayer, hybLayer],
      view: new View({
        center: fromLonLat(config.center),
        zoom: config.zoom,
        maxZoom: 22,
        minZoom: 7,
        constrainResolution: false
      })
    });

    const reducedMotionMedia = window.matchMedia("(prefers-reduced-motion: reduce)");
    const styles = createMapViewStyles(() => reducedMotionMedia.matches);
    featureLayers = createMapViewFeatureLayers({
      map,
      defaultStyleSelector: styles.defaultStyleSelector,
      selectedStyleSelector: styles.selectedStyleSelector
    });

    map.on("singleclick", (evt) => {
      if (!map) {
        return;
      }

      const clickedFeature = map.forEachFeatureAtPixel(evt.pixel, (item) => item);
      const feature = asVectorFeature(clickedFeature);
      if (!feature) {
        featureLayers?.selectFeatureId(null);
        onEmptyClick?.();
        return;
      }

      const idx = feature.getId();
      if (idx === undefined || onFeatureClick === null) {
        return;
      }

      onFeatureClick({
        index: Number(idx),
        coordinate: evt.coordinate as number[]
      });
    });
  };

  const changeLayer = (type: BaseType): void => {
    if (!map || !baseLayer || !satLayer || !hybLayer) {
      return;
    }

    const view = map.getView();
    const zoomLevel = view.getZoom();
    if (typeof zoomLevel === "number" && zoomLevel >= 20) {
      view.setZoom(19);
    }

    baseLayer.setVisible(type === "Base");
    satLayer.setVisible(type === "Satellite" || type === "Hybrid");
    hybLayer.setVisible(type === "Hybrid");

    document
      .querySelectorAll(".map-controls .layer-desktop, .map-controls .layer-popover button")
      .forEach((btn) => btn.classList.remove("active"));
    document.getElementById(`btn-${type}`)?.classList.add("active");
    document.getElementById(`m-btn-${type}`)?.classList.add("active");
  };

  const renderFeatures = (data: LandFeatureCollection): void => {
    if (!map || !featureLayers) {
      return;
    }

    const parsed = new GeoJSON().readFeatures(data, {
      featureProjection: "EPSG:3857"
    }) as Feature<Geometry>[];

    const next = new globalThis.Map<number, Feature<Geometry>>();
    parsed.forEach((feature, idx) => {
      feature.setId(idx);
      next.set(idx, feature);
    });

    featureLayers.setFeatures(next);
  };

  const fitToFeatures = (): void => {
    if (!map || !featureLayers) {
      return;
    }

    const allFeatures = [...featureLayers.getAllFeatures()];
    if (allFeatures.length === 0) {
      return;
    }

    const extent = createEmpty();
    allFeatures.forEach((f) => {
      const geom = f.getGeometry();
      if (geom) {
        extend(extent, geom.getExtent());
      }
    });

    map.getView().fit(extent, { padding: [50, 50, 50, 50], duration: 500 });
  };

  const selectFeatureByIndex = (index: number, options: SelectOptions): boolean => {
    if (!featureLayers || !map) {
      return false;
    }

    const feature = featureLayers.getFeatureById(index);
    if (!feature) {
      return false;
    }

    featureLayers.selectFeatureId(index);

    const geometry = feature.getGeometry();
    if (!geometry) {
      return false;
    }

    const extent = geometry.getExtent();
    const focusCoord = getCenter(extent);

    if (options.shouldFit) {
      const view = map.getView();
      const [minX, minY, maxX, maxY] = extent;
      const isPointLike = minX === maxX && minY === maxY;
      if (isPointLike) {
        view.animate({
          center: focusCoord,
          duration: 300
        });
        const zoomLevel = view.getZoom();
        if (typeof zoomLevel === "number" && zoomLevel < 19) {
          view.setZoom(19);
        }
      } else {
        view.fit(extent, {
          padding: [100, 100, 100, 100],
          duration: 300,
          maxZoom: 19
        });
      }
    }

    if (options.shouldFit) {
      window.setTimeout(() => {
        map?.getView().animate({ center: focusCoord, duration: 120 });
      }, 220);
    }

    return true;
  };

  const clearPopup = (): void => {
    featureLayers?.selectFeatureId(null);
  };

  const setFeatureClickHandler = (handler: (payload: FeatureClickPayload) => void): void => {
    onFeatureClick = handler;
  };

  const setEmptyClickHandler = (handler: () => void): void => {
    onEmptyClick = handler;
  };

  return {
    changeLayer,
    clearPopup,
    fitToFeatures,
    init,
    renderFeatures,
    selectFeatureByIndex,
    setFeatureClickHandler,
    setEmptyClickHandler
  };
}

export type MapView = ReturnType<typeof createMapView>;
