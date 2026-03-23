// ============================================================
// types/index.ts
// ============================================================

// ── Phase 1 ────────────────────────────────────────────────

export interface SystemStats {
  cpu_pct: number;
  ram_pct: number;
  ram_used_gb: number;
  ram_total_gb: number;
  gpu_pct: number | null;
  gpu_vram_pct: number | null;
  gpu_vram_used: number | null;
  gpu_vram_total: number | null;
  gpu_temp: number | null;
  disk_pct: number;
  disk_free_gb: number;
  ollama_running: boolean;
  db_connected: boolean;
  timestamp: string;
}

export interface CheckResult {
  name: string;
  category: string;
  passed: boolean;
  message: string;
  fix: string;
  critical: boolean;
  warning: boolean;
}

export interface SchemaTable {
  table_name: string;
  estimated_row_count: number | string;
  columns: SchemaColumn[];
  indexes: SchemaIndex[];
}

export interface SchemaColumn {
  name: string;
  type: string;
  nullable: string;
  primary_key: string;
  max_length: number | null;
}

export interface SchemaIndex {
  name: string;
  type: string;
  unique: boolean;
  key_columns: string;
  included_columns: string | null;
}

export interface ViewDefinition {
  view_name: string;
  definition: string;
  referenced_tables: string[];
}

// ── Phase 2 ────────────────────────────────────────────────

export type JobStatus = 'queued' | 'running' | 'complete' | 'failed' | 'cancelled' | 'completed';
export type JobType = 'full_run' | 'analyze' | 'batch' | 'benchmark' | 'sandbox_test' | 'pull_model';

export interface JobRequest {
  type: JobType;
  query?: string;
  folder?: string;
  label?: string;
  benchmark_runs?: number;
  skip_deploy?: boolean;
  safe?: boolean;
  [key: string]: any;
  sql_statements?: string[];
  bak_path?: string;
  threshold_pct?: number;
  model_name?: string;
}

export interface MigrationRef {
  number: number;
  filename: string;
  path: string;
  status: string;
}

export interface JobResult {
  success: boolean;
  optimization?: any;
  benchmark?: {
    before: { avg_ms: number; min_ms: number; max_ms: number; row_count: number };
    after: { avg_ms: number; min_ms: number; max_ms: number; row_count: number };
    improvement_pct: number;
    speedup: number;
    row_mismatch: boolean;
  };
  migration?: MigrationRef | null;
  errors: string[];
  history_id?: number;
  passed?: boolean;
  safe_to_deploy?: boolean;
  model_name?: string;
  status?: string;
}

export interface Job {
  job_id: string;
  status: JobStatus;
  type: JobType;
  created_at: string;
  started_at: string | null;
  finished_at: string | null;
  request: JobRequest;
  result: JobResult | null;
  current_step: number;
  total_steps: number;
  step_label: string;
  log_lines: string[];
  error: string | null;
}

export interface SSEEvent {
  type: 'step' | 'log' | 'complete' | 'error';
  payload?: any;
}

// ── Phase 3 — History & Migrations ─────────────────────────

// Run history record — maps 1:1 to history.db runs table
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
  success: number;   // 1 = success, 0 = failed (SQLite boolean)
}

// History stats — from get_stats()
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

// Trend point — one entry in a trend series (oldest first)
export interface TrendPoint {
  id: number;
  timestamp: string;
  before_ms: number | null;
  after_ms: number | null;
  improvement_pct: number | null;
  label: string | null;
  migration_number: number | null;
}

// Run comparison — diff of two runs
export interface RunComparison {
  run_a: RunRecord;
  run_b: RunRecord;
  diff: {
    before_ms?: { run_a: number; run_b: number; delta: number; direction: string };
    after_ms?: { run_a: number; run_b: number; delta: number; direction: string };
    improvement_pct?: { run_a: number; run_b: number; delta: number; direction: string };
    speedup?: { run_a: number; run_b: number; delta: number; direction: string };
  };
}

// Migration list entry (from registry.json)
export interface Migration {
  number: number;
  filename: string;
  description: string;
  date: string;
  client: string;
  tables_affected: string[];
  reason: string;
  before_ms: number | null;
  after_ms: number | null;
  improvement_pct: number | null;
  status: 'pending' | 'applied' | 'rolled_back';
  applied_to: string[];
  applied_date?: string;
  rollback_date?: string;
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

// ── Phase 4 — Deployment Gate ─────────────────────────────────────────────────

export interface ShadowDB {
  name: string;
  created: string;
  state: string;
  is_orphaned: boolean;
}

export interface SandboxStep {
  number: number;
  label: string;
  status: 'pending' | 'running' | 'passed' | 'failed';
  detail?: string;
}

export interface SandboxResult {
  shadow_name: string;
  passed: boolean;
  safe_to_deploy: boolean;
  errors: string[];
  apply_result?: {
    statements: number;
    failed_count: number;
    results: Array<{
      sql: string;
      success: boolean;
      elapsed_ms?: number;
      error?: string;
    }>;
  };
  regression_result?: {
    passed: boolean;
    threshold_pct: number;
    regressions: Array<{
      label: string;
      reason: string;
      baseline_ms?: number;
      shadow_ms?: number;
      slowdown_pct?: number;
    }>;
  };
}

export interface DeployPreview {
  client: string;
  migrations: Migration[];
  deploy_sql: string;
  rollback_sql: string;
  migration_count: number;
  has_schema_changes: boolean;
}

export interface DeployPackage {
  package_path: string;
  folder_name: string;
  client: string;
  files: string[];
  migrations: Migration[];
  created_at: string;
}

// ── Phase 5 — Model Manager ───────────────────────────────────────────────────

export interface OllamaModel {
  name: string;       // "qwen2.5-coder:14b"
  size: number;       // bytes
  size_gb: string;       // "8.2 GB"
  digest: string;       // sha256 hash prefix
  modified_at: string;       // ISO timestamp
  family?: string;       // "qwen2", "deepseek", etc.
  parameter_size?: string;       // "14B"
  quantization?: string;       // "Q4_K_M"
}

export interface RunningModel {
  name: string;
  size_vram: number;    // bytes
  size_vram_gb: string;   // "8.2 GB"
  expires_at: string;   // ISO timestamp
}

export interface ActiveModels {
  optimizer: string;   // MODELS["optimizer"]
  reasoner: string;   // MODELS["reasoner"]
  optimizer_available: boolean;
  reasoner_available: boolean;
}

export interface PullProgress {
  status: string;
  completed?: number;
  total?: number;
  pct?: number;
}

// ── Phase 5 — Client Manager ──────────────────────────────────────────────────

export interface ClientRecord {
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

export interface ClientConfig {
  name: string;
  display_name: string;
  created: string;
  notes: string;
  db_config: {
    server: string;
    database: string;
    driver: string;
    trusted_connection: string;
    username?: string;
  };
  bak_path: string;
  sandbox_data_dir: string;
  sandbox_timeout: number;
}

export interface ClientPaths {
  name: string;
  base: string;
  migrations: string;
  reports: string;
  deployments: string;
  snapshots: string;
  runs: string;
  history_db: string;
  config_file: string;
}

export interface NewClientRequest {
  name: string;
  display_name?: string;
  server?: string;
  database?: string;
  bak_path?: string;
  notes?: string;
}

export interface UpdateClientRequest {
  display_name?: string;
  server?: string;
  database?: string;
  bak_path?: string;
  notes?: string;
}

// ── Phase 6 — Plan Visualizer ─────────────────────────────────────────────────
// APPEND this block to the bottom of web/src/types/index.ts
// Do NOT remove or rename any existing types above this section.

// Severity of a plan operator problem
export type OperatorSeverity = 'HIGH' | 'MEDIUM' | 'INFO' | null;

// One node in the operator tree (used by D3)
export interface PlanOperator {
  id:         string;          // unique id within this plan (generated)
  name:       string;          // "Nested Loops", "Index Seek", "Table Scan", etc.
  cost:       number;          // EstimatedTotalSubtreeCost
  cost_pct:   number;          // % of total plan cost (0–100)
  est_rows:   number;          // EstimateRows
  act_rows:   number | null;   // ActualRows (only in actual plans)
  severity:   OperatorSeverity;
  reason:     string;          // e.g. "Entire table read — no index used"
  // index / object info when present
  object?:    string;          // table or index name
  seek_pred?: string;          // seek predicates summary
  children:   PlanOperator[];  // direct children in tree
}

// Warning from the plan (implicit conversions, no join predicate, tempdb spill)
export interface PlanWarning {
  type:   string;   // "ImplicitConversion" | "NoJoinPredicate" | "TempDbSpill"
  detail: string;
}

// Missing index hint emitted by SQL Server
export interface MissingIndexHint {
  impact:  string;   // e.g. "87.5"
  columns: string[]; // e.g. ["EQUALITY(machine_id)", "INCLUDE(value, timestamp)"]
}

// Full structured plan returned by the bridge
export interface StructuredPlan {
  plan_type:        'actual' | 'estimated';
  elapsed_ms:       number | null;
  row_count:        number | null;
  total_cost:       number;
  operator_count:   number;
  tree:             PlanOperator;     // root of the operator tree
  warnings:         PlanWarning[];
  missing_indexes:  MissingIndexHint[];
  // flat lists for summary panels
  flagged:          Array<PlanOperator & { severity: 'HIGH' | 'MEDIUM' | 'INFO' }>;
  query:            string;           // the original query analyzed
}

// Request body for plan analysis from query
export interface PlanFromQueryRequest {
  query:  string;
  actual: boolean;   // true = run query and get actual plan; false = estimated only
}
