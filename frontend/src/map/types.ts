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
  source_fields?: Array<{ key: string; label: string; value: string }>;
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
  pageQuery?: string | null;
  clientTs: number;
  clientTz: string;
  clientLang?: string | null;
  platform?: string | null;
  referrerUrl?: string | null;
  referrerDomain?: string | null;
  utmSource?: string | null;
  utmMedium?: string | null;
  utmCampaign?: string | null;
  utmTerm?: string | null;
  utmContent?: string | null;
  screenWidth?: number | null;
  screenHeight?: number | null;
  viewportWidth?: number | null;
  viewportHeight?: number | null;
};
