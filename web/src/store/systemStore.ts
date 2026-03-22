// src/store/systemStore.ts
import { create } from "zustand";
import type { HardwareStats } from "@/types/system";

interface SystemStore {
  stats: HardwareStats | null;
  lastUpdated: Date | null;
  isInference: boolean;   // true while a job is running → 500ms poll

  setStats:     (stats: HardwareStats) => void;
  setInference: (v: boolean)           => void;
}

export const useSystemStore = create<SystemStore>((set) => ({
  stats:        null,
  lastUpdated:  null,
  isInference:  false,

  setStats: (stats) => set({ stats, lastUpdated: new Date() }),
  setInference: (v) => set({ isInference: v }),
}));
