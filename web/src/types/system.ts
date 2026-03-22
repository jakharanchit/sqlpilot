// src/types/system.ts

export interface GpuStats {
  name: string;
  vram_usage_mb: number;
  vram_total_mb: number;
  vram_pct: number;
  utilization_pct: number;
  source: "pynvml" | "nvidia-smi";
}

export interface OllamaStatus {
  status: "online" | "offline";
  active_models: string[];
  url: string;
}

export interface DbStatus {
  status: "online" | "offline" | "error";
  database: string;
  server: string;
  error: string | null;
}

export interface HardwareStats {
  cpu_usage: number;
  ram_usage_mb: number;
  ram_total_mb: number;
  ram_pct: number;
  gpu: GpuStats | null;
  gpu_source: "pynvml" | "nvidia-smi" | "unavailable";
  ollama: OllamaStatus;
  db: DbStatus;
}

export interface CheckResult {
  name: string;
  category: string;
  passed: boolean;
  warning: boolean;
  critical: boolean;
  message: string;
  fix: string;
}

export interface SystemCheckResult {
  passed: boolean;
  critical_failures: number;
  warnings: number;
  checks: CheckResult[];
}
