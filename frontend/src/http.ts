export class HttpError extends Error {
  status: number;

  constructor(message: string, status = 0) {
    super(message);
    this.name = "HttpError";
    this.status = status;
  }
}

function normalizeErrorMessage(payload: unknown, fallback: string): string {
  if (payload && typeof payload === "object") {
    const rec = payload as Record<string, unknown>;
    if (typeof rec.message === "string" && rec.message.trim()) {
      return rec.message;
    }
    if (typeof rec.detail === "string" && rec.detail.trim()) {
      return rec.detail;
    }
  }
  return fallback;
}

export async function fetchJson<T>(
  input: RequestInfo | URL,
  init?: RequestInit & { timeoutMs?: number }
): Promise<T> {
  const timeoutMs = init?.timeoutMs ?? 10000;
  const controller = new AbortController();
  const timer = window.setTimeout(() => controller.abort(), timeoutMs);

  try {
    const response = await fetch(input, {
      ...init,
      signal: controller.signal
    });

    const text = await response.text();
    const payload = text ? (JSON.parse(text) as unknown) : {};

    if (!response.ok) {
      throw new HttpError(normalizeErrorMessage(payload, `요청 실패 (${response.status})`), response.status);
    }

    return payload as T;
  } catch (error) {
    if (error instanceof HttpError) {
      throw error;
    }
    if (error instanceof DOMException && error.name === "AbortError") {
      throw new HttpError("요청 시간이 초과되었습니다.");
    }
    if (error instanceof SyntaxError) {
      throw new HttpError("서버 응답 형식이 올바르지 않습니다.");
    }
    throw new HttpError("네트워크 오류가 발생했습니다.");
  } finally {
    window.clearTimeout(timer);
  }
}

export async function fetchBlob(
  input: RequestInfo | URL,
  init?: RequestInit & { timeoutMs?: number }
): Promise<{ blob: Blob; headers: Headers }> {
  const timeoutMs = init?.timeoutMs ?? 10000;
  const controller = new AbortController();
  const timer = window.setTimeout(() => controller.abort(), timeoutMs);

  try {
    const response = await fetch(input, {
      ...init,
      signal: controller.signal
    });

    if (!response.ok) {
      const text = await response.text();
      let payload: unknown = {};
      if (text) {
        try {
          payload = JSON.parse(text) as unknown;
        } catch {
          payload = {};
        }
      }
      throw new HttpError(normalizeErrorMessage(payload, `요청 실패 (${response.status})`), response.status);
    }

    return { blob: await response.blob(), headers: response.headers };
  } catch (error) {
    if (error instanceof HttpError) {
      throw error;
    }
    if (error instanceof DOMException && error.name === "AbortError") {
      throw new HttpError("요청 시간이 초과되었습니다.");
    }
    throw new HttpError("네트워크 오류가 발생했습니다.");
  } finally {
    window.clearTimeout(timer);
  }
}
