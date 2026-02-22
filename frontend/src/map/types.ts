export type MapConfig = {
  vworldKey: string;
  center: [number, number];
  zoom: number;
};

export type LandFeatureProperties = {
  id?: number;
  address?: string;
  land_type?: string;
  area?: number;
  adm_property?: string;
  gen_property?: string;
  contact?: string;
};

export type LandFeature = {
  type: "Feature";
  geometry: unknown;
  properties: LandFeatureProperties;
};

export type LandFeatureCollection = {
  type: "FeatureCollection";
  features: LandFeature[];
};

export type LandsPageResponse = LandFeatureCollection & {
  nextCursor: string | null;
};

export type BaseType = "Base" | "Satellite" | "Hybrid";
export type LandClickSource = "map_click" | "list_click" | "nav_prev" | "nav_next";

export type MapEventPayload =
  | {
      eventType: "search";
      anonId: string;
      minArea: number;
      searchTerm: string;
      rawSearchTerm: string;
      rawMinAreaInput: string;
      rawMaxAreaInput: string;
      rawRentOnly: string;
    }
  | {
      eventType: "land_click";
      anonId: string;
      landAddress: string;
      landId?: string;
      clickSource?: LandClickSource;
    };

export type WebVisitEventType = "visit_start" | "heartbeat" | "visit_end";

export type WebVisitEventPayload = {
  eventType: WebVisitEventType;
  anonId: string;
  sessionId: string;
  pagePath: string;
  clientTs: number;
  clientTz: string;
};
