// src/api/system.ts
import { api } from "./client";
import type { HardwareStats, SystemCheckResult } from "@/types/system";

export const systemApi = {
  getStats: ()                        => api.get<HardwareStats>("/api/system/stats"),
  getCheck: ()                        => api.get<SystemCheckResult>("/api/system/check"),
  setPollRate: (interval_ms: number)  => api.put<{ interval_ms: number }>(`/api/system/poll?interval_ms=${interval_ms}`),
};
