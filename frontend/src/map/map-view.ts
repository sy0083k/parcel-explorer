import Feature from "ol/Feature";
import GeoJSON from "ol/format/GeoJSON";
import type Geometry from "ol/geom/Geometry";
import Overlay from "ol/Overlay";
import TileLayer from "ol/layer/Tile";
import VectorLayer from "ol/layer/Vector";
import Map from "ol/Map";
import View from "ol/View";
import { getCenter } from "ol/extent";
import { fromLonLat } from "ol/proj";
import VectorSource from "ol/source/Vector";
import XYZ from "ol/source/XYZ";
import Fill from "ol/style/Fill";
import Stroke from "ol/style/Stroke";
import Style from "ol/style/Style";

import type { BaseType, LandFeatureCollection, LandFeatureProperties, MapConfig } from "./types";

type MapViewElements = {
  popupElement: HTMLElement;
  popupContent: HTMLElement;
  popupCloser: HTMLElement | null;
};

type FeatureClickPayload = {
  index: number;
  coordinate: number[];
};

type SelectOptions = {
  shouldFit: boolean;
  coordinateOverride?: number[];
  panIntoView?: boolean;
};

function asVectorFeature(feature: unknown): Feature<Geometry> | null {
  return feature instanceof Feature ? feature : null;
}

function readCssVar(name: string, fallback: string): string {
  const value = getComputedStyle(document.documentElement).getPropertyValue(name).trim();
  return value || fallback;
}

export function createMapView(elements: MapViewElements) {
  let map: Map | null = null;
  let baseLayer: TileLayer<XYZ> | null = null;
  let satLayer: TileLayer<XYZ> | null = null;
  let hybLayer: TileLayer<XYZ> | null = null;
  let vectorLayer: VectorLayer<VectorSource<Feature<Geometry>>> | null = null;
  let onFeatureClick: ((payload: FeatureClickPayload) => void) | null = null;

  const overlay = new Overlay({ element: elements.popupElement, autoPan: false });

  elements.popupCloser?.addEventListener("click", (event: Event) => {
    event.preventDefault();
    overlay.setPosition(undefined);
  });

  const showPopup = (feature: Feature<Geometry>, coordinate: number[], panIntoView = false): void => {
    const props = feature.getProperties() as LandFeatureProperties;
    elements.popupContent.replaceChildren();

    const rows = [
      ["📍 주소", props.address],
      ["📏 면적", `${props.area}㎡`],
      ["📂 지목", props.land_type],
      ["📞 문의", props.contact]
    ];

    rows.forEach(([label, value]) => {
      const line = document.createElement("div");
      line.textContent = `${label}: ${value || ""}`;
      elements.popupContent.appendChild(line);
    });

    overlay.setPosition(coordinate);
    if (panIntoView) {
      overlay.panIntoView({ animation: { duration: 250 } });
    }
  };

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
      overlays: [overlay],
      view: new View({
        center: fromLonLat(config.center),
        zoom: config.zoom,
        maxZoom: 22,
        minZoom: 7,
        constrainResolution: false
      })
    });

    map.on("singleclick", (evt) => {
      if (!map) {
        return;
      }

      const clickedFeature = map.forEachFeatureAtPixel(evt.pixel, (item) => item);
      const feature = asVectorFeature(clickedFeature);
      if (!feature) {
        overlay.setPosition(undefined);
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
    if (!map) {
      return;
    }

    if (vectorLayer) {
      map.removeLayer(vectorLayer);
    }

    const vectorSource = new VectorSource<Feature<Geometry>>();
    const parsed = new GeoJSON().readFeatures(data, {
      featureProjection: "EPSG:3857"
    }) as Feature<Geometry>[];

    parsed.forEach((feature, idx) => {
      feature.setId(idx);
      vectorSource.addFeature(feature);
    });

    vectorLayer = new VectorLayer({
      source: vectorSource,
      zIndex: 10,
      style: new Style({
        stroke: new Stroke({ color: readCssVar("--color-map-stroke", "#ff3333"), width: 3 }),
        fill: new Fill({ color: readCssVar("--color-map-fill", "rgba(52, 152, 219, 0.18)") })
      })
    });

    map.addLayer(vectorLayer);
  };

  const fitToFeatures = (): void => {
    const source = vectorLayer?.getSource();
    if (!source || !map || source.getFeatures().length === 0) {
      return;
    }

    map.getView().fit(source.getExtent(), { padding: [50, 50, 50, 50], duration: 500 });
  };

  const selectFeatureByIndex = (index: number, options: SelectOptions): boolean => {
    if (!vectorLayer || !map) {
      return false;
    }

    const feature = vectorLayer.getSource()?.getFeatureById(index) as Feature<Geometry> | null;
    if (!feature) {
      return false;
    }

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

    const popupCoordinate = options.coordinateOverride ?? focusCoord;
    showPopup(feature, popupCoordinate, Boolean(options.panIntoView));

    if (options.shouldFit) {
      window.setTimeout(() => {
        map?.getView().animate({ center: focusCoord, duration: 120 });
      }, 220);
    }

    return true;
  };

  const clearPopup = (): void => {
    overlay.setPosition(undefined);
  };

  const setFeatureClickHandler = (handler: (payload: FeatureClickPayload) => void): void => {
    onFeatureClick = handler;
  };

  return {
    changeLayer,
    clearPopup,
    fitToFeatures,
    init,
    renderFeatures,
    selectFeatureByIndex,
    setFeatureClickHandler
  };
}

export type MapView = ReturnType<typeof createMapView>;
