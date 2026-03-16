export type UploadResponse = {
  success: boolean;
  total?: number;
  message: string;
  geomJobId?: number;
};

export type PublicDownloadUploadResponse = {
  success: boolean;
  message: string;
  filename?: string;
  uploadedAt?: string;
};

export type StatsResponse = {
  summary: {
    searchCount: number;
    clickCount: number;
    uniqueSessionCount: number;
  };
  landSummary: {
    totalLands: number;
    missingGeomLands: number;
  };
  topRegions: Array<{ region: string; count: number }>;
  topMinAreaBuckets: Array<{ bucket: string; count: number }>;
  topClickedLands: Array<{ address: string; clickCount: number; uniqueSessionCount: number }>;
  dailyTrend: Array<{ date: string; searchCount: number; clickCount: number }>;
};

export type WebStatsResponse = {
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

export type GeomRefreshStartResponse = {
  success: boolean;
  jobId: number;
  started: boolean;
  message: string;
};

export type GeomRefreshStatusResponse = {
  success: boolean;
  job: {
    id: number;
    status: string;
    attempts: number;
    updatedCount: number;
    failedCount: number;
    errorMessage: string;
    createdAt: string;
    updatedAt: string;
  };
};
