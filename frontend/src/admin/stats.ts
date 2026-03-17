import { fetchJson } from "../http";

import { requireElement } from "./dom";
import { resolveAdminErrorMessage } from "./errors";
import type { StatsResponse, WebStatsResponse } from "./types";

type AdminStatsCharts = {
  renderStatsCharts(payload: StatsResponse): void;
  renderWebStatsChart(payload: WebStatsResponse): void;
};

type AdminStatsController = {
  load(force?: boolean): Promise<void>;
  bindRefreshButton(): void;
};

function renderTopList<T>(
  id: string,
  items: T[],
  formatter: (item: T, index: number) => string,
  emptyText: string
): void {
  const el = document.getElementById(id);
  if (!el) {
    return;
  }
  if (!items.length) {
    el.textContent = emptyText;
    return;
  }
  el.style.whiteSpace = "pre-line";
  el.textContent = items.map((item, index) => formatter(item, index)).join("\n");
}

export function createAdminStatsController(charts: AdminStatsCharts): AdminStatsController {
  let hasLoadedStats = false;

  async function load(force = false): Promise<void> {
    if (!force && hasLoadedStats) {
      return;
    }

    const status = requireElement("statsStatus", HTMLDivElement);
    const searchCount = requireElement("stats-search-count", HTMLInputElement);
    const clickCount = requireElement("stats-click-count", HTMLInputElement);
    const uniqueSessionCount = requireElement("stats-unique-session-count", HTMLInputElement);
    const totalLands = requireElement("stats-total-lands", HTMLInputElement);
    const missingGeomLands = requireElement("stats-missing-geom-lands", HTMLInputElement);
    const webDailyVisitors = requireElement("web-daily-visitors", HTMLInputElement);
    const webTotalVisitors = requireElement("web-total-visitors", HTMLInputElement);
    const webAvgDwell = requireElement("web-avg-dwell", HTMLInputElement);
    const webSessionCount = requireElement("web-session-count", HTMLInputElement);
    const webStatus = requireElement("webStatsStatus", HTMLDivElement);

    if (
      !status ||
      !searchCount ||
      !clickCount ||
      !uniqueSessionCount ||
      !totalLands ||
      !missingGeomLands ||
      !webDailyVisitors ||
      !webTotalVisitors ||
      !webAvgDwell ||
      !webSessionCount ||
      !webStatus
    ) {
      return;
    }

    status.style.color = "#6b7280";
    status.innerText = "통계를 불러오는 중입니다...";
    webStatus.style.color = "#6b7280";
    webStatus.innerText = "웹 통계를 불러오는 중입니다...";

    try {
      const [payload, webPayload] = await Promise.all([
        fetchJson<StatsResponse>("/admin/stats?limit=10", { timeoutMs: 10000 }),
        fetchJson<WebStatsResponse>("/admin/stats/web?days=30", { timeoutMs: 10000 })
      ]);

      searchCount.value = String(payload.summary.searchCount);
      clickCount.value = String(payload.summary.clickCount);
      uniqueSessionCount.value = String(payload.summary.uniqueSessionCount);
      totalLands.value = String(payload.landSummary.totalLands);
      missingGeomLands.value = String(payload.landSummary.missingGeomLands);
      webDailyVisitors.value = String(webPayload.summary.dailyVisitors);
      webTotalVisitors.value = String(webPayload.summary.totalVisitors);
      webAvgDwell.value = String(webPayload.summary.avgDwellMinutes);
      webSessionCount.value = String(webPayload.summary.sessionCount);

      renderTopList(
        "statsTopRegions",
        payload.topRegions,
        (item, index) => `${index + 1}. ${item.region} (${item.count})`,
        "지역 검색 데이터 없음"
      );
      renderTopList(
        "statsTopBuckets",
        payload.topMinAreaBuckets,
        (item, index) => `${index + 1}. ${item.bucket}㎡ (${item.count})`,
        "최소 면적 검색 데이터 없음"
      );
      renderTopList(
        "statsTopClickedLands",
        payload.topClickedLands,
        (item, index) =>
          `${index + 1}. ${item.address}\n   총 클릭: ${item.clickCount}, 고유 세션: ${item.uniqueSessionCount}`,
        "클릭 데이터 없음"
      );

      charts.renderStatsCharts(payload);
      charts.renderWebStatsChart(webPayload);
      hasLoadedStats = true;
      status.style.color = "#16a34a";
      status.innerText = "통계 갱신 완료";
      webStatus.style.color = "#16a34a";
      webStatus.innerText = "웹 통계 갱신 완료";
    } catch (error) {
      const message = resolveAdminErrorMessage(error, "통계를 불러오지 못했습니다.");
      status.style.color = "#dc2626";
      status.innerText = message;
      webStatus.style.color = "#dc2626";
      webStatus.innerText = message;
    }
  }

  return {
    load,
    bindRefreshButton(): void {
      const refreshStatsButton = requireElement("refreshStatsBtn", HTMLButtonElement);
      if (!refreshStatsButton) {
        return;
      }
      refreshStatsButton.addEventListener("click", () => {
        void load(true);
      });
    }
  };
}
