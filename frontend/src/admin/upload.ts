import { fetchJson } from "../http";

import { requireElement } from "./dom";
import { resolveAdminErrorMessage } from "./errors";
import type { PublicDownloadUploadResponse, UploadResponse } from "./types";

type AdminUploadActions = {
  bindUpload(): void;
  bindPublicDownloadUpload(): void;
};

export function createAdminUploadActions(csrfToken: string): AdminUploadActions {
  async function handleUpload(): Promise<void> {
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
      const message = resolveAdminErrorMessage(error, "업로드에 실패했습니다.");
      status.innerText = `오류 발생: ${message}`;
    }
  }

  async function handlePublicDownloadUpload(): Promise<void> {
    const fileInput = requireElement("publicDownloadFile", HTMLInputElement);
    const status = requireElement("publicDownloadStatus", HTMLDivElement);

    if (!fileInput || !status) {
      return;
    }

    const file = fileInput.files?.[0];
    if (!file) {
      alert("다운로드 파일을 선택해주세요.");
      return;
    }

    const formData = new FormData();
    formData.append("file", file);
    formData.append("csrf_token", csrfToken);

    status.style.color = "black";

    try {
      status.innerText = "다운로드 파일 업로드 중...";
      const result = await fetchJson<PublicDownloadUploadResponse>("/admin/public-download/upload", {
        method: "POST",
        body: formData,
        timeoutMs: 45000
      });
      status.style.color = "green";
      status.innerText = result.filename ? `업로드 완료: ${result.filename}` : "업로드가 완료되었습니다.";
    } catch (error) {
      status.style.color = "red";
      const message = resolveAdminErrorMessage(error, "다운로드 파일 업로드에 실패했습니다.");
      status.innerText = `오류 발생: ${message}`;
    }
  }

  return {
    bindUpload(): void {
      const uploadButton = document.getElementById("uploadBtn");
      if (!uploadButton) {
        return;
      }
      uploadButton.addEventListener("click", () => {
        void handleUpload();
      });
    },
    bindPublicDownloadUpload(): void {
      const publicDownloadUploadButton = document.getElementById("publicDownloadUploadBtn");
      if (!publicDownloadUploadButton) {
        return;
      }
      publicDownloadUploadButton.addEventListener("click", () => {
        void handlePublicDownloadUpload();
      });
    }
  };
}
