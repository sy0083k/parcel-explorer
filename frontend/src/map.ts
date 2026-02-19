import "ol/ol.css";
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

import { HttpError, fetchJson } from "./http";

type MapConfig = {
  vworldKey: string;
  center: [number, number];
  zoom: number;
};

type LandFeatureProperties = {
  id?: number;
  address?: string;
  land_type?: string;
  area?: number;
  adm_property?: string;
  gen_property?: string;
  contact?: string;
};

type LandFeature = {
  type: "Feature";
  geometry: unknown;
  properties: LandFeatureProperties;
};

type LandFeatureCollection = {
  type: "FeatureCollection";
  features: LandFeature[];
};

type LandsPageResponse = LandFeatureCollection & {
  nextCursor: string | null;
};

type BaseType = "Base" | "Satellite" | "Hybrid";

let map: Map | null = null;
let baseLayer: TileLayer<XYZ> | null = null;
let satLayer: TileLayer<XYZ> | null = null;
let hybLayer: TileLayer<XYZ> | null = null;
let vectorLayer: VectorLayer<VectorSource<Feature<Geometry>>> | null = null;
let originalData: LandFeatureCollection | null = null;
let currentFeaturesData: LandFeature[] = [];
let currentIndex = -1;
let overlay: Overlay | null = null;
let content: HTMLElement | null = null;
let regionSearchInput: HTMLInputElement | null = null;

let startY = 0;
let startHeight = 0;
const sidebar = document.getElementById("sidebar");
const handle = document.querySelector(".mobile-handle");
const snapHeights = {
  collapsed: 0.15,
  mid: 0.4,
  expanded: 0.85
};

function asVectorFeature(feature: unknown): Feature<Geometry> | null {
  return feature instanceof Feature ? feature : null;
}

function setListStatus(message: string, color = "#999"): void {
  const listArea = document.getElementById("list-container");
  if (!listArea) {
    return;
  }

  const status = document.createElement("p");
  status.style.padding = "20px";
  status.style.color = color;
  status.textContent = message;
  listArea.replaceChildren(status);
}

function initMap(key: string, center: [number, number], zoom: number): void {
  const commonSource = (type: BaseType) =>
    new XYZ({
      url: `https://api.vworld.kr/req/wmts/1.0.0/${key}/${type}/{z}/{y}/{x}.${type === "Satellite" ? "jpeg" : "png"}`,
      crossOrigin: "anonymous"
    });

  baseLayer = new TileLayer({ source: commonSource("Base"), visible: true, zIndex: 0 });
  satLayer = new TileLayer({ source: commonSource("Satellite"), visible: false, zIndex: 0 });
  hybLayer = new TileLayer({ source: commonSource("Hybrid"), visible: false, zIndex: 1 });

  map = new Map({
    target: "map",
    layers: [baseLayer, satLayer, hybLayer],
    overlays: overlay ? [overlay] : [],
    view: new View({
      center: fromLonLat(center),
      zoom,
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
    if (feature) {
      const idx = feature.getId();
      if (idx !== undefined) {
        selectItem(Number(idx), false);
      }
      showPopup(feature, evt.coordinate as number[], true);
    } else {
      overlay?.setPosition(undefined);
    }
  });
}

function changeLayer(type: BaseType): void {
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

  document.querySelectorAll(".map-controls button").forEach((btn) => btn.classList.remove("active"));
  document.getElementById(`btn-${type}`)?.classList.add("active");
}

async function loadLandData(): Promise<void> {
  const allFeatures: LandFeature[] = [];
  let cursor: string | null = null;

  setListStatus("데이터를 불러오는 중입니다...");

  while (true) {
    const query = new URLSearchParams({ limit: "500" });
    if (cursor) {
      query.set("cursor", cursor);
    }

    const page = await fetchJson<LandsPageResponse>(`/api/lands?${query.toString()}`, { timeoutMs: 20000 });
    allFeatures.push(...page.features);

    if (!page.nextCursor) {
      break;
    }
    cursor = page.nextCursor;
  }

  originalData = { type: "FeatureCollection", features: allFeatures };
  applyFilters();
}

function applyFilters(): void {
  if (!originalData || !regionSearchInput) {
    return;
  }

  const rentOnlyFilter = document.getElementById("rent-only-filter") as HTMLInputElement | null;
  const minAreaInput = document.getElementById("min-area") as HTMLInputElement | null;
  const maxAreaInput = document.getElementById("max-area") as HTMLInputElement | null;

  const isRentOnly = Boolean(rentOnlyFilter?.checked);
  const searchTerm = regionSearchInput.value.trim();
  const minArea = Number.parseFloat(minAreaInput?.value || "") || 0;
  const maxArea = Number.parseFloat(maxAreaInput?.value || "") || Number.POSITIVE_INFINITY;

  const filteredFeatures = originalData.features.filter((feature) => {
    const p = feature.properties;
    const address = p.address || "";
    const area = p.area || 0;

    const matchRegion = searchTerm === "" || address.includes(searchTerm);
    const matchArea = area >= minArea && area <= maxArea;

    let matchRent = true;
    if (isRentOnly) {
      const isAdmRentable = (p.adm_property || "").toLowerCase() === "o";
      const isGenRentable = (p.gen_property || "").startsWith("대부");
      matchRent = isAdmRentable || isGenRentable;
    }

    return matchRegion && matchArea && matchRent;
  });

  updateMapAndList({ type: "FeatureCollection", features: filteredFeatures });
}

function updateMapAndList(data: LandFeatureCollection): void {
  if (!map) {
    return;
  }

  currentFeaturesData = data.features;
  currentIndex = -1;

  if (vectorLayer) {
    map.removeLayer(vectorLayer);
  }

  const vectorSource = new VectorSource<Feature<Geometry>>();
  const parsedFeatures = new GeoJSON().readFeatures(data, { featureProjection: "EPSG:3857" }) as Feature<Geometry>[];

  parsedFeatures.forEach((feature, idx) => {
    feature.setId(idx);
    vectorSource.addFeature(feature);
  });

  vectorLayer = new VectorLayer({
    source: vectorSource,
    zIndex: 10,
    style: new Style({
      stroke: new Stroke({ color: "#ff3333", width: 3 }),
      fill: new Fill({ color: "rgba(255, 51, 51, 0.2)" })
    })
  });
  map.addLayer(vectorLayer);

  const listArea = document.getElementById("list-container");
  if (!listArea) {
    return;
  }
  listArea.replaceChildren();

  if (!data.features.length) {
    setListStatus("결과 없음", "red");
  }

  data.features.forEach((feature, idx) => {
    const item = document.createElement("div");
    item.className = "list-item";
    item.id = `item-${idx}`;

    const title = document.createElement("strong");
    title.textContent = feature.properties.address || "";

    const lineBreak = document.createElement("br");

    const desc = document.createElement("small");
    desc.textContent = `${feature.properties.land_type || ""} | ${feature.properties.area || ""}㎡`;

    item.appendChild(title);
    item.appendChild(lineBreak);
    item.appendChild(desc);
    item.addEventListener("click", () => selectItem(idx));
    listArea.appendChild(item);
  });

  if (data.features.length > 0) {
    map.getView().fit(vectorSource.getExtent(), { padding: [50, 50, 50, 50], duration: 500 });
  }

  updateNavigationUI();
}

function selectItem(idx: number, shouldFit = true): void {
  if (!vectorLayer || !map || idx < 0 || idx >= currentFeaturesData.length) {
    return;
  }

  currentIndex = idx;
  const feature = vectorLayer.getSource()?.getFeatureById(idx) as Feature<Geometry> | null;

  if (feature) {
    const geometry = feature.getGeometry();
    if (geometry) {
      const extent = geometry.getExtent();
      const focusCoord = getCenter(extent);

      if (shouldFit) {
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

      showPopup(feature, focusCoord, false);
      if (shouldFit) {
        window.setTimeout(() => {
          map?.getView().animate({ center: focusCoord, duration: 120 });
        }, 220);
      }
    }
  }

  updateNavigationUI();

  const selectedEl = document.getElementById(`item-${idx}`);
  if (selectedEl) {
    selectedEl.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }
}

function showPopup(feature: Feature<Geometry>, coordinate: number[], panIntoView = false): void {
  if (!content || !overlay) {
    return;
  }

  const props = feature.getProperties() as LandFeatureProperties;
  content.replaceChildren();

  const rows = [
    ["📍 주소", props.address],
    ["📏 면적", `${props.area}㎡`],
    ["📂 지목", props.land_type],
    ["📞 문의", props.contact]
  ];

  rows.forEach(([label, value]) => {
    const line = document.createElement("div");
    line.textContent = `${label}: ${value || ""}`;
    content?.appendChild(line);
  });

  overlay.setPosition(coordinate);
  if (panIntoView) {
    overlay.panIntoView({ animation: { duration: 250 } });
  }
}

function navigateItem(direction: number): void {
  const nextIdx = currentIndex + direction;
  if (nextIdx >= 0 && nextIdx < currentFeaturesData.length) {
    selectItem(nextIdx);
  }
}

function updateNavigationUI(): void {
  const total = currentFeaturesData.length;
  const navInfo = document.getElementById("nav-info");
  const prevBtn = document.getElementById("prev-btn") as HTMLButtonElement | null;
  const nextBtn = document.getElementById("next-btn") as HTMLButtonElement | null;

  if (navInfo) {
    navInfo.innerText = total > 0 ? `${currentIndex + 1} / ${total}` : "0 / 0";
  }

  if (prevBtn) {
    prevBtn.disabled = currentIndex <= 0;
  }
  if (nextBtn) {
    nextBtn.disabled = currentIndex >= total - 1 || total === 0;
  }

  document.querySelectorAll(".list-item").forEach((item, idx) => {
    item.classList.toggle("selected", idx === currentIndex);
  });
}

function initBottomSheet(): void {
  if (!handle || !sidebar) {
    return;
  }

  handle.addEventListener("touchstart", (event: TouchEvent) => {
    startY = event.touches[0].clientY;
    startHeight = sidebar.offsetHeight;
    (sidebar as HTMLElement).style.transition = "none";
  });

  handle.addEventListener("touchmove", (event: TouchEvent) => {
    const touchY = event.touches[0].clientY;
    const deltaY = startY - touchY;
    const newHeight = startHeight + deltaY;

    if (newHeight > window.innerHeight * 0.12 && newHeight < window.innerHeight * 0.9) {
      (sidebar as HTMLElement).style.height = `${newHeight}px`;
    }
  });

  handle.addEventListener("touchend", () => {
    (sidebar as HTMLElement).style.transition = "height 0.3s ease-out";
    const currentRatio = sidebar.clientHeight / window.innerHeight;
    if (currentRatio >= 0.6) {
      (sidebar as HTMLElement).style.height = `${snapHeights.expanded * 100}vh`;
    } else if (currentRatio <= 0.25) {
      (sidebar as HTMLElement).style.height = `${snapHeights.collapsed * 100}vh`;
    } else {
      (sidebar as HTMLElement).style.height = `${snapHeights.mid * 100}vh`;
    }
  });
}

async function bootstrap(): Promise<void> {
  regionSearchInput = document.getElementById("region-search") as HTMLInputElement | null;
  const popupElement = document.getElementById("popup");
  content = document.getElementById("popup-content");
  const closer = document.getElementById("popup-closer");

  if (!popupElement || !content) {
    return;
  }

  overlay = new Overlay({ element: popupElement, autoPan: false });

  if (closer) {
    closer.addEventListener("click", (event) => {
      event.preventDefault();
      overlay?.setPosition(undefined);
    });
  }

  document.getElementById("btn-search")?.addEventListener("click", applyFilters);
  const rentOnlyFilter = document.getElementById("rent-only-filter");
  rentOnlyFilter?.addEventListener("change", applyFilters);
  document.getElementById("btn-Base")?.addEventListener("click", () => changeLayer("Base"));
  document.getElementById("btn-Satellite")?.addEventListener("click", () => changeLayer("Satellite"));
  document.getElementById("btn-Hybrid")?.addEventListener("click", () => changeLayer("Hybrid"));
  document.getElementById("prev-btn")?.addEventListener("click", () => navigateItem(-1));
  document.getElementById("next-btn")?.addEventListener("click", () => navigateItem(1));

  if (regionSearchInput) {
    regionSearchInput.addEventListener("keydown", (event: KeyboardEvent) => {
      if (event.key === "Enter") {
        event.preventDefault();
        applyFilters();
      }
    });
  }

  initBottomSheet();

  try {
    const config = await fetchJson<MapConfig>("/api/config", { timeoutMs: 10000 });
    initMap(config.vworldKey, config.center, config.zoom);
    await loadLandData();
  } catch (error) {
    const message = error instanceof HttpError ? error.message : "지도를 초기화하지 못했습니다.";
    setListStatus(message, "red");
  }
}

document.addEventListener("DOMContentLoaded", () => {
  void bootstrap();
});
