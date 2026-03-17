import { beforeEach, describe, expect, test, vi } from "vitest";

const { fetchJsonMock } = vi.hoisted(() => ({
  fetchJsonMock: vi.fn(),
}));

vi.mock("../http", () => ({
  fetchJson: fetchJsonMock,
}));

import { createTelemetry } from "./telemetry";

describe("createTelemetry", () => {
  beforeEach(() => {
    fetchJsonMock.mockReset();
  });

  test("creates and reuses anon id cookie", () => {
    const telemetry = createTelemetry();

    expect(telemetry.getOrCreateAnonId()).toBe("uuid-test-1");
    expect(document.cookie).toContain("anon_id=uuid-test-1");
    expect(telemetry.getOrCreateAnonId()).toBe("uuid-test-1");
  });

  test("tracks search event with raw inputs", async () => {
    fetchJsonMock.mockResolvedValue({ success: true });
    const telemetry = createTelemetry();

    telemetry.trackSearchEvent(120, "대산읍", " 대산읍 ", " 120 ", " 500 ", "true");

    await Promise.resolve();

    expect(fetchJsonMock).toHaveBeenCalledWith("/api/events", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        eventType: "search",
        anonId: "uuid-test-1",
        minArea: 120,
        searchTerm: "대산읍",
        rawSearchTerm: " 대산읍 ",
        rawMinAreaInput: " 120 ",
        rawMaxAreaInput: " 500 ",
        rawRentOnly: "true",
      }),
      timeoutMs: 3000,
    });
  });

  test("ignores blank land click address", async () => {
    const telemetry = createTelemetry();

    telemetry.trackLandClickEvent("   ", "map_click");
    await Promise.resolve();

    expect(fetchJsonMock).not.toHaveBeenCalled();
  });

  test("tracks land click with trimmed address and string land id", async () => {
    fetchJsonMock.mockResolvedValue({ success: true });
    const telemetry = createTelemetry();

    telemetry.trackLandClickEvent(" 충남 서산시 대산읍 독곶리 1-1 ", "list_click", 99);
    await Promise.resolve();

    expect(fetchJsonMock).toHaveBeenCalledWith("/api/events", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        eventType: "land_click",
        anonId: "uuid-test-1",
        landAddress: "충남 서산시 대산읍 독곶리 1-1",
        landId: "99",
        clickSource: "list_click",
      }),
      timeoutMs: 3000,
    });
  });

  test("posts visit_end as keepalive web event", async () => {
    fetchJsonMock.mockResolvedValue({ success: true });
    const telemetry = createTelemetry();

    await telemetry.postWebEvent({
      eventType: "visit_end",
      anonId: "anon-1",
      sessionId: "session-1",
      pagePath: "/",
      clientTs: 1763596800,
      clientTz: "Asia/Seoul",
    });

    expect(fetchJsonMock).toHaveBeenCalledWith("/api/web-events", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        eventType: "visit_end",
        anonId: "anon-1",
        sessionId: "session-1",
        pagePath: "/",
        clientTs: 1763596800,
        clientTz: "Asia/Seoul",
      }),
      timeoutMs: 3000,
      keepalive: true,
    });
  });

  test("swallows telemetry failures to preserve UX", async () => {
    fetchJsonMock.mockRejectedValue(new Error("network"));
    const telemetry = createTelemetry();

    telemetry.trackSearchEvent(10, "예천동", "예천동", "10", "20", "false");

    await Promise.resolve();
    await Promise.resolve();

    expect(fetchJsonMock).toHaveBeenCalledTimes(1);
  });
});
