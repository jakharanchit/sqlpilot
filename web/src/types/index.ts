// src/types/client.ts
export interface ClientSummary {
  name: string;
  display_name: string;
  created: string;
  database: string;
  server: string;
  bak_path: string;
  migrations: number;
  runs: number;
  active: boolean;
}

// src/types/history.ts — stub for Phase 3
export interface RunRecord {
  id: number;
  timestamp: string;
  client: string;
  run_type: string;
  label: string | null;
  query_preview: string | null;
  tables_involved: string | null;
  before_ms: number | null;
  after_ms: number | null;
  improvement_pct: number | null;
  speedup: number | null;
  migration_number: number | null;
  success: number;
}

export interface HistoryStats {
  total_runs: number;
  successful_runs: number;
  avg_improvement: number | null;
  best_improvement: number | null;
  worst_improvement: number | null;
  total_migrations: number;
  queries_tracked: number;
  tables_touched: number;
}

// src/types/job.ts — stub for Phase 2
export type JobType =
  | "full_run" | "batch_run" | "analyze"
  | "benchmark" | "sandbox_test" | "watch" | "deploy";

export type JobStatus =
  | "pending" | "running" | "completed" | "failed" | "cancelled";

export interface JobSummary {
  job_id: string;
  type: JobType;
  status: JobStatus;
  params: Record<string, unknown>;
  result: Record<string, unknown> | null;
  error: string | null;
  created_at: string;
  started_at: string | null;
  completed_at: string | null;
  client: string;
}
