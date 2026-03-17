import { describe, expect, test, vi } from "vitest";

import { getOrCreateWebSession } from "./web-session-store";

describe("getOrCreateWebSession", () => {
  test("creates a new session when last-seen cookie is expired", () => {
    document.cookie = "web_session_id=existing-session; Path=/";
    document.cookie = `web_last_seen_ts=${Date.now() - (31 * 60 * 1000)}; Path=/`;

    const session = getOrCreateWebSession(Date.now());

    expect(session).toEqual({ sessionId: "uuid-test-1", isNew: true });
    expect(document.cookie).toContain("web_session_id=uuid-test-1");
  });

  test("reuses existing session and refreshes last-seen timestamp", () => {
    vi.spyOn(Date, "now").mockReturnValue(1773705600000);
    document.cookie = "web_session_id=existing-session; Path=/";
    document.cookie = "web_last_seen_ts=1773705500000; Path=/";

    const session = getOrCreateWebSession(Date.now());

    expect(session).toEqual({ sessionId: "existing-session", isNew: false });
    expect(document.cookie).toContain("web_last_seen_ts=1773705600000");
  });
});
