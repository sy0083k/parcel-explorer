import type { WebVisitEventPayload, WebVisitEventType } from "./types";

const WEB_SESSION_ID_COOKIE_NAME = "web_session_id";
const WEB_LAST_SEEN_COOKIE_NAME = "web_last_seen_ts";
const WEB_SESSION_MAX_AGE_SECONDS = 60 * 60 * 24;
const WEB_SESSION_TIMEOUT_MS = 30 * 60 * 1000;
const WEB_HEARTBEAT_INTERVAL_MS = 15000;
const WEB_TRACK_PATH = "/";

type SessionTrackerDeps = {
  getOrCreateAnonId: () => string;
  postWebEvent: (payload: WebVisitEventPayload) => Promise<void>;
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

export function createSessionTracker(deps: SessionTrackerDeps) {
  let webHeartbeatTimer: number | null = null;

  const sendSingle = async (
    eventType: WebVisitEventType,
    anonId: string,
    sessionId: string,
    nowSeconds: number,
    clientTz: string
  ): Promise<void> => {
    await deps.postWebEvent({
      eventType,
      anonId,
      sessionId,
      pagePath: WEB_TRACK_PATH,
      clientTs: nowSeconds,
      clientTz
    });
  };

  const sendWebEvent = (eventType: WebVisitEventType): void => {
    const nowMs = Date.now();
    const anonId = deps.getOrCreateAnonId();
    const { sessionId, isNew } = getOrCreateWebSessionId(nowMs);
    const clientTz = getClientTz();
    const nowSeconds = Math.floor(nowMs / 1000);

    if (isNew && eventType !== "visit_start") {
      void sendSingle("visit_start", anonId, sessionId, nowSeconds, clientTz)
        .then(() => sendSingle(eventType, anonId, sessionId, nowSeconds, clientTz))
        .catch(() => {
          // Ignore telemetry failures.
        });
      return;
    }

    void sendSingle(eventType, anonId, sessionId, nowSeconds, clientTz).catch(() => {
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
