import { HttpError, fetchJson } from "./http";
declare const Chart: any;

type UploadResponse = {
  success: boolean;
  total?: number;
  message: string;
  geomJobId?: number;
};

type StatsResponse = {
  summary: {
    searchCount: number;
    clickCount: number;
    uniqueSessionCount: number;
  };
  topRegions: Array<{ region: string; count: number }>;
  topMinAreaBuckets: Array<{ bucket: string; count: number }>;
  topClickedLands: Array<{ address: string; clickCount: number; uniqueSessionCount: number }>;
  dailyTrend: Array<{ date: string; searchCount: number; clickCount: number }>;
};
type WebStatsResponse = {
  summary: {
    dailyVisitors: number;
    totalVisitors: number;
    avgDwellMinutes: number;
    sessionCount: number;
  };
  dailyTrend: Array<{
    date: string;
    visitors: number;
    sessions: number;
    avgDwellMinutes: number;
  }>;
};

function requireElement<T extends Element>(id: string, type: { new (): T }): T | null {
  const el = document.getElementById(id);
  return el instanceof type ? el : null;
}

function initTabs(onStatsSelected: () => void): void {
  const tabs = document.querySelectorAll<HTMLButtonElement>(".nav button");
  const panels: Record<string, HTMLElement | null> = {
    upload: document.getElementById("panel-upload"),
    settings: document.getElementById("panel-settings"),
    password: document.getElementById("panel-password"),
    stats: document.getElementById("panel-stats")
  };

  tabs.forEach((tab) => {
    tab.addEventListener("click", () => {
      tabs.forEach((item) => item.classList.remove("active"));
      tab.classList.add("active");

      const name = tab.dataset.tab || "upload";
      Object.values(panels).forEach((panel) => panel?.classList.remove("active"));
      panels[name]?.classList.add("active");

      if (name === "stats") {
        onStatsSelected();
      }
    });
  });
}

async function handleUpload(csrfToken: string): Promise<void> {
  const fileInput = requireElement("excelFile", HTMLInputElement);
  const status = requireElement("status", HTMLDivElement);

  if (!fileInput || !status) {
    return;
  }

  const file = fileInput.files?.[0];
  if (!file) {
    alert("파일을 선택해주세요.");
    return;
  }

  const formData = new FormData();
  formData.append("file", file);
  formData.append("csrf_token", csrfToken);

  status.style.color = "black";

  try {
    status.innerText = "1단계: 엑셀 파일 입력 중...";
    const result = await fetchJson<UploadResponse>("/admin/upload", {
      method: "POST",
      body: formData,
      timeoutMs: 45000
    });

    status.style.color = "green";
    status.innerText = result.geomJobId
      ? `업로드 완료 (작업 ID: ${result.geomJobId}). 경계선 보강이 백그라운드에서 진행됩니다.`
      : `업로드 완료: ${result.message}`;
    alert("서버에서 데이터 처리를 시작했습니다. 창을 닫아도 작업은 계속됩니다.");
  } catch (error) {
    status.style.color = "red";
    const message = error instanceof HttpError ? error.message : String(error);
    status.innerText = `오류 발생: ${message}`;
  }
}

function validateSettingsForm(): boolean {
  const input = document.querySelector<HTMLInputElement>('input[name="settings_password"]');
  if (!input || !input.value.trim()) {
    alert("환경 변수 저장을 위해 관리자 비밀번호를 입력해주세요.");
    return false;
  }
  return true;
}

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

let regionChart: any = null;
let minAreaChart: any = null;
let trendChart: any = null;
let webTrendChart: any = null;
let hasLoadedStats = false;

function renderStatsCharts(payload: StatsResponse): void {
  const regionCanvas = requireElement("statsRegionChart", HTMLCanvasElement);
  const minAreaCanvas = requireElement("statsMinAreaChart", HTMLCanvasElement);
  const trendCanvas = requireElement("statsTrendChart", HTMLCanvasElement);

  if (regionChart) {
    regionChart.destroy();
    regionChart = null;
  }
  if (minAreaChart) {
    minAreaChart.destroy();
    minAreaChart = null;
  }
  if (trendChart) {
    trendChart.destroy();
    trendChart = null;
  }

  if (regionCanvas) {
    regionChart = new Chart(regionCanvas, {
      type: "bar",
      data: {
        labels: payload.topRegions.map((item) => item.region),
        datasets: [
          {
            label: "검색 수",
            data: payload.topRegions.map((item) => item.count),
            backgroundColor: "#3b82f6"
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        scales: {
          y: {
            beginAtZero: true,
            grace: "5%",
            ticks: {
              precision: 0
            }
          }
        }
      }
    });
  }

  if (minAreaCanvas) {
    minAreaChart = new Chart(minAreaCanvas, {
      type: "bar",
      data: {
        labels: payload.topMinAreaBuckets.map((item) => item.bucket),
        datasets: [
          {
            label: "검색 수",
            data: payload.topMinAreaBuckets.map((item) => item.count),
            backgroundColor: "#16a34a"
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        scales: {
          y: {
            beginAtZero: true,
            grace: "5%",
            ticks: {
              precision: 0
            }
          }
        }
      }
    });
  }

  if (trendCanvas) {
    trendChart = new Chart(trendCanvas, {
      type: "line",
      data: {
        labels: payload.dailyTrend.map((item) => item.date),
        datasets: [
          {
            label: "검색",
            data: payload.dailyTrend.map((item) => item.searchCount),
            borderColor: "#3b82f6",
            backgroundColor: "rgba(59,130,246,0.2)",
            fill: true
          },
          {
            label: "클릭",
            data: payload.dailyTrend.map((item) => item.clickCount),
            borderColor: "#f97316",
            backgroundColor: "rgba(249,115,22,0.2)",
            fill: true
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        scales: {
          y: {
            beginAtZero: true,
            grace: "5%",
            ticks: {
              precision: 0
            }
          }
        }
      }
    });
  }
}

async function loadStats(force = false): Promise<void> {
  if (!force && hasLoadedStats) {
    return;
  }

  const status = requireElement("statsStatus", HTMLDivElement);
  const searchCount = requireElement("stats-search-count", HTMLInputElement);
  const clickCount = requireElement("stats-click-count", HTMLInputElement);
  const uniqueSessionCount = requireElement("stats-unique-session-count", HTMLInputElement);
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

    renderStatsCharts(payload);
    renderWebStatsChart(webPayload);
    hasLoadedStats = true;
    status.style.color = "#16a34a";
    status.innerText = "통계 갱신 완료";
    webStatus.style.color = "#16a34a";
    webStatus.innerText = "웹 통계 갱신 완료";
  } catch (error) {
    const message = error instanceof HttpError ? error.message : "통계를 불러오지 못했습니다.";
    status.style.color = "#dc2626";
    status.innerText = message;
    webStatus.style.color = "#dc2626";
    webStatus.innerText = message;
  }
}

function renderWebStatsChart(payload: WebStatsResponse): void {
  const canvas = requireElement("webStatsTrendChart", HTMLCanvasElement);
  if (!canvas) {
    return;
  }
  if (webTrendChart) {
    webTrendChart.destroy();
    webTrendChart = null;
  }

  webTrendChart = new Chart(canvas, {
    type: "line",
    data: {
      labels: payload.dailyTrend.map((item) => item.date),
      datasets: [
        {
          label: "방문자",
          data: payload.dailyTrend.map((item) => item.visitors),
          borderColor: "#0ea5e9",
          backgroundColor: "rgba(14,165,233,0.2)",
          fill: true
        },
        {
          label: "평균 체류(분)",
          data: payload.dailyTrend.map((item) => item.avgDwellMinutes),
          borderColor: "#22c55e",
          backgroundColor: "rgba(34,197,94,0.2)",
          fill: true
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      scales: {
        y: {
          beginAtZero: true,
          grace: "5%"
        }
      }
    }
  });
}

document.addEventListener("DOMContentLoaded", () => {
  initTabs(() => {
    void loadStats(false);
  });

  const csrfInput = requireElement("csrfToken", HTMLInputElement);
  const uploadButton = document.getElementById("uploadBtn");
  const settingsForm = document.getElementById("settingsForm");
  const refreshStatsButton = document.getElementById("refreshStatsBtn");

  if (uploadButton && csrfInput) {
    uploadButton.addEventListener("click", () => {
      void handleUpload(csrfInput.value);
    });
  }

  if (settingsForm instanceof HTMLFormElement) {
    settingsForm.addEventListener("submit", (event) => {
      if (!validateSettingsForm()) {
        event.preventDefault();
      }
    });
  }

  if (refreshStatsButton instanceof HTMLButtonElement) {
    refreshStatsButton.addEventListener("click", () => {
      void loadStats(true);
    });
  }
});
