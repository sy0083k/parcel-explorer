import type { WebVisitEventPayload, WebVisitEventType } from "./types";

const WEB_SESSION_ID_COOKIE_NAME = "web_session_id";
const WEB_LAST_SEEN_COOKIE_NAME = "web_last_seen_ts";
const WEB_SESSION_MAX_AGE_SECONDS = 60 * 60 * 24;
const WEB_SESSION_TIMEOUT_MS = 30 * 60 * 1000;
const WEB_HEARTBEAT_INTERVAL_MS = 15000;

type SessionTrackerDeps = {
  getOrCreateAnonId: () => string;
  postWebEvent: (payload: WebVisitEventPayload) => Promise<void>;
};

type VisitContext = {
  pagePath: string;
  pageQuery: string | null;
  clientLang: string | null;
  platform: string | null;
  referrerUrl: string | null;
  referrerDomain: string | null;
  utmSource: string | null;
  utmMedium: string | null;
  utmCampaign: string | null;
  utmTerm: string | null;
  utmContent: string | null;
  screenWidth: number | null;
  screenHeight: number | null;
  viewportWidth: number | null;
  viewportHeight: number | null;
};

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

function createClientSessionId(): string {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    return crypto.randomUUID();
  }
  return `${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;
}

function getClientTz(): string {
  const tz = Intl.DateTimeFormat().resolvedOptions().timeZone;
  return tz || "UTC";
}

function getOrCreateWebSessionId(nowMs: number): { sessionId: string; isNew: boolean } {
  const existingSessionId = getCookie(WEB_SESSION_ID_COOKIE_NAME);
  const existingLastSeenRaw = getCookie(WEB_LAST_SEEN_COOKIE_NAME);
  const existingLastSeenMs = existingLastSeenRaw ? Number.parseInt(existingLastSeenRaw, 10) : Number.NaN;
  const isExpired = Number.isNaN(existingLastSeenMs) || nowMs - existingLastSeenMs > WEB_SESSION_TIMEOUT_MS;

  if (!existingSessionId || isExpired) {
    const sessionId = createClientSessionId();
    setCookie(WEB_SESSION_ID_COOKIE_NAME, sessionId, WEB_SESSION_MAX_AGE_SECONDS);
    setCookie(WEB_LAST_SEEN_COOKIE_NAME, String(nowMs), WEB_SESSION_MAX_AGE_SECONDS);
    return { sessionId, isNew: true };
  }

  setCookie(WEB_LAST_SEEN_COOKIE_NAME, String(nowMs), WEB_SESSION_MAX_AGE_SECONDS);
  return { sessionId: existingSessionId, isNew: false };
}

function normalizeReferrerUrl(raw: string): string | null {
  const value = raw.trim();
  if (!value) {
    return null;
  }
  try {
    const parsed = new URL(value);
    parsed.search = "";
    parsed.hash = "";
    return `${parsed.origin}${parsed.pathname}`.slice(0, 1024);
  } catch {
    return null;
  }
}

function extractReferrerDomain(referrerUrl: string | null): string | null {
  if (!referrerUrl) {
    return null;
  }
  try {
    return new URL(referrerUrl).hostname.toLowerCase() || null;
  } catch {
    return null;
  }
}

function pickString(value: string | null, maxLength: number): string | null {
  if (!value) {
    return null;
  }
  const trimmed = value.trim();
  if (!trimmed) {
    return null;
  }
  return trimmed.slice(0, maxLength);
}

function readViewportDimension(value: number): number | null {
  if (!Number.isFinite(value) || value <= 0) {
    return null;
  }
  return Math.round(value);
}

function buildVisitContext(): VisitContext {
  const params = new URLSearchParams(window.location.search);
  const referrerUrl = normalizeReferrerUrl(document.referrer);
  const pagePath = window.location.pathname || "/";
  const pageQuery = pickString(window.location.search.replace(/^\?/, ""), 1024);

  return {
    pagePath,
    pageQuery,
    clientLang: pickString(navigator.language || null, 64),
    platform: pickString(navigator.platform || null, 64),
    referrerUrl,
    referrerDomain: extractReferrerDomain(referrerUrl),
    utmSource: pickString(params.get("utm_source"), 256),
    utmMedium: pickString(params.get("utm_medium"), 256),
    utmCampaign: pickString(params.get("utm_campaign"), 256),
    utmTerm: pickString(params.get("utm_term"), 256),
    utmContent: pickString(params.get("utm_content"), 256),
    screenWidth: readViewportDimension(window.screen.width),
    screenHeight: readViewportDimension(window.screen.height),
    viewportWidth: readViewportDimension(window.innerWidth),
    viewportHeight: readViewportDimension(window.innerHeight)
  };
}

export function createSessionTracker(deps: SessionTrackerDeps) {
  let webHeartbeatTimer: number | null = null;

  const sendSingle = async (
    eventType: WebVisitEventType,
    anonId: string,
    sessionId: string,
    nowSeconds: number,
    clientTz: string,
    context: VisitContext
  ): Promise<void> => {
    await deps.postWebEvent({
      eventType,
      anonId,
      sessionId,
      pagePath: context.pagePath,
      pageQuery: context.pageQuery,
      clientTs: nowSeconds,
      clientTz,
      clientLang: context.clientLang,
      platform: context.platform,
      referrerUrl: context.referrerUrl,
      referrerDomain: context.referrerDomain,
      utmSource: context.utmSource,
      utmMedium: context.utmMedium,
      utmCampaign: context.utmCampaign,
      utmTerm: context.utmTerm,
      utmContent: context.utmContent,
      screenWidth: context.screenWidth,
      screenHeight: context.screenHeight,
      viewportWidth: context.viewportWidth,
      viewportHeight: context.viewportHeight
    });
  };

  const sendWebEvent = (eventType: WebVisitEventType): void => {
    const nowMs = Date.now();
    const anonId = deps.getOrCreateAnonId();
    const { sessionId, isNew } = getOrCreateWebSessionId(nowMs);
    const clientTz = getClientTz();
    const nowSeconds = Math.floor(nowMs / 1000);
    const context = buildVisitContext();

    if (isNew && eventType !== "visit_start") {
      void sendSingle("visit_start", anonId, sessionId, nowSeconds, clientTz, context)
        .then(() => sendSingle(eventType, anonId, sessionId, nowSeconds, clientTz, context))
        .catch(() => {
          // Ignore telemetry failures.
        });
      return;
    }

    void sendSingle(eventType, anonId, sessionId, nowSeconds, clientTz, context).catch(() => {
      // Ignore telemetry failures.
    });
  };

  const startWebHeartbeat = (): void => {
    if (webHeartbeatTimer !== null) {
      window.clearInterval(webHeartbeatTimer);
    }
    webHeartbeatTimer = window.setInterval(() => {
      if (document.visibilityState === "visible") {
        sendWebEvent("heartbeat");
      }
    }, WEB_HEARTBEAT_INTERVAL_MS);
  };

  const stopWebHeartbeat = (): void => {
    if (webHeartbeatTimer === null) {
      return;
    }
    window.clearInterval(webHeartbeatTimer);
    webHeartbeatTimer = null;
  };

  const mount = (): void => {
    sendWebEvent("visit_start");
    startWebHeartbeat();

    document.addEventListener("visibilitychange", () => {
      if (document.visibilityState === "hidden") {
        sendWebEvent("visit_end");
        stopWebHeartbeat();
        return;
      }
      sendWebEvent("visit_start");
      startWebHeartbeat();
    });

    window.addEventListener("pagehide", () => {
      sendWebEvent("visit_end");
      stopWebHeartbeat();
    });
  };

  return {
    mount
  };
}

export type SessionTracker = ReturnType<typeof createSessionTracker>;
