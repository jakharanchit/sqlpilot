// src/hooks/useSystemStats.ts
import { useCallback } from "react";
import { systemApi } from "@/api/system";
import { useSystemStore } from "@/store/systemStore";
import { useInterval } from "./useInterval";

/**
 * Polls /api/system/stats at:
 *   2000ms  when idle
 *    500ms  while a job is running (isInference = true)
 *
 * Also tells the bridge to adjust its background poll rate to match.
 */
export function useSystemStats() {
  const { setStats, isInference } = useSystemStore();
  const delay = isInference ? 500 : 2000;

  const fetch = useCallback(async () => {
    try {
      const stats = await systemApi.getStats();
      setStats(stats);
    } catch {
      // silently fail — UI shows last known state
    }
  }, [setStats]);

  // Kick off immediately on mount
  useInterval(fetch, delay);

  return useSystemStore((s) => s.stats);
}
