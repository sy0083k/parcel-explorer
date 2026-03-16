import { HttpError, fetchJson } from "../http";

import { requireElement } from "./dom";
import type { GeomRefreshStartResponse, GeomRefreshStatusResponse } from "./types";

type GeomRefreshController = {
  bindRefreshButton(): void;
};

type ReloadStats = (force?: boolean) => Promise<void>;

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => window.setTimeout(resolve, ms));
}

export function createGeomRefreshController(csrfToken: string, reloadStats: ReloadStats): GeomRefreshController {
  let isPolling = false;
  let currentJobId: number | null = null;

  async function poll(jobId: number): Promise<void> {
    if (isPolling && currentJobId === jobId) {
      return;
    }

    const status = requireElement("geomRefreshStatus", HTMLDivElement);
    const triggerBtn = requireElement("refreshGeomBtn", HTMLButtonElement);
    if (!status || !triggerBtn) {
      return;
    }

    isPolling = true;
    currentJobId = jobId;
    triggerBtn.disabled = true;

    const maxPollCount = 300;
    const pollIntervalMs = 2000;

    try {
      for (let idx = 0; idx < maxPollCount; idx += 1) {
        const payload = await fetchJson<GeomRefreshStatusResponse>(`/admin/lands/geom-refresh/${jobId}`, {
          timeoutMs: 10000
        });
        const job = payload.job;

        if (job.status === "pending" || job.status === "running") {
          status.style.color = "#6b7280";
          status.innerText = `경계선 수집 작업 진행 중... (작업 ID: ${job.id}, 시도: ${job.attempts})`;
          await sleep(pollIntervalMs);
          continue;
        }

        if (job.status === "done") {
          status.style.color = "#16a34a";
          status.innerText = `작업 완료 (갱신 ${job.updatedCount}건, 미갱신 ${job.failedCount}건)`;
          await reloadStats(true);
          return;
        }

        if (job.status === "failed") {
          const suffix = job.errorMessage ? `: ${job.errorMessage}` : "";
          status.style.color = "#dc2626";
          status.innerText = `작업 실패${suffix}`;
          await reloadStats(true);
          return;
        }

        status.style.color = "#dc2626";
        status.innerText = `알 수 없는 작업 상태: ${job.status}`;
        return;
      }

      status.style.color = "#dc2626";
      status.innerText = "작업 상태 확인 시간이 초과되었습니다. 잠시 후 다시 시도해주세요.";
    } catch (error) {
      const message = error instanceof HttpError ? error.message : "작업 상태를 불러오지 못했습니다.";
      status.style.color = "#dc2626";
      status.innerText = message;
    } finally {
      isPolling = false;
      currentJobId = null;
      triggerBtn.disabled = false;
    }
  }

  async function start(): Promise<void> {
    const status = requireElement("geomRefreshStatus", HTMLDivElement);
    const triggerBtn = requireElement("refreshGeomBtn", HTMLButtonElement);
    if (!status || !triggerBtn) {
      return;
    }

    triggerBtn.disabled = true;
    status.style.color = "#6b7280";
    status.innerText = "경계선 수집 작업을 시작하는 중...";

    try {
      const formData = new FormData();
      formData.append("csrf_token", csrfToken);
      const payload = await fetchJson<GeomRefreshStartResponse>("/admin/lands/geom-refresh", {
        method: "POST",
        body: formData,
        timeoutMs: 10000
      });
      status.style.color = "#6b7280";
      status.innerText = `${payload.message} (작업 ID: ${payload.jobId})`;
      await poll(payload.jobId);
    } catch (error) {
      const message = error instanceof HttpError ? error.message : "작업 시작에 실패했습니다.";
      status.style.color = "#dc2626";
      status.innerText = message;
      triggerBtn.disabled = false;
    }
  }

  return {
    bindRefreshButton(): void {
      const refreshGeomButton = requireElement("refreshGeomBtn", HTMLButtonElement);
      if (!refreshGeomButton) {
        return;
      }
      refreshGeomButton.addEventListener("click", () => {
        void start();
      });
    }
  };
}
