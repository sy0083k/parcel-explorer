import { fetchJson } from "../http";

import type { LandFeature, LandsPageResponse } from "./types";

export async function loadAllLandFeatures(): Promise<LandFeature[]> {
  const allFeatures: LandFeature[] = [];
  let cursor: string | null = null;

  while (true) {
    const query = new URLSearchParams({ limit: "500" });
    if (cursor) {
      query.set("cursor", cursor);
    }

    const page = await fetchJson<LandsPageResponse>(`/api/lands?${query.toString()}`, { timeoutMs: 20000 });
    allFeatures.push(...page.features);

    if (!page.nextCursor) {
      break;
    }
    cursor = page.nextCursor;
  }

  return allFeatures;
}
