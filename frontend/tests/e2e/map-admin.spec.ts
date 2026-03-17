import { expect, test } from "@playwright/test";

const VWORLD_TILE = Buffer.from(
  "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAusB9WnM6i8AAAAASUVORK5CYII=",
  "base64"
);

const CHART_STUB = `
  window.__chartCalls = [];
  window.Chart = class Chart {
    constructor(_canvas, config) {
      window.__chartCalls.push({
        type: config?.type ?? null,
        labels: Array.isArray(config?.data?.labels) ? config.data.labels.length : 0
      });
      this.config = config;
    }
    destroy() {}
  };
`;

function parseJsonBody(request: { postData(): string | null }): Record<string, unknown> {
  return JSON.parse(request.postData() || "{}") as Record<string, unknown>;
}

test.beforeEach(async ({ context }) => {
  await context.route("https://api.vworld.kr/**", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "image/png",
      body: VWORLD_TILE,
    });
  });

  await context.route("https://cdn.jsdelivr.net/npm/chart.js@4.4.4/dist/chart.umd.min.js", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/javascript",
      body: CHART_STUB,
    });
  });
});

test("loads map flow, records telemetry, and renders admin stats", async ({ page }) => {
  const visitStartPromise = page.waitForRequest((request) => {
    if (!request.url().endsWith("/api/web-events")) {
      return false;
    }
    return parseJsonBody(request).eventType === "visit_start";
  });

  await page.goto("/");

  const visitStart = parseJsonBody(await visitStartPromise);
  expect(visitStart.pagePath).toBe("/");

  await expect(page.locator(".list-item")).toHaveCount(2);
  await expect(page.locator("#nav-info")).toHaveText("0 / 2");

  await page.locator("#region-search").fill("예천동");
  await page.locator("#min-area").fill("120");

  const searchPromise = page.waitForRequest((request) => {
    if (!request.url().endsWith("/api/events")) {
      return false;
    }
    return parseJsonBody(request).eventType === "search";
  });

  await page.locator("#btn-search").click();

  const searchPayload = parseJsonBody(await searchPromise);
  expect(searchPayload.searchTerm).toBe("예천동");
  expect(searchPayload.rawSearchTerm).toBe("예천동");
  expect(searchPayload.minArea).toBe(120);
  expect(searchPayload.rawMinAreaInput).toBe("120");
  expect(searchPayload.rawRentOnly).toBe("true");

  await expect(page.locator(".list-item")).toHaveCount(1);
  await expect(page.locator(".list-item").first()).toContainText("충남 서산시 예천동 100-1");

  const clickPromise = page.waitForRequest((request) => {
    if (!request.url().endsWith("/api/events")) {
      return false;
    }
    return parseJsonBody(request).eventType === "land_click";
  });

  await page.locator(".list-item").first().click();

  const clickPayload = parseJsonBody(await clickPromise);
  expect(clickPayload.clickSource).toBe("list_click");
  expect(clickPayload.landAddress).toBe("충남 서산시 예천동 100-1");
  expect(Number(clickPayload.landId)).toBeGreaterThan(0);

  await expect(page.locator(".list-item.selected")).toHaveCount(1);
  await expect(page.locator("#nav-info")).toHaveText("1 / 1");

  const visitEndPromise = page.waitForRequest((request) => {
    if (!request.url().endsWith("/api/web-events")) {
      return false;
    }
    return parseJsonBody(request).eventType === "visit_end";
  });

  await page.goto("/admin/login");

  const visitEnd = parseJsonBody(await visitEndPromise);
  expect(visitEnd.pagePath).toBe("/");

  await page.locator('input[name="username"]').fill("admin");
  await page.locator('input[name="password"]').fill("admin-password");

  await Promise.all([
    page.waitForURL(/\/admin\/?$/),
    page.getByRole("button", { name: "로그인" }).click(),
  ]);

  const statsResponsePromise = page.waitForResponse((response) => response.url().includes("/admin/stats?limit=10"));
  const webStatsResponsePromise = page.waitForResponse((response) =>
    response.url().includes("/admin/stats/web?days=30")
  );

  await page.getByRole("button", { name: /통계/ }).click();

  await statsResponsePromise;
  await webStatsResponsePromise;

  await expect(page.locator("#statsStatus")).toHaveText("통계 갱신 완료");
  await expect(page.locator("#webStatsStatus")).toHaveText("웹 통계 갱신 완료");
  await expect(page.locator("#stats-search-count")).toHaveValue("1");
  await expect(page.locator("#stats-click-count")).toHaveValue("1");
  await expect(page.locator("#stats-unique-session-count")).toHaveValue("1");
  await expect(page.locator("#web-total-visitors")).toHaveValue("1");
  await expect(page.locator("#web-session-count")).toHaveValue("1");

  await page.waitForFunction(() => {
    const calls = (window as Window & { __chartCalls?: unknown[] }).__chartCalls;
    return Array.isArray(calls) && calls.length >= 4;
  });
});
