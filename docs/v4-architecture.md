# SQL Optimization Agent — V4 Web UI Architecture
> Complete technical specification. All decisions locked. Build from this document.
> Generated: 2026-03-21

---

## 1. Decisions Summary

| Concern | Decision | Rationale |
|---|---|---|
| Frontend framework | React 18 + Vite | Right-sized for localhost tool, D3 compatible |
| Styling | Tailwind CSS | Dark/light themes trivial, utility-first speed |
| Charts / Gauges | Recharts | Simpler than raw D3 for line charts and gauges |
| Plan Visualizer | D3 v7 directly | Full control over tree layout, per spec |
| SQL Diff Editor | Monaco Editor | Best SQL highlighting, bundle size irrelevant |
| State management | Zustand | Minimal boilerplate, no Redux overhead |
| Backend | FastAPI + Uvicorn | Python-native, async, SSE built-in |
| Job execution | Background thread per job + SSE | Existing tools are sync Python — no modification needed |
| Communication | SSE (streaming) + REST (commands/data) | Unidirectional pipeline output, REST for everything else |
| Jobs persistence | Extend history.db — add `jobs` table | Collocated with run history, single DB file |
| VRAM monitoring | pynvml + nvidia-smi subprocess fallback | RTX 5070 not confirmed with pynvml yet |
| Startup | `python agent.py serve` — one command | Spawns uvicorn + vite as subprocesses |
| Auth | None for V4 (localhost only) | Revisit when moving to network/cloud |
| Design | Professional light — enterprise dashboard | Clean, data-dense, not terminal-style |
| Pages | All 8 pages in scope | Full feature parity with CLI |
| Out of scope | Mobile layout, multi-user, cloud, email, PDF, dark/light toggle | Post-V4 |

---

## 2. Repository Structure

```
sql-agent/                              ← existing project root (unchanged)
├── agent.py                            ← ADD: `serve` command at bottom
├── config.py                           ← unchanged
├── tools/                              ← unchanged (all 18 tools)
│
├── bridge/                             ← NEW: FastAPI backend
│   ├── main.py                         ← App factory, CORS, router registration
│   ├── requirements.txt                ← fastapi uvicorn psutil pynvml
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── jobs.py                     ← /api/jobs — create, list, detail, stream, cancel
│   │   ├── system.py                   ← /api/system — stats, health check
│   │   ├── schema.py                   ← /api/schema — tables, views, inspect
│   │   ├── history.py                  ← /api/history — runs, stats, trends, compare
│   │   ├── migrations.py               ← /api/migrations — list, mark applied/rolled-back
│   │   ├── clients.py                  ← /api/clients — list, create, switch, edit
│   │   ├── models.py                   ← /api/models — Ollama inventory, VRAM, preload
│   │   ├── deploy.py                   ← /api/deploy — preview, generate package
│   │   ├── sandbox.py                  ← /api/sandbox — test, list shadows, destroy
│   │   └── settings.py                 ← /api/settings — read/write config.py
│   ├── services/
│   │   ├── __init__.py
│   │   ├── job_queue.py                ← ThreadPoolExecutor, job state machine, log queues
│   │   ├── hardware.py                 ← psutil CPU/RAM + pynvml/nvidia-smi VRAM
│   │   └── sse.py                      ← SSE format helpers, event generators
│   └── schemas/                        ← Pydantic request/response models
│       ├── __init__.py
│       ├── job.py
│       ├── system.py
│       ├── history.py
│       ├── client.py
│       └── settings.py
│
└── web/                                ← NEW: React frontend
    ├── package.json
    ├── vite.config.ts
    ├── tailwind.config.ts
    ├── tsconfig.json
    ├── index.html
    └── src/
        ├── main.tsx
        ├── App.tsx                     ← React Router setup
        ├── api/                        ← Typed API client layer (fetch wrappers)
        │   ├── client.ts               ← base URL, error handling, typed fetch
        │   ├── jobs.ts
        │   ├── system.ts
        │   ├── schema.ts
        │   ├── history.ts
        │   ├── migrations.ts
        │   ├── clients.ts
        │   ├── models.ts
        │   ├── deploy.ts
        │   ├── sandbox.ts
        │   └── settings.ts
        ├── pages/
        │   ├── Dashboard.tsx
        │   ├── Optimizer.tsx
        │   ├── PlanVisualizer.tsx
        │   ├── DeploymentGate.tsx
        │   ├── History.tsx
        │   ├── ModelManager.tsx
        │   ├── ClientManager.tsx
        │   └── Settings.tsx
        ├── components/
        │   ├── layout/
        │   │   ├── Sidebar.tsx         ← Left nav, client switcher, system status dot
        │   │   ├── TopBar.tsx          ← Page title, active client badge, job indicator
        │   │   └── PageShell.tsx       ← Consistent page wrapper with padding/scroll
        │   ├── dashboard/
        │   │   ├── HardwareGauges.tsx  ← CPU/RAM/VRAM ring gauges (Recharts RadialBar)
        │   │   ├── ActiveJobCard.tsx   ← Running job with live step counter
        │   │   ├── RecentRunsPanel.tsx ← Last 5 runs from history
        │   │   └── SystemStatusRow.tsx ← DB / Ollama / Git health badges
        │   ├── optimizer/
        │   │   ├── QueryInput.tsx      ← Monaco SQL editor (submit box)
        │   │   ├── PipelineLog.tsx     ← SSE log stream, auto-scroll terminal
        │   │   ├── StepProgress.tsx    ← 9-step progress bar + current step label
        │   │   └── ResultPanel.tsx     ← Optimized query + index scripts + diff
        │   ├── visualizer/
        │   │   ├── PlanDiffContainer.tsx  ← Side-by-side with shared zoom/pan
        │   │   ├── PlanTree.tsx           ← D3 tree SVG component
        │   │   ├── PlanNode.tsx           ← SVG node card (cost %, operator icon)
        │   │   ├── PlanEdge.tsx           ← Variable-width path by estimateRows
        │   │   ├── planParser.ts          ← XML → PlanNode tree (fast-xml-parser)
        │   │   └── operatorIcons.ts       ← physicalOp → SVG path map
        │   ├── deployment/
        │   │   ├── SandboxPipeline.tsx    ← 5-step lifecycle with state machine UI
        │   │   ├── DeployConfirmModal.tsx ← "Type APPLY_TO_PROD" gate
        │   │   ├── SqlDiffViewer.tsx      ← Monaco diff editor (original vs optimized)
        │   │   └── RollbackPanel.tsx      ← rollback.sql viewer + download
        │   ├── history/
        │   │   ├── RunsTable.tsx          ← Filterable table of all runs
        │   │   ├── TrendChart.tsx         ← Recharts LineChart over time
        │   │   └── ComparePanel.tsx       ← Side-by-side run comparison
        │   ├── models/
        │   │   ├── ModelCard.tsx          ← Name, size, status dot, preload button
        │   │   └── VramBar.tsx            ← Linear VRAM progress bar + alert
        │   ├── clients/
        │   │   ├── ClientList.tsx         ← Table with active indicator
        │   │   └── ClientEditForm.tsx     ← Server/DB/bak path fields
        │   └── shared/
        │       ├── GaugeRing.tsx          ← Recharts RadialBarChart wrapper
        │       ├── StatusBadge.tsx        ← Green/yellow/red pill
        │       ├── CodeBlock.tsx          ← Syntax-highlighted pre with copy button
        │       ├── EmptyState.tsx         ← Consistent empty state pattern
        │       ├── LoadingSpinner.tsx
        │       └── ConfirmDialog.tsx      ← Generic modal for destructive actions
        ├── hooks/
        │   ├── useSSE.ts               ← EventSource wrapper with cleanup
        │   ├── useInterval.ts          ← setInterval with auto-cleanup
        │   ├── useJob.ts               ← Poll job status + manage SSE stream
        │   └── useSystemStats.ts       ← 2s poll during idle, 500ms during inference
        ├── store/                      ← Zustand stores
        │   ├── jobStore.ts             ← active job, log lines, step progress
        │   ├── clientStore.ts          ← active client name, client list
        │   └── systemStore.ts          ← hardware stats, Ollama status
        └── types/
            ├── job.ts
            ├── plan.ts                 ← PlanNode interface (from spec)
            ├── system.ts
            ├── history.ts
            └── client.ts
```

---

## 3. Startup Command

### `python agent.py serve`

Added at the bottom of `agent.py`:

```python
@app.command()
def serve(
    host:      str  = typer.Option("127.0.0.1", "--host", "-h"),
    port:      int  = typer.Option("8000",      "--port", "-p"),
    dev:       bool = typer.Option(True,         "--dev",  help="Run Vite dev server alongside"),
    open_browser: bool = typer.Option(True,      "--open"),
):
    """
    Start the V4 Web UI.
    Launches FastAPI bridge + Vite dev server in one command.
    
    Example:
        python agent.py serve
        python agent.py serve --no-dev   # serve built frontend from FastAPI
    """
```

**Startup sequence:**
1. Start uvicorn in a background thread (bridge)
2. If `--dev`: spawn `npm run dev` in `web/` as a subprocess
3. If `--no-dev`: FastAPI serves `web/dist/` as static files (post `npm run build`)
4. If `--open`: open browser after 2 second delay

**URLs:**
- Dev mode: `http://localhost:5173` (Vite) → proxies `/api/*` to `http://localhost:8000`
- Production build: `http://localhost:8000` (FastAPI serves everything)

---

## 4. FastAPI Bridge — Full API Contract

Base URL: `http://localhost:8000`

All endpoints return `application/json` unless noted.

---

### 4.1 Jobs — `/api/jobs`

The job system is the backbone. Every long-running CLI operation becomes a job.

**Job types:** `full_run` | `batch_run` | `analyze` | `benchmark` | `sandbox_test` | `watch` | `deploy`

**Job statuses:** `pending` → `running` → `completed` | `failed` | `cancelled`

```
POST   /api/jobs                  Create and queue a job
GET    /api/jobs                  List jobs (with filters)
GET    /api/jobs/{job_id}         Get job detail + result
GET    /api/jobs/{job_id}/stream  SSE — streams log lines live
DELETE /api/jobs/{job_id}         Cancel a running job
```

**POST /api/jobs — Request:**
```json
{
  "type": "full_run",
  "params": {
    "query": "SELECT * FROM vw_dashboard WHERE machine_id=1",
    "label": "dashboard filter",
    "benchmark_runs": null,
    "safe": false,
    "no_deploy": false
  }
}
```

**POST /api/jobs — Response 202:**
```json
{
  "job_id": "3f8a2b1c-...",
  "status": "pending",
  "created_at": "2026-03-21T14:32:01"
}
```

**GET /api/jobs/{job_id} — Response:**
```json
{
  "job_id": "3f8a2b1c-...",
  "type": "full_run",
  "status": "completed",
  "params": { "query": "...", "label": "..." },
  "result": {
    "success": true,
    "optimized_query": "SELECT ...",
    "index_scripts": ["CREATE INDEX ..."],
    "improvement_pct": 87.4,
    "before_ms": 847.3,
    "after_ms": 107.2,
    "migration": { "number": 5, "filename": "005_optimize_..." }
  },
  "error": null,
  "created_at": "2026-03-21T14:32:01",
  "started_at": "2026-03-21T14:32:02",
  "completed_at": "2026-03-21T14:35:47"
}
```

**GET /api/jobs/{job_id}/stream — SSE Response:**
```
Content-Type: text/event-stream

data: {"type": "log", "line": "Step 1/9 — Identifying tables...", "ts": "14:32:02"}

data: {"type": "step", "step": 1, "total": 9, "label": "Identifying tables"}

data: {"type": "log", "line": "  ✓ Found 2 object(s): measurements, sensors", "ts": "14:32:02"}

data: {"type": "step", "step": 5, "total": 9, "label": "DeepSeek-R1 diagnosing"}

data: {"type": "complete", "result": { ...same as job detail result... }}

data: {"type": "error", "message": "Cannot connect to SQL Server"}
```

**GET /api/jobs — Query params:** `?type=full_run&status=completed&limit=20&offset=0`

---

### 4.2 System — `/api/system`

```
GET  /api/system/stats    Hardware metrics (CPU, RAM, VRAM, Ollama)
GET  /api/system/check    Full config_validator.run_checks() results
```

**GET /api/system/stats — Response:**
```json
{
  "cpu_usage": 45.2,
  "ram_usage_mb": 12400,
  "ram_total_mb": 32768,
  "ram_pct": 37.8,
  "gpu": {
    "name": "NVIDIA GeForce RTX 5070",
    "vram_usage_mb": 8400,
    "vram_total_mb": 16384,
    "vram_pct": 51.3,
    "utilization_pct": 92,
    "source": "pynvml"
  },
  "ollama": {
    "status": "online",
    "active_models": ["qwen2.5-coder:14b"],
    "url": "http://localhost:11434"
  },
  "db": {
    "status": "online",
    "database": "AcmeDev",
    "server": "localhost"
  }
}
```

**GET /api/system/check — Response:**
```json
{
  "passed": true,
  "critical_failures": 0,
  "warnings": 1,
  "checks": [
    { "name": "Database name set", "category": "Config", "passed": true, "message": "Database: AcmeDev" },
    { "name": "SQL Server reachable", "category": "Database", "passed": true, "message": "AcmeDev — SQL Server 2022" },
    { "name": "Schema snapshot", "category": "Watcher", "passed": true, "warning": true, "message": "Snapshot is 8 days old", "fix": "Run snapshot command" }
  ]
}
```

---

### 4.3 Schema — `/api/schema`

```
GET  /api/schema/tables           list_all_tables()
GET  /api/schema/views            list_all_views()
GET  /api/schema/table/{name}     get_schema(name)
GET  /api/schema/view/{name}      get_view_definition(name)
```

**GET /api/schema/table/{name} — Response:**
```json
{
  "table_name": "measurements",
  "estimated_row_count": 250000,
  "columns": [
    { "name": "id", "type": "int", "nullable": "NO", "primary_key": "YES" },
    { "name": "machine_id", "type": "int", "nullable": "NO", "primary_key": "NO" }
  ],
  "indexes": [
    { "name": "IX_measurements_machine", "type": "NONCLUSTERED", "unique": false,
      "key_columns": "machine_id, timestamp", "included_columns": "value" }
  ]
}
```

---

### 4.4 History — `/api/history`

```
GET  /api/history                          get_history() with filters
GET  /api/history/stats                    get_stats()
GET  /api/history/top?limit=10             get_top_improvements()
GET  /api/history/regressions              get_regressions()
GET  /api/history/trend?table=&query=      get_trend()
GET  /api/history/{id_a}/compare/{id_b}    compare_runs()
```

**GET /api/history — Query params:** `?query=&table=&limit=20&offset=0`

**GET /api/history/stats — Response:**
```json
{
  "total_runs": 47,
  "successful_runs": 44,
  "avg_improvement": 72.3,
  "best_improvement": 98.6,
  "worst_improvement": -4.2,
  "total_migrations": 12,
  "queries_tracked": 31,
  "tables_touched": 8
}
```

---

### 4.5 Migrations — `/api/migrations`

```
GET   /api/migrations                   list_migrations()
GET   /api/migrations?status=pending    list_migrations(status_filter="pending")
POST  /api/migrations/{n}/apply         mark_applied(n)
POST  /api/migrations/{n}/rollback      mark_rolled_back(n)
```

**GET /api/migrations — Response:**
```json
{
  "migrations": [
    {
      "number": 4,
      "filename": "004_optimize_vw_dashboard.sql",
      "description": "optimize: SELECT * FROM vw_dashboard",
      "date": "2026-03-20 14:32:01",
      "tables_affected": ["measurements"],
      "before_ms": 847.3,
      "after_ms": 12.1,
      "improvement_pct": 98.6,
      "status": "pending",
      "applied_to": []
    }
  ],
  "total": 5,
  "pending": 2,
  "applied": 3
}
```

---

### 4.6 Clients — `/api/clients`

```
GET   /api/clients                list_clients()
POST  /api/clients                create_client()
GET   /api/clients/active         get_active_client()
PUT   /api/clients/active         set_active_client() → { "name": "client_xyz" }
GET   /api/clients/{name}         get_client_config(name)
PUT   /api/clients/{name}         update_client_config(name, ...)
```

---

### 4.7 Models — `/api/models`

```
GET   /api/models                 Ollama inventory + VRAM status per model
POST  /api/models/{name}/preload  Send warmup inference to load model into VRAM
```

**GET /api/models — Response:**
```json
{
  "models": [
    {
      "name": "qwen2.5-coder:14b",
      "size_gb": 9.1,
      "modified_at": "2026-03-15T10:00:00",
      "is_loaded": true,
      "vram_mb": 8400
    },
    {
      "name": "deepseek-r1:14b",
      "size_gb": 8.8,
      "modified_at": "2026-03-10T08:00:00",
      "is_loaded": false,
      "vram_mb": 0
    }
  ],
  "vram_total_mb": 16384,
  "vram_used_mb": 8400
}
```

---

### 4.8 Deploy — `/api/deploy`

```
GET   /api/deploy/preview         Pending migrations + estimated package contents
POST  /api/deploy                 generate_deployment_package() → creates a job
GET   /api/deploy/packages        List generated deployment package folders
GET   /api/deploy/packages/{name}/files/{filename}   Serve a file for download
```

**GET /api/deploy/preview — Response:**
```json
{
  "client": "client_acme",
  "pending_count": 3,
  "migrations": [ ... ],
  "estimated_files": ["deploy.sql", "rollback.sql", "pre_flight.md", "technical_report.md", "walkthrough.md"]
}
```

---

### 4.9 Sandbox — `/api/sandbox`

```
POST    /api/sandbox/test           run_sandbox_test() → creates a job
GET     /api/sandbox/shadows        list_shadows()
DELETE  /api/sandbox/shadows/{name} destroy(name)
```

**POST /api/sandbox/test — Request:**
```json
{
  "migration_numbers": [4, 5],
  "threshold_pct": 30.0,
  "keep_on_failure": false,
  "bak_path": null
}
```

---

### 4.10 Settings — `/api/settings`

```
GET  /api/settings    Read safe subset of config.py
PUT  /api/settings    Write updated values to config.py
```

**GET /api/settings — Response:**
```json
{
  "db_config": {
    "server": "localhost",
    "database": "AcmeDev",
    "driver": "ODBC Driver 17 for SQL Server",
    "trusted_connection": "yes"
  },
  "ollama_base_url": "http://localhost:11434",
  "models": {
    "optimizer": "qwen2.5-coder:14b",
    "reasoner": "deepseek-r1:14b"
  },
  "benchmark_runs": 10,
  "auto_commit_git": true,
  "sandbox_bak_path": "C:\\Backups\\AcmeDev.bak",
  "sandbox_timeout": 300
}
```

**PUT /api/settings — Request:** Same shape, partial updates accepted.

---

## 5. Job Queue Design (`bridge/services/job_queue.py`)

```
JobQueue (singleton)
├── _executor: ThreadPoolExecutor(max_workers=1)   ← one job at a time
├── _jobs: Dict[str, JobState]                     ← in-memory job registry
├── _log_queues: Dict[str, queue.Queue]            ← per-job log line buffers
└── _db: sqlite3 connection → history.db jobs table

JobState
├── job_id: str (UUID4)
├── type: str
├── status: Literal["pending", "running", "completed", "failed", "cancelled"]
├── params: dict
├── result: dict | None
├── error: str | None
├── created_at, started_at, completed_at: datetime
└── log_queue: queue.Queue
```

**Flow:**
1. `POST /api/jobs` → `JobQueue.submit(type, params)` → returns `job_id`
2. Worker thread starts, sets `status=running`, updates DB
3. Tool function runs with stdout/Rich console redirected to `log_queue`
4. `GET /api/jobs/{id}/stream` opens SSE connection, drains `log_queue` in a generator
5. On completion/failure: `status` updated, `result`/`error` written to DB
6. SSE sends `type: complete` or `type: error` event, client closes stream

**Console redirection strategy:**
- Monkey-patch `console.print` in pipeline/optimizer/etc. to also write to `log_queue`
- Same pattern used in `tui/app.py` — already proven working
- Format: strip Rich markup for clean text, or pass markup directly (frontend renders plain text in terminal log)

**history.db — jobs table schema:**
```sql
CREATE TABLE IF NOT EXISTS jobs (
    job_id       TEXT PRIMARY KEY,
    type         TEXT NOT NULL,
    status       TEXT NOT NULL DEFAULT 'pending',
    params       TEXT,              -- JSON blob
    result       TEXT,             -- JSON blob (pipeline result dict)
    error        TEXT,
    log_lines    INTEGER DEFAULT 0,
    created_at   TEXT NOT NULL,
    started_at   TEXT,
    completed_at TEXT,
    client       TEXT
);

CREATE INDEX IF NOT EXISTS idx_jobs_status    ON jobs (status);
CREATE INDEX IF NOT EXISTS idx_jobs_created   ON jobs (created_at);
CREATE INDEX IF NOT EXISTS idx_jobs_client    ON jobs (client);
```

---

## 6. Hardware Monitor (`bridge/services/hardware.py`)

```python
class HardwareStats:
    cpu_usage: float
    ram_usage_mb: int
    ram_total_mb: int
    gpu: GpuStats | None
    source: str  # "pynvml" | "nvidia-smi" | "unavailable"

class GpuStats:
    name: str
    vram_usage_mb: int
    vram_total_mb: int
    vram_pct: float
    utilization_pct: int
```

**VRAM detection cascade:**
1. Try `pynvml.nvmlInit()` → `nvmlDeviceGetMemoryInfo()`
2. On failure, fall back to: `subprocess.run(["nvidia-smi", "--query-gpu=...", "--format=csv,noheader,nounits"])`
3. On failure: `gpu: null`, `source: "unavailable"`

**Poll frequency (set by frontend via `useSystemStats`):**
- Idle: every 2000ms
- Active inference detected (job `status=running`): every 500ms
- VRAM > 90%: trigger pulsating red border on `HardwareGauges`

---

## 7. React Component Map

### 7.1 Routing (`App.tsx`)

```
/                    → redirect to /dashboard
/dashboard           → Dashboard.tsx
/optimizer           → Optimizer.tsx
/optimizer/:job_id   → Optimizer.tsx (resume viewing a job)
/visualizer          → PlanVisualizer.tsx
/deploy              → DeploymentGate.tsx
/history             → History.tsx
/models              → ModelManager.tsx
/clients             → ClientManager.tsx
/settings            → Settings.tsx
```

### 7.2 Page Layouts

**Dashboard** — 3-zone layout:
```
┌─────────────────────────────────────────────────┐
│  SystemStatusRow (DB • Ollama • Git • Snapshot)  │
├────────────┬──────────────┬──────────────────────┤
│ CPU Gauge  │  RAM Gauge   │  VRAM Gauge (red>90%)│
├────────────┴──────────────┴──────────────────────┤
│  ActiveJobCard (step progress + live log preview) │
├─────────────────────────────────────────────────┤
│  RecentRunsPanel (last 5, improvement %, time)   │
└─────────────────────────────────────────────────┘
```

**Query Optimizer** — 3-column layout:
```
┌──────────────────┬──────────────────┬─────────────────┐
│ QueryInput       │ PipelineLog       │ ResultPanel      │
│ (Monaco SQL box) │ (SSE terminal)    │ (appears after)  │
│ [Full-Run]       │ Step 5/9 ████░░   │ Optimized SQL    │
│ [Analyze only]   │ Streaming...      │ Index Scripts    │
│ [Benchmark only] │                   │ [→ Visualizer]   │
│                  │                   │ [→ Deploy]       │
└──────────────────┴──────────────────┴─────────────────┘
```

**Plan Visualizer** — Full-width, split view:
```
┌──────────────────────────────────────────────────────┐
│  Upload .sqlplan  OR  Load from last job             │
├─────────────────────┬────────────────────────────────┤
│  BEFORE             │  AFTER                          │
│  [D3 tree SVG]      │  [D3 tree SVG]                  │
│  ← shared zoom/pan →│  ← synchronized                │
│                     │                                  │
│  Cost: 4.82         │  Cost: 0.41  (-91.5% ✓)        │
└─────────────────────┴────────────────────────────────┘
  [Optimization Summary floating card: $cost, % improvement]
```

**Deployment Gate** — Linear pipeline:
```
┌──────────────────────────────────────────────────────┐
│  Pending Migrations (3)                               │
│  ● 004 optimize_vw_dashboard  98.6% faster  [view]   │
│  ● 005 add_ix_sensors                       [view]   │
├──────────────────────────────────────────────────────┤
│  [Run Sandbox Test First]  ← required before deploy  │
│                                                       │
│  Sandbox Pipeline:                                    │
│  ① Provision  ② Restore  ③ Mutate  ④ Validate  ⑤ Wipe│
│                                                       │
│  [SANDBOX PASSED ✓] → [Generate Deploy Package] →     │
│  [DeployConfirmModal with SQL diff + type APPLY...]   │
└──────────────────────────────────────────────────────┘
```

**History & Trends** — Table + chart split:
```
┌──────────────┬─────────────────────────────────────┐
│ Filters       │  TrendChart (Recharts LineChart)     │
│ Table: ____   │  avg_ms over time per table          │
│ Query: ____   │                                      │
│ [Top] [Regs]  ├─────────────────────────────────────┤
│               │  RunsTable (sortable, filterable)    │
│               │  #  Date  Label  Before  After  Imp. │
│               │  [Compare] button on row select      │
└──────────────┴─────────────────────────────────────┘
```

---

## 8. Zustand Stores

### `jobStore.ts`
```typescript
interface JobStore {
  activeJobId: string | null;
  activeJobStatus: JobStatus | null;
  logLines: LogLine[];
  currentStep: number;
  totalSteps: number;
  stepLabel: string;
  result: JobResult | null;
  
  setActiveJob: (id: string) => void;
  appendLog: (line: LogLine) => void;
  setStep: (step: number, total: number, label: string) => void;
  setResult: (result: JobResult) => void;
  reset: () => void;
}
```

### `clientStore.ts`
```typescript
interface ClientStore {
  activeClient: string;
  clients: ClientSummary[];
  setActiveClient: (name: string) => Promise<void>;
  refreshClients: () => Promise<void>;
}
```

### `systemStore.ts`
```typescript
interface SystemStore {
  stats: HardwareStats | null;
  lastUpdated: Date | null;
  isInference: boolean;  // true when a job is running → 500ms poll
  setStats: (stats: HardwareStats) => void;
  setInference: (v: boolean) => void;
}
```

---

## 9. Key Custom Hooks

### `useSSE(url, { onMessage, onComplete, onError })`
- Creates `EventSource`, parses `data:` fields as JSON
- Auto-closes on `type: complete` or `type: error`
- Cleanup on unmount
- Returns `{ connected, close }`

### `useJob(jobId)`
- Polls `GET /api/jobs/{jobId}` every 3s until terminal state
- Opens SSE stream via `useSSE` while `status === "running"`
- Writes to `jobStore` (logLines, step, result)
- Returns `{ job, isLoading, isStreaming }`

### `useSystemStats()`
- Reads `systemStore.isInference` to determine poll interval
- `useInterval` → `GET /api/system/stats` → `systemStore.setStats`
- Returns current stats from store

### `useInterval(callback, delay)`
- Standard interval hook with cleanup
- `delay: null` pauses the interval

---

## 10. D3 Plan Visualizer Design

### Data Contract (from spec)
```typescript
interface PlanNode {
  name: string;          // display name e.g. "Index Seek"
  physicalOp: string;
  logicalOp: string;
  estimateRows: number;
  nodeCost: number;      // subtree cost minus sum of children subtree costs
  relativeCost: number;  // percentage of total plan cost
  isParallel: boolean;
  warnings: string[];
  children: PlanNode[];
}
```

### XML Parser (`planParser.ts`)
1. `fast-xml-parser` ingests `.sqlplan` XML
2. Navigate: `BatchSequence > Batch > Statements > StmtSimple > QueryPlan`
3. Recursively flatten `RelOp` nodes into `PlanNode` tree
4. Calculate `nodeCost = EstimatedTotalSubtreeCost - sum(children.EstimatedTotalSubtreeCost)`
5. Calculate `relativeCost = nodeCost / rootCost * 100`

### D3 Layout
- `d3.hierarchy(root)` → `d3.tree().nodeSize([120, 200])`
- Orientation: right-to-left (root = Result on left, table scans on right)
- Node: 180×70px SVG `<rect>` with rounded corners
- Edge: `d3.linkHorizontal()` path, `stroke-width` proportional to `Math.log(estimateRows + 1)`

### Color coding (per spec):
- `relativeCost < 10%`: `#64748B` border (slate)
- `10–30%`: `#D97706` border (amber, warning)
- `> 30%`: `#DC2626` border + drop shadow (red, bottleneck)
- Optimized node (cost lower than baseline): `#16A34A` border

### Shared zoom/pan (`PlanDiffContainer`):
- Two SVG refs share a single `d3.zoom()` transform via `useRef`
- `zoom.on("zoom")` updates both SVGs simultaneously
- "Reset Zoom" button returns to `d3.zoomIdentity`

### Operator icon map (`operatorIcons.ts`):
- `Table Scan` → cylinder icon
- `Index Seek` → funnel icon
- `Nested Loops` → two overlapping circles
- `Hash Match` → hash symbol
- `Sort` → sort-ascending icon
- etc. — all custom SVG paths, no external icon lib needed for these

---

## 11. Monaco Integration

### SQL Diff Viewer (`SqlDiffViewer.tsx`)
```typescript
import { DiffEditor } from "@monaco-editor/react";

<DiffEditor
  original={originalSql}
  modified={optimizedSql}
  language="sql"
  theme="light"   // enterprise light theme
  options={{
    renderSideBySide: true,
    readOnly: true,
    minimap: { enabled: false },
    fontSize: 13,
    fontFamily: "JetBrains Mono, monospace",
  }}
/>
```

### Query Input (`QueryInput.tsx`)
```typescript
import { Editor } from "@monaco-editor/react";

<Editor
  language="sql"
  theme="light"
  height="160px"
  options={{ minimap: { enabled: false }, lineNumbers: "off" }}
  onChange={setSqlValue}
/>
```

---

## 12. Sandbox State Machine

Five terminal states with strict UI lock:

```
IDLE
  ↓ [Run Sandbox Test]
PROVISIONING   → pulsing cloud icon
  ↓
RESTORING      → linear progress bar (polls job log for MB progress)
  ↓
MUTATING       → SQL statements ticking off one by one
  ↓
VALIDATING     → speedup gauge animates (before_ms → after_ms)
  ↓
WIPING         → shredder/fade animation
  ↓
COMPLETED ✓    → unlocks [Generate Deploy Package] button
  or
FAILED ✗       → Emergency Halt mode
               → Show error card (SQL State + exception)
               → Show last 20 log lines
               → Show rollback.sql preview
               → [Download Rollback Script] button
               → [Keep Shadow for Inspection] toggle
```

**Sandbox Lock rule:**
- "Generate Deploy Package" and "Deploy to Production" buttons are `disabled` in global state until `sandboxStatus === "completed"`
- Enforced in `jobStore` — not just local component state

---

## 13. DeployConfirmModal — "Red Button" Gate

```
┌─────────────────────────────────────────────────────┐
│  ⚠ Apply to Production                              │
│  ─────────────────────────────────────────────────  │
│  Impact Summary:                                     │
│  • 3 migrations to apply                            │
│  • Estimated cost delta: -72.4%                     │
│  • +3 new indexes                                   │
│  • Tables affected: measurements, sensors           │
│                                                     │
│  [SQL Diff Viewer — Monaco DiffEditor]              │
│  original.sql ←→ optimized.sql                      │
│                                                     │
│  To confirm, type exactly:                          │
│  ┌────────────────────────────────────────────┐     │
│  │ APPLY_TO_PROD                              │     │
│  └────────────────────────────────────────────┘     │
│                                                     │
│  [Cancel]          [Apply to Production ←disabled]  │
└─────────────────────────────────────────────────────┘
```

The "Apply to Production" button only enables when `inputValue === "APPLY_TO_PROD"`.

---

## 14. Design System — Professional Light

### Typography
- **Display / headings:** `DM Sans` (geometric, clean, enterprise feel)
- **Body / UI:** `DM Sans` (consistent family)
- **Code / SQL:** `JetBrains Mono` (best-in-class for SQL, monospaced)

### Color Palette (CSS Variables)
```css
:root {
  --bg-base:        #F8FAFC;  /* slate-50 — page background */
  --bg-surface:     #FFFFFF;  /* card/panel background */
  --bg-elevated:    #F1F5F9;  /* input, hover states */
  --border:         #E2E8F0;  /* slate-200 */
  --border-strong:  #CBD5E1;  /* slate-300 */

  --text-primary:   #0F172A;  /* slate-900 */
  --text-secondary: #475569;  /* slate-600 */
  --text-muted:     #94A3B8;  /* slate-400 */

  --accent:         #2563EB;  /* blue-600 — primary actions */
  --accent-light:   #DBEAFE;  /* blue-100 — accent backgrounds */
  --accent-hover:   #1D4ED8;  /* blue-700 */

  --success:        #16A34A;  /* green-600 */
  --success-light:  #DCFCE7;  /* green-100 */
  --warning:        #D97706;  /* amber-600 */
  --warning-light:  #FEF3C7;  /* amber-100 */
  --danger:         #DC2626;  /* red-600 */
  --danger-light:   #FEE2E2;  /* red-100 */

  --sidebar-width:  240px;
  --topbar-height:  56px;

  --shadow-sm:  0 1px 2px 0 rgb(0 0 0 / 0.05);
  --shadow-md:  0 4px 6px -1px rgb(0 0 0 / 0.07);
  --shadow-lg:  0 10px 15px -3px rgb(0 0 0 / 0.08);
}
```

### Component Standards
- Cards: `bg-white border border-slate-200 rounded-lg shadow-sm`
- Primary button: `bg-blue-600 hover:bg-blue-700 text-white rounded-md px-4 py-2`
- Danger button: `bg-red-600 hover:bg-red-700 text-white`
- Secondary button: `border border-slate-300 bg-white hover:bg-slate-50 text-slate-700`
- Input: `border border-slate-300 rounded-md px-3 py-2 focus:ring-2 focus:ring-blue-500`
- Status badges: pill-shaped, color per severity

### Sidebar Navigation
```
[SQL Agent logo + version]
─────────────────────────
[Client: client_acme ▾]   ← dropdown to switch client
─────────────────────────
◈ Dashboard
◈ Query Optimizer
◈ Plan Visualizer
◈ Deployment Gate
◈ History & Trends
─────────────────────────
◈ Model Manager
◈ Client Manager
◈ Settings
─────────────────────────
[System status mini-bar]  ← CPU/VRAM mini gauges at bottom
```

---

## 15. Build Phases

### Phase 1 — Foundation (Week 1)
**Goal:** Both servers running, one page renders real data.

- `bridge/main.py` — FastAPI app with CORS for `localhost:5173`
- `bridge/services/job_queue.py` — job queue skeleton (no tool calls yet, just echo)
- `bridge/services/hardware.py` — CPU/RAM via psutil, VRAM with fallback
- `bridge/routers/system.py` — `/api/system/stats` working
- `bridge/routers/schema.py` — `/api/schema/tables` and `/api/schema/table/{name}`
- `agent.py` — add `serve` command
- `web/` — Vite + React + Tailwind scaffold
- `web/src/` — Sidebar, TopBar, PageShell, routing skeleton
- `web/src/pages/Dashboard.tsx` — HardwareGauges wired to `/api/system/stats`
- `web/src/hooks/useSystemStats.ts`

**Done when:** `python agent.py serve` opens a browser showing real CPU/RAM/VRAM gauges.

### Phase 2 — Query Optimizer (Week 2)
**Goal:** Submit a query, watch it optimize live, see results.

- `bridge/services/job_queue.py` — full implementation with console redirect
- `bridge/routers/jobs.py` — POST, GET, SSE stream
- `history.db` — add `jobs` table migration
- `web/src/pages/Optimizer.tsx`
- `web/src/components/optimizer/` — all 4 components
- `web/src/hooks/useSSE.ts`, `useJob.ts`
- `web/src/store/jobStore.ts`

**Done when:** Full-run query → live step progress → results displayed.

### Phase 3 — History & Migrations (Week 2-3)
**Goal:** History table, trends chart, migration management.

- `bridge/routers/history.py` — all endpoints
- `bridge/routers/migrations.py` — list, mark applied/rollback
- `web/src/pages/History.tsx`
- `web/src/components/history/` — RunsTable, TrendChart (Recharts), ComparePanel

**Done when:** History loads, trend chart renders, compare works.

### Phase 4 — Deployment Gate + Sandbox (Week 3)
**Goal:** Full sandbox lifecycle → deployment confirmation gate.

- `bridge/routers/sandbox.py` and `bridge/routers/deploy.py`
- `web/src/pages/DeploymentGate.tsx`
- `web/src/components/deployment/` — all 4 components
- Monaco DiffEditor integration
- Sandbox state machine in `SandboxPipeline.tsx`
- DeployConfirmModal with "APPLY_TO_PROD" gate

**Done when:** Sandbox runs, fails/passes, deploy gate blocks correctly.

### Phase 5 — Model Manager + Clients (Week 3-4)
**Goal:** Ollama inventory visible, client switching from UI.

- `bridge/routers/models.py` and `bridge/routers/clients.py`
- `web/src/pages/ModelManager.tsx` and `web/src/pages/ClientManager.tsx`
- `web/src/store/clientStore.ts`
- Client switcher in sidebar

**Done when:** Switch client from UI, VRAM bar shows per-model usage.

### Phase 6 — Plan Visualizer (Week 4)
**Goal:** Upload .sqlplan → D3 tree renders → before/after diff.

- `web/src/components/visualizer/planParser.ts` — XML → PlanNode
- `web/src/components/visualizer/PlanTree.tsx` — D3 layout + SVG
- `web/src/components/visualizer/PlanNode.tsx` and `PlanEdge.tsx`
- `web/src/components/visualizer/PlanDiffContainer.tsx` — shared zoom
- `web/src/pages/PlanVisualizer.tsx`

**Done when:** Upload two .sqlplan files → side-by-side D3 trees with synchronized pan/zoom.

### Phase 7 — Settings (Week 4)
**Goal:** Config.py editable from UI.

- `bridge/routers/settings.py`
- `web/src/pages/Settings.tsx` — form fields, save, test connection button

### Phase 8 — Polish + Production Build (Week 4-5)
**Goal:** Ship-ready.

- `npm run build` → FastAPI serves `web/dist/` as static files
- `python agent.py serve --no-dev` → single process
- Loading states, empty states, error boundaries everywhere
- Toast notifications for job completion / errors
- VRAM 90% alert animation
- Final Tailwind pass for consistency

---

## 16. Package Files

### `bridge/requirements.txt`
```
fastapi>=0.110.0
uvicorn[standard]>=0.27.0
psutil>=5.9.0
pynvml>=11.5.0
python-multipart>=0.0.9
```

### `web/package.json` (key deps)
```json
{
  "dependencies": {
    "react": "^18.3.0",
    "react-dom": "^18.3.0",
    "react-router-dom": "^6.22.0",
    "zustand": "^4.5.0",
    "recharts": "^2.12.0",
    "d3": "^7.9.0",
    "@monaco-editor/react": "^4.6.0",
    "fast-xml-parser": "^4.3.0",
    "clsx": "^2.1.0",
    "lucide-react": "^0.363.0"
  },
  "devDependencies": {
    "@types/react": "^18.3.0",
    "@types/d3": "^7.4.0",
    "typescript": "^5.4.0",
    "vite": "^5.2.0",
    "@vitejs/plugin-react": "^4.2.0",
    "tailwindcss": "^3.4.0",
    "postcss": "^8.4.0",
    "autoprefixer": "^10.4.0"
  }
}
```

### `web/vite.config.ts`
```typescript
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: "../bridge/static",   // FastAPI serves from here in production
  },
});
```

---

## 17. What Does NOT Change in V4

The following files are **read-only from the bridge's perspective**. The FastAPI layer imports and calls them — it never modifies them:

- `tools/*.py` — all 18 existing tools
- `config.py` — read at startup; Settings endpoint writes it carefully
- `history.db` — extended with `jobs` table only; existing schema untouched
- `migrations/`, `runs/`, `reports/`, `deployments/`, `snapshots/` — written by tools same as before
- `agent.py` — only addition is the `serve` command at the bottom

The CLI remains **fully functional**. V4 is additive.

---

## 18. Next Steps

Ready to build. Suggested next message:

> "Start Phase 1 — build `bridge/main.py`, `job_queue.py`, `hardware.py`, and `system.py` router. Then the React scaffold with routing and the Dashboard page wired to real hardware stats."

Or if you want to see UI first:

> "Build a static mockup of the Dashboard page so I can approve the design before wiring up the backend."

---

*V4 Architecture — locked 2026-03-21*  
*8 pages · FastAPI bridge · React 18 + Vite · D3 visualizer · SSE streaming · Monaco diff*
