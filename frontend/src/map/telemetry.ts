import { fetchJson } from "../http";

import type { LandClickSource, MapEventPayload, WebVisitEventPayload } from "./types";

const ANON_COOKIE_NAME = "anon_id";
const ANON_COOKIE_MAX_AGE_SECONDS = 60 * 60 * 24 * 365;

function getCookie(name: string): string | null {
  const encodedName = `${encodeURIComponent(name)}=`;
  const found = document.cookie
    .split(";")
    .map((item) => item.trim())
    .find((item) => item.startsWith(encodedName));
  if (!found) {
    return null;
  }
  return decodeURIComponent(found.slice(encodedName.length));
}

function setCookie(name: string, value: string, maxAgeSeconds: number): void {
  document.cookie = `${encodeURIComponent(name)}=${encodeURIComponent(value)}; Max-Age=${maxAgeSeconds}; Path=/; SameSite=Lax`;
}

function createAnonId(): string {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    return crypto.randomUUID();
  }
  return `${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;
}

async function postMapEvent(payload: MapEventPayload): Promise<void> {
  await fetchJson<{ success: boolean }>("/api/events", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
    timeoutMs: 3000
  });
}

async function postWebEvent(payload: WebVisitEventPayload): Promise<void> {
  await fetchJson<{ success: boolean }>("/api/web-events", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
    timeoutMs: 3000,
    keepalive: payload.eventType === "visit_end"
  });
}

export function createTelemetry() {
  function getOrCreateAnonId(): string {
    const existing = getCookie(ANON_COOKIE_NAME);
    if (existing) {
      return existing;
    }
    const generated = createAnonId();
    setCookie(ANON_COOKIE_NAME, generated, ANON_COOKIE_MAX_AGE_SECONDS);
    return generated;
  }

  function trackSearchEvent(
    minArea: number,
    searchTerm: string,
    rawSearchTerm: string,
    rawMinAreaInput: string,
    rawMaxAreaInput: string,
    rawRentOnly: string
  ): void {
    const anonId = getOrCreateAnonId();
    void postMapEvent({
      eventType: "search",
      anonId,
      minArea,
      searchTerm,
      rawSearchTerm,
      rawMinAreaInput,
      rawMaxAreaInput,
      rawRentOnly
    }).catch(() => {
      // Keep map UX responsive even if telemetry fails.
    });
  }

  function trackLandClickEvent(address: string, clickSource: LandClickSource, landId?: number): void {
    const trimmed = address.trim();
    if (!trimmed) {
      return;
    }
    const anonId = getOrCreateAnonId();
    void postMapEvent({
      eventType: "land_click",
      anonId,
      landAddress: trimmed,
      landId: typeof landId === "number" ? String(landId) : undefined,
      clickSource
    }).catch(() => {
      // Keep map UX responsive even if telemetry fails.
    });
  }

  return {
    getOrCreateAnonId,
    postWebEvent,
    trackSearchEvent,
    trackLandClickEvent
  };
}

export type Telemetry = ReturnType<typeof createTelemetry>;
