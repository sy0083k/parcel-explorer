import { beforeEach, describe, expect, test, vi } from "vitest";

import { createSessionTracker } from "./session-tracker";

describe("createSessionTracker", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date("2026-03-17T00:00:00Z"));
    window.history.replaceState(null, "", "/?utm_source=google&utm_medium=social");
    Object.defineProperty(document, "referrer", {
      configurable: true,
      value: "https://Example.com/search?q=test",
    });
    Object.defineProperty(navigator, "language", {
      configurable: true,
      value: "ko-KR",
    });
    Object.defineProperty(navigator, "platform", {
      configurable: true,
      value: "Linux x86_64",
    });
    Object.defineProperty(window, "innerWidth", {
      configurable: true,
      value: 1280,
    });
    Object.defineProperty(window, "innerHeight", {
      configurable: true,
      value: 800,
    });
    Object.defineProperty(window.screen, "width", {
      configurable: true,
      value: 1920,
    });
    Object.defineProperty(window.screen, "height", {
      configurable: true,
      value: 1080,
    });
  });

  test("mount sends visit_start with derived visit context", async () => {
    const postWebEvent = vi.fn(async () => undefined);
    const tracker = createSessionTracker({
      getOrCreateAnonId: () => "anon-1",
      postWebEvent,
    });

    tracker.mount();
    await Promise.resolve();

    expect(postWebEvent).toHaveBeenCalledTimes(1);
    expect(postWebEvent).toHaveBeenCalledWith(
      expect.objectContaining({
        eventType: "visit_start",
        anonId: "anon-1",
        sessionId: "uuid-test-1",
        pagePath: "/",
        pageQuery: "utm_source=google&utm_medium=social",
        clientTs: 1773705600,
        clientTz: "Asia/Seoul",
        clientLang: "ko-KR",
        platform: "Linux x86_64",
        referrerUrl: "https://example.com/search",
        referrerDomain: "example.com",
        utmSource: "google",
        utmMedium: "social",
        screenWidth: 1920,
        screenHeight: 1080,
        viewportWidth: 1280,
        viewportHeight: 800,
      }),
    );
  });

  test("heartbeat posts when page is visible", async () => {
    const postWebEvent = vi.fn(async () => undefined);
    const tracker = createSessionTracker({
      getOrCreateAnonId: () => "anon-1",
      postWebEvent,
    });

    tracker.mount();
    await Promise.resolve();
    vi.advanceTimersByTime(15000);
    await Promise.resolve();

    expect(postWebEvent).toHaveBeenCalledWith(expect.objectContaining({ eventType: "heartbeat" }));
  });

  test("hidden visibility sends visit_end and visible resumes with visit_start", async () => {
    const postWebEvent = vi.fn(async () => undefined);
    const tracker = createSessionTracker({
      getOrCreateAnonId: () => "anon-1",
      postWebEvent,
    });

    tracker.mount();
    await Promise.resolve();

    Object.defineProperty(document, "visibilityState", {
      configurable: true,
      value: "hidden",
    });
    document.dispatchEvent(new Event("visibilitychange"));
    await Promise.resolve();

    Object.defineProperty(document, "visibilityState", {
      configurable: true,
      value: "visible",
    });
    document.dispatchEvent(new Event("visibilitychange"));
    await Promise.resolve();

    expect(postWebEvent).toHaveBeenCalledWith(expect.objectContaining({ eventType: "visit_end" }));
    expect(postWebEvent).toHaveBeenCalledWith(expect.objectContaining({ eventType: "visit_start" }));
  });

  test("pagehide sends visit_end", async () => {
    const postWebEvent = vi.fn(async () => undefined);
    const tracker = createSessionTracker({
      getOrCreateAnonId: () => "anon-1",
      postWebEvent,
    });

    tracker.mount();
    await Promise.resolve();
    window.dispatchEvent(new Event("pagehide"));
    await Promise.resolve();

    expect(postWebEvent).toHaveBeenCalledWith(expect.objectContaining({ eventType: "visit_end" }));
  });

  test("reuses existing active session id for non-start event", async () => {
    const postWebEvent = vi.fn(async () => undefined);
    document.cookie = "web_session_id=existing-session; Path=/";
    document.cookie = `web_last_seen_ts=${Date.now()}; Path=/`;
    const tracker = createSessionTracker({
      getOrCreateAnonId: () => "anon-1",
      postWebEvent,
    });

    tracker.mount();
    await Promise.resolve();
    await Promise.resolve();
    window.dispatchEvent(new Event("pagehide"));
    await Promise.resolve();

    expect(postWebEvent).toHaveBeenNthCalledWith(
      1,
      expect.objectContaining({ eventType: "visit_start", sessionId: "existing-session" }),
    );
    expect(postWebEvent).toHaveBeenNthCalledWith(
      2,
      expect.objectContaining({ eventType: "visit_end", sessionId: "existing-session" }),
    );
  });
});
