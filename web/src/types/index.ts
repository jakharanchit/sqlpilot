// ============================================================
// types/index.ts
// All shared TypeScript types for the SQL Optimization Agent UI.
// Phase 1 + Phase 2 types — DO NOT REMOVE
// Phase 3 types appended at bottom
// ============================================================

// ── Phase 1 ────────────────────────────────────────────────

export interface SystemStats {
  cpu_pct:        number;
  ram_pct:        number;
  ram_used_gb:    number;
  ram_total_gb:   number;
  gpu_pct:        number | null;
  gpu_vram_pct:   number | null;
  gpu_vram_used:  number | null;
  gpu_vram_total: number | null;
  gpu_temp:       number | null;
  disk_pct:       number;
  disk_free_gb:   number;
  ollama_running: boolean;
  db_connected:   boolean;
  timestamp:      string;
}

export interface CheckResult {
  name:     string;
  category: string;
  passed:   boolean;
  message:  string;
  fix:      string;
  critical: boolean;
  warning:  boolean;
}

export interface SchemaTable {
  table_name:           string;
  estimated_row_count:  number | string;
  columns:              SchemaColumn[];
  indexes:              SchemaIndex[];
}

export interface SchemaColumn {
  name:        string;
  type:        string;
  nullable:    string;
  primary_key: string;
  max_length:  number | null;
}

export interface SchemaIndex {
  name:             string;
  type:             string;
  unique:           boolean;
  key_columns:      string;
  included_columns: string | null;
}

export interface ViewDefinition {
  view_name:          string;
  definition:         string;
  referenced_tables:  string[];
}

// ── Phase 2 ────────────────────────────────────────────────

export type JobStatus = 'queued' | 'running' | 'complete' | 'failed' | 'cancelled' | 'completed';
export type JobType   = 'full_run' | 'analyze' | 'batch' | 'benchmark';

export interface JobRequest {
  type:            JobType;
  query?:          string;
  folder?:         string;
  label?:          string;
  benchmark_runs?: number;
  skip_deploy?:    boolean;
  safe?:           boolean;
  [key: string]: any;
}

export interface MigrationRef {
  number:   number;
  filename: string;
  path:     string;
  status:   string;
}

export interface JobResult {
  success:        boolean;
  optimization?:  any;
  benchmark?: {
    before:           { avg_ms: number; min_ms: number; max_ms: number; row_count: number };
    after:            { avg_ms: number; min_ms: number; max_ms: number; row_count: number };
    improvement_pct:  number;
    speedup:          number;
    row_mismatch:     boolean;
  };
  migration?:     MigrationRef | null;
  errors:         string[];
  history_id?:    number;
}

export interface Job {
  job_id:       string;
  status:       JobStatus;
  type:         JobType;
  created_at:   string;
  started_at:   string | null;
  finished_at:  string | null;
  request:      JobRequest;
  result:       JobResult | null;
  current_step: number;
  total_steps:  number;
  step_label:   string;
  log_lines:    string[];
  error:        string | null;
}

export interface SSEEvent {
  type:    'step' | 'log' | 'complete' | 'error';
  payload?: any;
}

// ── Phase 3 — History & Migrations ─────────────────────────

// Run history record — maps 1:1 to history.db runs table
export interface RunRecord {
  id:               number;
  timestamp:        string;
  client:           string;
  run_type:         string;
  label:            string | null;
  query_preview:    string | null;
  tables_involved:  string | null;
  before_ms:        number | null;
  after_ms:         number | null;
  improvement_pct:  number | null;
  speedup:          number | null;
  migration_number: number | null;
  success:          number;   // 1 = success, 0 = failed (SQLite boolean)
}

// History stats — from get_stats()
export interface HistoryStats {
  total_runs:        number;
  successful_runs:   number;
  avg_improvement:   number | null;
  best_improvement:  number | null;
  worst_improvement: number | null;
  total_migrations:  number;
  queries_tracked:   number;
  tables_touched:    number;
}

// Trend point — one entry in a trend series (oldest first)
export interface TrendPoint {
  id:               number;
  timestamp:        string;
  before_ms:        number | null;
  after_ms:         number | null;
  improvement_pct:  number | null;
  label:            string | null;
  migration_number: number | null;
}

// Run comparison — diff of two runs
export interface RunComparison {
  run_a: RunRecord;
  run_b: RunRecord;
  diff: {
    before_ms?:       { run_a: number; run_b: number; delta: number; direction: string };
    after_ms?:        { run_a: number; run_b: number; delta: number; direction: string };
    improvement_pct?: { run_a: number; run_b: number; delta: number; direction: string };
    speedup?:         { run_a: number; run_b: number; delta: number; direction: string };
  };
}

// Migration list entry (from registry.json)
export interface Migration {
  number:          number;
  filename:        string;
  description:     string;
  date:            string;
  client:          string;
  tables_affected: string[];
  reason:          string;
  before_ms:       number | null;
  after_ms:        number | null;
  improvement_pct: number | null;
  status:          'pending' | 'applied' | 'rolled_back';
  applied_to:      string[];
  applied_date?:   string;
  rollback_date?:  string;
}

// ── Missing Types added for TS compilation ─────────────────
export type JobDetail = Job;
export type JobSummary = Job;

export interface LogLine {
  line: string;
  ts?: string;
  kind: 'log' | 'step' | 'error' | 'success' | 'warn' | 'info' | 'dim' | 'section';
}

export type SSEStepEvent = {
  type: 'step';
  step: number;
  total: number;
  label: string;
};

export type SSELogEvent = {
  type: 'log';
  line: string;
  ts?: string;
};

export type AnalyzeParams = any;
export type FullRunParams = any;
export type BenchmarkParams = any;

export interface ClientSummary {
  name: string;
  display_name?: string;
  server?: string;
  database?: string;
}
