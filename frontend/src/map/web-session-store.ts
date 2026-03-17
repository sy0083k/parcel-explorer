import { createClientId, readCookie, writeCookie } from "./browser-client";

const WEB_SESSION_ID_COOKIE_NAME = "web_session_id";
const WEB_LAST_SEEN_COOKIE_NAME = "web_last_seen_ts";
const WEB_SESSION_MAX_AGE_SECONDS = 60 * 60 * 24;
const WEB_SESSION_TIMEOUT_MS = 30 * 60 * 1000;

export type WebSession = {
  sessionId: string;
  isNew: boolean;
};

export function getOrCreateWebSession(nowMs: number): WebSession {
  const existingSessionId = readCookie(WEB_SESSION_ID_COOKIE_NAME);
  const existingLastSeenRaw = readCookie(WEB_LAST_SEEN_COOKIE_NAME);
  const existingLastSeenMs = existingLastSeenRaw ? Number.parseInt(existingLastSeenRaw, 10) : Number.NaN;
  const isExpired = Number.isNaN(existingLastSeenMs) || nowMs - existingLastSeenMs > WEB_SESSION_TIMEOUT_MS;

  if (!existingSessionId || isExpired) {
    const sessionId = createClientId();
    writeCookie(WEB_SESSION_ID_COOKIE_NAME, sessionId, WEB_SESSION_MAX_AGE_SECONDS);
    writeCookie(WEB_LAST_SEEN_COOKIE_NAME, String(nowMs), WEB_SESSION_MAX_AGE_SECONDS);
    return { sessionId, isNew: true };
  }

  writeCookie(WEB_LAST_SEEN_COOKIE_NAME, String(nowMs), WEB_SESSION_MAX_AGE_SECONDS);
  return { sessionId: existingSessionId, isNew: false };
}
