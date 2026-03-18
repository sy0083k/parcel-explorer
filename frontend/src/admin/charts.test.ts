import { describe, expect, test, vi } from "vitest"

import { createAdminCharts } from "./charts"
import type { StatsResponse, WebStatsResponse } from "./types"

function buildStatsPayload(): StatsResponse {
  return {
    summary: {
      searchCount: 3,
      clickCount: 2,
      uniqueSessionCount: 1,
    },
    landSummary: {
      totalLands: 10,
      missingGeomLands: 1,
    },
    topRegions: [{ region: "예천동", count: 3 }],
    topMinAreaBuckets: [{ bucket: "100", count: 2 }],
    topClickedLands: [{ address: "충남 서산시 예천동 100-1", clickCount: 2, uniqueSessionCount: 1 }],
    dailyTrend: [{ date: "2026-03-18", searchCount: 3, clickCount: 2 }],
  }
}

function buildWebStatsPayload(): WebStatsResponse {
  return {
    summary: {
      dailyVisitors: 5,
      totalVisitors: 10,
      avgDwellMinutes: 3.5,
      sessionCount: 7,
    },
    dailyTrend: [{ date: "2026-03-18", visitors: 5, sessions: 7, avgDwellMinutes: 3.5 }],
  }
}

function mountChartCanvases(): void {
  document.body.innerHTML = `
    <canvas id="statsRegionChart"></canvas>
    <canvas id="statsMinAreaChart"></canvas>
    <canvas id="statsTrendChart"></canvas>
    <canvas id="webStatsTrendChart"></canvas>
  `
}

describe("createAdminCharts", () => {
  test("does not throw when Chart global is unavailable", () => {
    mountChartCanvases()
    delete window.Chart
    const charts = createAdminCharts()

    expect(() => charts.renderStatsCharts(buildStatsPayload())).not.toThrow()
    expect(() => charts.renderWebStatsChart(buildWebStatsPayload())).not.toThrow()
    expect(() => charts.destroyAll()).not.toThrow()
  })

  test("creates charts for stats and web payloads when Chart global exists", () => {
    mountChartCanvases()
    const constructorSpy = vi.fn()

    class ChartStub {
      destroy = vi.fn()

      constructor(_canvas: HTMLCanvasElement, _config: unknown) {
        constructorSpy(_canvas, _config)
      }
    }

    window.Chart = ChartStub as unknown as Window["Chart"]

    const charts = createAdminCharts()
    charts.renderStatsCharts(buildStatsPayload())
    charts.renderWebStatsChart(buildWebStatsPayload())

    expect(constructorSpy).toHaveBeenCalledTimes(4)
  })

  test("destroys previous chart instances on rerender and destroyAll", () => {
    mountChartCanvases()
    const destroySpies: Array<ReturnType<typeof vi.fn>> = []
    const constructorSpy = vi.fn()

    class ChartStub {
      destroy: ReturnType<typeof vi.fn>

      constructor(_canvas: HTMLCanvasElement, _config: unknown) {
        constructorSpy(_canvas, _config)
        this.destroy = vi.fn()
        destroySpies.push(this.destroy)
      }
    }

    window.Chart = ChartStub as unknown as Window["Chart"]

    const charts = createAdminCharts()
    charts.renderStatsCharts(buildStatsPayload())
    charts.renderWebStatsChart(buildWebStatsPayload())
    charts.renderStatsCharts(buildStatsPayload())
    charts.destroyAll()

    expect(constructorSpy).toHaveBeenCalledTimes(7)
    expect(destroySpies[0]).toHaveBeenCalledTimes(1)
    expect(destroySpies[1]).toHaveBeenCalledTimes(1)
    expect(destroySpies[2]).toHaveBeenCalledTimes(1)
    expect(destroySpies[3]).toHaveBeenCalledTimes(1)
    expect(destroySpies[4]).toHaveBeenCalledTimes(1)
    expect(destroySpies[5]).toHaveBeenCalledTimes(1)
    expect(destroySpies[6]).toHaveBeenCalledTimes(1)
  })
})
