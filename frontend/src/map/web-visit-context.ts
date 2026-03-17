type VisitContext = {
  pagePath: string;
  pageQuery: string | null;
  clientLang: string | null;
  platform: string | null;
  referrerUrl: string | null;
  referrerDomain: string | null;
  utmSource: string | null;
  utmMedium: string | null;
  utmCampaign: string | null;
  utmTerm: string | null;
  utmContent: string | null;
  screenWidth: number | null;
  screenHeight: number | null;
  viewportWidth: number | null;
  viewportHeight: number | null;
};

function normalizeReferrerUrl(raw: string): string | null {
  const value = raw.trim();
  if (!value) {
    return null;
  }
  try {
    const parsed = new URL(value);
    parsed.search = "";
    parsed.hash = "";
    return `${parsed.origin}${parsed.pathname}`.slice(0, 1024);
  } catch {
    return null;
  }
}

function extractReferrerDomain(referrerUrl: string | null): string | null {
  if (!referrerUrl) {
    return null;
  }
  try {
    return new URL(referrerUrl).hostname.toLowerCase() || null;
  } catch {
    return null;
  }
}

function pickString(value: string | null, maxLength: number): string | null {
  if (!value) {
    return null;
  }
  const trimmed = value.trim();
  if (!trimmed) {
    return null;
  }
  return trimmed.slice(0, maxLength);
}

function readViewportDimension(value: number): number | null {
  if (!Number.isFinite(value) || value <= 0) {
    return null;
  }
  return Math.round(value);
}

export function getClientTz(): string {
  const tz = Intl.DateTimeFormat().resolvedOptions().timeZone;
  return tz || "UTC";
}

export function buildWebVisitContext(): VisitContext {
  const params = new URLSearchParams(window.location.search);
  const referrerUrl = normalizeReferrerUrl(document.referrer);
  const pagePath = window.location.pathname || "/";
  const pageQuery = pickString(window.location.search.replace(/^\?/, ""), 1024);

  return {
    pagePath,
    pageQuery,
    clientLang: pickString(navigator.language || null, 64),
    platform: pickString(navigator.platform || null, 64),
    referrerUrl,
    referrerDomain: extractReferrerDomain(referrerUrl),
    utmSource: pickString(params.get("utm_source"), 256),
    utmMedium: pickString(params.get("utm_medium"), 256),
    utmCampaign: pickString(params.get("utm_campaign"), 256),
    utmTerm: pickString(params.get("utm_term"), 256),
    utmContent: pickString(params.get("utm_content"), 256),
    screenWidth: readViewportDimension(window.screen.width),
    screenHeight: readViewportDimension(window.screen.height),
    viewportWidth: readViewportDimension(window.innerWidth),
    viewportHeight: readViewportDimension(window.innerHeight)
  };
}

export type { VisitContext };
