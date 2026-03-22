// ── System types ─────────────────────────────────────────────────────────────

export interface HardwareStats {
  cpu_pct:       number;
  ram_used_gb:   number;
  ram_total_gb:  number;
  ram_pct:       number;
  gpu_pct:       number | null;
  vram_used_gb:  number | null;
  vram_total_gb: number | null;
  vram_pct:      number | null;
  gpu_name:      string | null;
  inference_active: boolean;
  polled_at:     string;
}

export interface SystemCheck {
  db_connected:    boolean;
  ollama_running:  boolean;
  models_ready:    boolean;
  active_client:   string;
  warnings:        string[];
  errors:          string[];
}

// ── Schema types ─────────────────────────────────────────────────────────────

export interface ColumnDef {
  name:        string;
  type:        string;
  nullable:    string;
  primary_key: string;
  max_length:  number | null;
}

export interface IndexDef {
  name:             string;
  type:             string;
  unique:           boolean;
  key_columns:      string;
  included_columns: string | null;
}

export interface TableSchema {
  table_name:           string;
  columns:              ColumnDef[];
  indexes:              IndexDef[];
  estimated_row_count:  number | string;
}

export interface ViewDef {
  view_name:         string;
  definition:        string;
  referenced_tables: string[];
}

// ── Client types ──────────────────────────────────────────────────────────────

export interface ClientSummary {
  name:         string;
  display_name: string;
  database:     string;
  server:       string;
  migrations:   number;
  runs:         number;
  active:       boolean;
  created:      string;
}

// ── History types ─────────────────────────────────────────────────────────────

export interface RunRecord {
  id:              number;
  timestamp:       string;
  client:          string;
  run_type:        string;
  label:           string | null;
  query_preview:   string | null;
  tables_involved: string | null;
  before_ms:       number | null;
  after_ms:        number | null;
  improvement_pct: number | null;
  speedup:         number | null;
  migration_number: number | null;
  success:         number;
}

// ── Job types ─────────────────────────────────────────────────────────────────

export type JobType =
  | "full_run"
  | "analyze"
  | "benchmark"
  | "sandbox_test"
  | "watch"
  | "deploy";

export type JobStatus =
  | "queued"
  | "running"
  | "completed"
  | "failed"
  | "cancelled";

export interface JobSummary {
  job_id:       string;
  type:         JobType;
  status:       JobStatus;
  created_at:   string;
  started_at:   string | null;
  completed_at: string | null;
  error:        string | null;
  current_step: number;
  total_steps:  number;
  step_label:   string;
}

export interface JobDetail extends JobSummary {
  params: Record<string, any>;
  result: JobResult | null;
}

export interface JobResult {
  success:      boolean;
  optimization?: OptimizationResult;
  benchmark?:   BenchmarkResult;
  migration?:   MigrationRef;
  report_path?: string;
  errors?:      string[];
}

export interface OptimizationResult {
  original_query:   string;
  optimized_query:  string;
  diagnosis:        string;
  index_scripts:    string[];
  log_path?:        string;
  migration?:       MigrationRef;
}

export interface BenchmarkResult {
  label:           string;
  before: {
    avg_ms:   number;
    min_ms:   number;
    max_ms:   number;
    p50_ms:   number;
    std_ms:   number;
    row_count: number;
  };
  after: {
    avg_ms:   number;
    min_ms:   number;
    max_ms:   number;
    p50_ms:   number;
    std_ms:   number;
    row_count: number;
  };
  improvement_pct: number;
  speedup:         number;
  row_mismatch:    boolean;
}

export interface MigrationRef {
  number:   number;
  filename: string;
  path:     string;
  status:   string;
}

// ── SSE event types ───────────────────────────────────────────────────────────

export interface SSELogEvent {
  type: "log";
  line: string;
  ts:   string;
}

export interface SSEStepEvent {
  type:  "step";
  step:  number;
  total: number;
  label: string;
}

export interface SSECompleteEvent {
  type:   "complete";
  result: JobResult;
}

export interface SSEErrorEvent {
  type:    "error";
  message: string;
}

export interface SSEPingEvent {
  type: "ping";
}

export type SSEEvent =
  | SSELogEvent
  | SSEStepEvent
  | SSECompleteEvent
  | SSEErrorEvent
  | SSEPingEvent;

// ── Log line (frontend display) ───────────────────────────────────────────────

export interface LogLine {
  line: string;
  ts:   string;
  kind: "log" | "step" | "error";
}

// ── Job submit params ─────────────────────────────────────────────────────────

export interface FullRunParams {
  query:          string;
  label?:         string;
  benchmark_runs?: number | null;
  safe?:          boolean;
  no_deploy?:     boolean;
}

export interface AnalyzeParams {
  query: string;
  label?: string;
}

export interface BenchmarkParams {
  before: string;
  after:  string;
  label?: string;
  runs?:  number;
}
