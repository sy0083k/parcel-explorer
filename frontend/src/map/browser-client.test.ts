import { describe, expect, test, vi } from "vitest";

import { createClientId, readCookie, writeCookie } from "./browser-client";

describe("browser-client", () => {
  test("writes and reads encoded cookies", () => {
    writeCookie("utm source", "naver search", 60);

    expect(readCookie("utm source")).toBe("naver search");
    expect(document.cookie).toContain("utm%20source=naver%20search");
  });

  test("falls back when crypto.randomUUID is unavailable", () => {
    Object.defineProperty(globalThis, "crypto", {
      configurable: true,
      value: {},
    });
    vi.spyOn(Date, "now").mockReturnValue(1000);
    vi.spyOn(Math, "random").mockReturnValue(0.123456789);

    expect(createClientId()).toBe("1000-4fzzzxjy");
  });
});
