import { HttpError, fetchBlob } from "../http";

function parseFilenameFromDisposition(contentDisposition: string | null): string | null {
  if (!contentDisposition) {
    return null;
  }

  const utf8Match = contentDisposition.match(/filename\\*=UTF-8''([^;]+)/i);
  if (utf8Match && utf8Match[1]) {
    try {
      return decodeURIComponent(utf8Match[1].trim());
    } catch {
      return utf8Match[1].trim();
    }
  }

  const plainMatch = contentDisposition.match(/filename=\"?([^\";]+)\"?/i);
  if (plainMatch && plainMatch[1]) {
    return plainMatch[1].trim();
  }
  return null;
}

export function createDownloadClient() {
  const downloadPreparedFile = async (): Promise<void> => {
    try {
      const { blob, headers } = await fetchBlob("/api/public-download", { method: "GET", timeoutMs: 10000 });
      const disposition = headers.get("content-disposition");
      const fallbackName = "parcel-explorer-download";
      const filename = parseFilenameFromDisposition(disposition) || fallbackName;
      const objectUrl = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = objectUrl;
      anchor.download = filename;
      anchor.style.display = "none";
      document.body.appendChild(anchor);
      anchor.click();
      document.body.removeChild(anchor);
      URL.revokeObjectURL(objectUrl);
    } catch (error) {
      const message = error instanceof HttpError ? error.message : "파일 다운로드 중 오류가 발생했습니다.";
      alert(message);
    }
  };

  return {
    downloadPreparedFile
  };
}

export type DownloadClient = ReturnType<typeof createDownloadClient>;
