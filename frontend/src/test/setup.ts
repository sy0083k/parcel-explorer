import { afterEach, beforeEach, vi } from "vitest";

beforeEach(() => {
  document.body.innerHTML = "";
  document.body.className = "";
  document.body.style.cssText = "";
  document.cookie = "anon_id=; Max-Age=0; Path=/";
  document.cookie = "web_session_id=; Max-Age=0; Path=/";
  document.cookie = "web_last_seen_ts=; Max-Age=0; Path=/";

  Object.defineProperty(document, "visibilityState", {
    configurable: true,
    value: "visible",
  });

  Object.defineProperty(window, "matchMedia", {
    configurable: true,
    value: vi.fn((query: string) => ({
      matches: false,
      media: query,
      onchange: null,
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      addListener: vi.fn(),
      removeListener: vi.fn(),
      dispatchEvent: vi.fn(),
    })),
  });

  Object.defineProperty(globalThis, "crypto", {
    configurable: true,
    value: {
      randomUUID: vi.fn(() => "uuid-test-1"),
    },
  });
});

afterEach(() => {
  vi.useRealTimers();
  vi.restoreAllMocks();
});
