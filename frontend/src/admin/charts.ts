declare const Chart: any;

import { requireElement } from "./dom";
import type { StatsResponse, WebStatsResponse } from "./types";

type AdminCharts = {
  renderStatsCharts(payload: StatsResponse): void;
  renderWebStatsChart(payload: WebStatsResponse): void;
  destroyAll(): void;
};

export function createAdminCharts(): AdminCharts {
  let regionChart: any = null;
  let minAreaChart: any = null;
  let trendChart: any = null;
  let webTrendChart: any = null;

  function destroyChart(chart: any): void {
    if (chart) {
      chart.destroy();
    }
  }

  return {
    renderStatsCharts(payload: StatsResponse): void {
      const regionCanvas = requireElement("statsRegionChart", HTMLCanvasElement);
      const minAreaCanvas = requireElement("statsMinAreaChart", HTMLCanvasElement);
      const trendCanvas = requireElement("statsTrendChart", HTMLCanvasElement);

      destroyChart(regionChart);
      destroyChart(minAreaChart);
      destroyChart(trendChart);
      regionChart = null;
      minAreaChart = null;
      trendChart = null;

      if (regionCanvas) {
        regionChart = new Chart(regionCanvas, {
          type: "bar",
          data: {
            labels: payload.topRegions.map((item) => item.region),
            datasets: [{ label: "검색 수", data: payload.topRegions.map((item) => item.count), backgroundColor: "#3b82f6" }]
          },
          options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: { y: { beginAtZero: true, grace: "5%", ticks: { precision: 0 } } }
          }
        });
      }

      if (minAreaCanvas) {
        minAreaChart = new Chart(minAreaCanvas, {
          type: "bar",
          data: {
            labels: payload.topMinAreaBuckets.map((item) => item.bucket),
            datasets: [{ label: "검색 수", data: payload.topMinAreaBuckets.map((item) => item.count), backgroundColor: "#16a34a" }]
          },
          options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: { y: { beginAtZero: true, grace: "5%", ticks: { precision: 0 } } }
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
            scales: { y: { beginAtZero: true, grace: "5%", ticks: { precision: 0 } } }
          }
        });
      }
    },
    renderWebStatsChart(payload: WebStatsResponse): void {
      const canvas = requireElement("webStatsTrendChart", HTMLCanvasElement);
      if (!canvas) {
        return;
      }
      destroyChart(webTrendChart);
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
          scales: { y: { beginAtZero: true, grace: "5%" } }
        }
      });
    },
    destroyAll(): void {
      destroyChart(regionChart);
      destroyChart(minAreaChart);
      destroyChart(trendChart);
      destroyChart(webTrendChart);
      regionChart = null;
      minAreaChart = null;
      trendChart = null;
      webTrendChart = null;
    }
  };
}
