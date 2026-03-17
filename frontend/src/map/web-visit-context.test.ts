import { describe, expect, test } from "vitest";

import { buildWebVisitContext } from "./web-visit-context";

describe("buildWebVisitContext", () => {
  test("normalizes referrer, query params, and viewport metadata", () => {
    window.history.replaceState(null, "", "/lands?utm_source=google&utm_content=hero");
    Object.defineProperty(document, "referrer", {
      configurable: true,
      value: " https://Example.com/path?q=test#fragment ",
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
      value: 720,
    });
    Object.defineProperty(window.screen, "width", {
      configurable: true,
      value: 1920,
    });
    Object.defineProperty(window.screen, "height", {
      configurable: true,
      value: 1080,
    });

    expect(buildWebVisitContext()).toEqual({
      pagePath: "/lands",
      pageQuery: "utm_source=google&utm_content=hero",
      clientLang: "ko-KR",
      platform: "Linux x86_64",
      referrerUrl: "https://example.com/path",
      referrerDomain: "example.com",
      utmSource: "google",
      utmMedium: null,
      utmCampaign: null,
      utmTerm: null,
      utmContent: "hero",
      screenWidth: 1920,
      screenHeight: 1080,
      viewportWidth: 1280,
      viewportHeight: 720,
    });
  });

  test("returns null for invalid optional values", () => {
    window.history.replaceState(null, "", "/");
    Object.defineProperty(document, "referrer", {
      configurable: true,
      value: "not a url",
    });
    Object.defineProperty(navigator, "language", {
      configurable: true,
      value: "   ",
    });
    Object.defineProperty(navigator, "platform", {
      configurable: true,
      value: "",
    });
    Object.defineProperty(window, "innerWidth", {
      configurable: true,
      value: 0,
    });
    Object.defineProperty(window, "innerHeight", {
      configurable: true,
      value: Number.NaN,
    });
    Object.defineProperty(window.screen, "width", {
      configurable: true,
      value: -1,
    });
    Object.defineProperty(window.screen, "height", {
      configurable: true,
      value: 0,
    });

    expect(buildWebVisitContext()).toEqual({
      pagePath: "/",
      pageQuery: null,
      clientLang: null,
      platform: null,
      referrerUrl: null,
      referrerDomain: null,
      utmSource: null,
      utmMedium: null,
      utmCampaign: null,
      utmTerm: null,
      utmContent: null,
      screenWidth: null,
      screenHeight: null,
      viewportWidth: null,
      viewportHeight: null,
    });
  });
});
