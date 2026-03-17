import { describe, expect, test } from "vitest";

import { HttpError } from "../http";

import { resolveAdminErrorMessage } from "./errors";

describe("resolveAdminErrorMessage", () => {
  test("returns HttpError message", () => {
    expect(resolveAdminErrorMessage(new HttpError("request failed", 500), "fallback")).toBe("request failed");
  });

  test("returns fallback for generic Error", () => {
    expect(resolveAdminErrorMessage(new Error("boom"), "fallback")).toBe("fallback");
  });

  test("returns fallback for non-error values", () => {
    expect(resolveAdminErrorMessage("boom", "fallback")).toBe("fallback");
    expect(resolveAdminErrorMessage(null, "fallback")).toBe("fallback");
  });
});
