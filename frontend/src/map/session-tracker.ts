import type { WebVisitEventPayload, WebVisitEventType } from "./types";
import { getOrCreateWebSession } from "./web-session-store";
import { buildWebVisitContext, getClientTz } from "./web-visit-context";
import type { VisitContext } from "./web-visit-context";

const WEB_HEARTBEAT_INTERVAL_MS = 15000;

type SessionTrackerDeps = {
  getOrCreateAnonId: () => string;
  postWebEvent: (payload: WebVisitEventPayload) => Promise<void>;
};

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
    const { sessionId, isNew } = getOrCreateWebSession(nowMs);
    const clientTz = getClientTz();
    const nowSeconds = Math.floor(nowMs / 1000);
    const context = buildWebVisitContext();

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

  const handleVisibilityChange = (): void => {
    if (document.visibilityState === "hidden") {
      sendWebEvent("visit_end");
      stopWebHeartbeat();
      return;
    }
    sendWebEvent("visit_start");
    startWebHeartbeat();
  };

  const handlePageHide = (): void => {
    sendWebEvent("visit_end");
    stopWebHeartbeat();
  };

  const mount = (): void => {
    sendWebEvent("visit_start");
    startWebHeartbeat();
    document.addEventListener("visibilitychange", handleVisibilityChange);
    window.addEventListener("pagehide", handlePageHide);
  };

  return {
    mount
  };
}

export type SessionTracker = ReturnType<typeof createSessionTracker>;
