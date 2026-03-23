# SQL Optimization Agent V4 — Complete Phase Plan
> Full build roadmap from Phase 1 through Phase 8.
> Attach this alongside the Phase 2 handoff doc in every new chat.
> Last updated: 2026-03-21

---

## Phase Overview

| Phase | Name | Goal | Status |
|---|---|---|---|
| 1 | Foundation | FastAPI bridge + React scaffold + Dashboard with live hardware gauges | ✅ COMPLETE |
| 2 | Query Optimizer | Submit query → watch pipeline stream live → see results | ⬅ NEXT |
| 3 | History & Trends | Runs table, trend charts, run comparison | Pending |
| 4 | Deployment Gate | Sandbox lifecycle, Monaco diff, confirm modal, rollback | Pending |
| 5 | Model Manager + Clients | Ollama inventory, VRAM per model, client switching | Pending |
| 6 | Plan Visualizer | D3 tree, before/after diff, synchronized zoom/pan | Pending |
| 7 | Settings | config.py editable from UI | Pending |
| 8 | Polish + Production Build | Loading states, error boundaries, `npm run build` → single process | Pending |

---

## Phase 1 — Foundation ✅ COMPLETE

**Goal:** Both servers running, Dashboard page renders real data from the machine.

### What was built
**Backend (`bridge/`):**
- `main.py` — FastAPI app, CORS for localhost:5173, static file serving for prod build
- `services/hardware.py` — background polling thread, psutil CPU/RAM, pynvml + nvidia-smi VRAM fallback
- `services/job_queue.py` — JobState dataclass, `jobs` table schema, create/list skeleton (no execution yet)
- `routers/system.py` — `GET /api/system/stats`, `GET /api/system/check`, `PUT /api/system/poll`
- `routers/schema.py` — `GET /api/schema/all|tables|views|table/{n}|view/{n}`

**Frontend (`web/src/`):**
- Full Vite + React 18 + TypeScript + Tailwind CSS scaffold
- `App.tsx` — React Router with all 8 routes
- `index.css` — full design system (CSS variables, animations, utility classes)
- Layout: `Sidebar.tsx` (nav, schema tree, client switcher, system dots), `TopBar.tsx`, `PageShell.tsx`
- Shared: `StatusBadge`, `LoadingSpinner`, `EmptyState`
- Dashboard components: `HardwareGauges` (Recharts RadialBarChart, VRAM alert), `SystemStatusRow`, `ActiveJobCard` (step bubbles wired in Phase 2), `RecentRunsPanel` (mock data, wired in Phase 3)
- Hooks: `useInterval`, `useSystemStats`
- Stores: `systemStore`, `clientStore`
- API layer: `client.ts`, `system.ts`, `schema.ts`
- `Dashboard.tsx` — fully wired to live hardware stats
- 7 page stubs (Optimizer, PlanVisualizer, DeploymentGate, History, ModelManager, ClientManager, Settings)
- `serve_command_for_agent_py.py` — paste into `agent.py`

**Done when:** `python agent.py serve` opens browser showing Dashboard with real CPU/RAM/VRAM gauges. ✅

---

## Phase 2 — Query Optimizer

**Goal:** Submit a SQL query, watch the 9-step pipeline stream live, see results.

**Done when:** Full-run query → live step progress in browser → optimized SQL + index scripts displayed.

### New files to create

**Backend:**
```
bridge/routers/jobs.py          POST/GET/DELETE + GET /{id}/stream (SSE)
bridge/services/sse.py          SSE format helpers, ping keepalive
```

**Frontend:**
```
web/src/store/jobStore.ts
web/src/hooks/useSSE.ts
web/src/hooks/useJob.ts
web/src/api/jobs.ts
web/src/components/optimizer/QueryInput.tsx     Monaco SQL editor + submit buttons
web/src/components/optimizer/PipelineLog.tsx    SSE terminal, auto-scroll
web/src/components/optimizer/StepProgress.tsx   9-step progress track
web/src/components/optimizer/ResultPanel.tsx    Optimized SQL, index scripts, action buttons
web/src/pages/Optimizer.tsx                     Full 3-column layout (replaces stub)
```

### Files to modify
```
bridge/main.py                  Add lifespan handler: start hardware monitor, ensure_jobs_table(), register jobs router
bridge/services/job_queue.py    Add submit(), _run(), console redirect, step detection
web/src/components/dashboard/ActiveJobCard.tsx   Wire to jobStore (currently static)
```

### Optimizer page layout
```
┌──────────────────┬──────────────────┬─────────────────┐
│ QueryInput       │ PipelineLog       │ ResultPanel      │
│                  │                   │ (after complete) │
│ Monaco SQL box   │ SSE terminal      │                  │
│ [Full-Run]       │ Step 5/9 ████░░   │ Optimized SQL    │
│ [Analyze only]   │ Streaming...      │ Index scripts    │
│ [Benchmark only] │                   │ [→ Visualizer]   │
│                  │                   │ [→ Deploy]       │
└──────────────────┴──────────────────┴─────────────────┘
```

### SSE event format
```
data: {"type": "log",      "line": "Step 1/9 — Identifying tables...", "ts": "14:32:02"}
data: {"type": "step",     "step": 1, "total": 9, "label": "Identifying tables"}
data: {"type": "complete", "result": { ...pipeline result dict... }}
data: {"type": "error",    "message": "Cannot connect to SQL Server"}
data: {"type": "ping"}     (every 15s keepalive — Ollama can take 5-10 min)
```

### Job types supported in Phase 2
```python
"full_run"   → tools.pipeline.run_single(query, label, benchmark_runs, skip_deploy)
"analyze"    → tools.optimizer.optimize_query(query, schema_list)
"benchmark"  → tools.benchmarker.benchmark_query(original, optimized, label, runs)
```

### Key implementation notes
1. `ThreadPoolExecutor(max_workers=1)` — one job at a time, others queue
2. Console redirect: monkey-patch `console` in `tools.optimizer`, `tools.pipeline`, `tools.benchmarker`, `tools.executor`, `tools.migrator`. Restore after job. Exact pattern in `tui/app.py → _patch_console()`
3. Step detection: parse log lines for `"Step N/M"` → emit `type:"step"` SSE events
4. If `benchmark.row_mismatch === true`: show red warning, disable "→ Deploy" button
5. Monaco: `import { Editor } from "@monaco-editor/react"`, language `"sql"`, theme `"light"`, no minimap

---

## Phase 3 — History & Trends

**Goal:** Full run history table, improvement trend chart, side-by-side run comparison.

**Done when:** History page shows all runs, filterable by table/query. Trend chart renders a Recharts LineChart over time. Compare panel shows two runs side by side.

### New files to create

**Backend:**
```
bridge/routers/history.py       GET /api/history, /stats, /top, /regressions, /trend, /{a}/compare/{b}
bridge/routers/migrations.py    GET /api/migrations, POST /{n}/apply, POST /{n}/rollback
```

**Frontend:**
```
web/src/api/history.ts
web/src/api/migrations.ts
web/src/components/history/RunsTable.tsx      Filterable, sortable table of runs
web/src/components/history/TrendChart.tsx     Recharts LineChart — avg_ms over time
web/src/components/history/ComparePanel.tsx   Side-by-side run diff
web/src/pages/History.tsx                     Full page layout (replaces stub)
```

### Files to modify
```
bridge/main.py                    Register history + migrations routers
web/src/components/dashboard/RecentRunsPanel.tsx   Replace mock data with real API call
```

### History page layout
```
┌──────────────┬─────────────────────────────────────────┐
│ Filters       │ TrendChart (Recharts LineChart)          │
│ Table: ____   │ avg_ms over time per table               │
│ Query: ____   ├─────────────────────────────────────────┤
│ [Top] [Regs]  │ RunsTable (sortable, filterable)         │
│               │ # · Date · Label · Before · After · Imp  │
│               │ [Compare] on row select                  │
└──────────────┴─────────────────────────────────────────┘
```

### API endpoints
```
GET  /api/history                      ?query=&table=&limit=20&offset=0
GET  /api/history/stats                → { total_runs, avg_improvement, best, worst, ... }
GET  /api/history/top?limit=10
GET  /api/history/regressions
GET  /api/history/trend?table=&query=
GET  /api/history/{id_a}/compare/{id_b}
GET  /api/migrations                   ?status=pending|applied|rolled_back
POST /api/migrations/{n}/apply
POST /api/migrations/{n}/rollback
```

### Existing CLI functions to call
```python
from tools.history import (
    get_history, get_stats, get_top_improvements,
    get_regressions, get_trend, compare_runs
)
from tools.migrator import (
    list_migrations, mark_applied, mark_rolled_back
)
```

---

## Phase 4 — Deployment Gate

**Goal:** Full sandbox lifecycle state machine → Monaco SQL diff → "APPLY_TO_PROD" gate → deploy package generated.

**Done when:** User can run sandbox test, see it pass/fail through 5 stages, review Monaco diff, type `APPLY_TO_PROD` to generate the deployment package.

### New files to create

**Backend:**
```
bridge/routers/deploy.py        GET /api/deploy/preview, POST /api/deploy, GET /api/deploy/packages
bridge/routers/sandbox.py       POST /api/sandbox/test, GET /api/sandbox/shadows, DELETE /api/sandbox/shadows/{name}
```

**Frontend:**
```
web/src/api/deploy.ts
web/src/api/sandbox.ts
web/src/components/deployment/SandboxPipeline.tsx   5-step lifecycle state machine UI
web/src/components/deployment/DeployConfirmModal.tsx  "Type APPLY_TO_PROD" gate
web/src/components/deployment/SqlDiffViewer.tsx       Monaco DiffEditor
web/src/components/deployment/RollbackPanel.tsx       rollback.sql viewer + download
web/src/pages/DeploymentGate.tsx                      Full page layout (replaces stub)
```

### Files to modify
```
bridge/main.py       Register deploy + sandbox routers
```

### Sandbox lifecycle states
```
IDLE
  ↓ [Run Sandbox Test]
PROVISIONING  → pulsing cloud icon
RESTORING     → linear progress bar (polls job log for MB progress)
MUTATING      → SQL statements ticking off one by one
VALIDATING    → speedup gauge animates (before_ms → after_ms)
WIPING        → fade animation
COMPLETED ✓   → unlocks [Generate Deploy Package]
  or
FAILED ✗      → Emergency Halt: error card + last 20 log lines + rollback.sql preview + download button
```

### Sandbox lock rule
- "Generate Deploy Package" and "Deploy to Production" buttons are `disabled` globally until `sandboxStatus === "completed"`
- Enforced in `jobStore`, not just local component state

### DeployConfirmModal — "Red Button" Gate
```
Impact Summary:
  • N migrations to apply
  • Estimated cost delta: -72.4%
  • +N new indexes
  • Tables affected: measurements, sensors

[Monaco DiffEditor — original.sql vs optimized.sql]

To confirm, type exactly:
  ┌──────────────────────────────────┐
  │ APPLY_TO_PROD                    │
  └──────────────────────────────────┘

[Cancel]       [Apply to Production ← disabled until typed]
```

### API endpoints
```
GET   /api/deploy/preview          → { client, pending_count, migrations, estimated_files }
POST  /api/deploy                  → creates a job (type: "deploy")
GET   /api/deploy/packages         → list generated package folders
GET   /api/deploy/packages/{name}/files/{filename}
POST  /api/sandbox/test            → creates a job (type: "sandbox_test")
GET   /api/sandbox/shadows         → list_shadows()
DELETE/api/sandbox/shadows/{name}  → destroy(name)
```

### Existing CLI functions to call
```python
from tools.reporter import generate_deployment_package
from tools.sandbox  import run_sandbox_test, list_shadows, destroy
from tools.migrator import get_pending_migrations
```

---

## Phase 5 — Model Manager + Client Manager

**Goal:** See Ollama model inventory with per-model VRAM, preload models, switch clients from UI.

**Done when:** Model Manager shows all Ollama models with GB size and loaded status. VRAM bar shows per-model usage. Client Manager lists all workspaces and switching clients reloads the entire UI context.

### New files to create

**Backend:**
```
bridge/routers/models.py        GET /api/models, POST /api/models/{name}/preload
bridge/routers/clients.py       GET /api/clients, POST, GET /active, PUT /active, GET /{name}, PUT /{name}
```

**Frontend:**
```
web/src/api/models.ts
web/src/api/clients.ts
web/src/components/models/ModelCard.tsx    Name, size, status dot, preload button
web/src/components/models/VramBar.tsx      Linear VRAM bar + 90% alert
web/src/components/clients/ClientList.tsx  Table with active indicator (★)
web/src/components/clients/ClientEditForm.tsx  Server/DB/bak path fields
web/src/pages/ModelManager.tsx             Full page (replaces stub)
web/src/pages/ClientManager.tsx            Full page (replaces stub)
```

### Files to modify
```
bridge/main.py                  Register models + clients routers
web/src/components/layout/Sidebar.tsx   Wire client switcher dropdown to clientStore + PUT /api/clients/active
```

### Model Manager layout
```
┌─────────────────────────────────────────────┐
│ VRAM: ████████░░  14.9 GB / 16 GB  (93%)    │  ← VramBar (red if > 90%)
├─────────────────────────────────────────────┤
│  ● qwen2.5-coder:14b    9.1 GB    [loaded]  │
│  ○ deepseek-r1:14b      8.8 GB    [preload] │
│  ○ llama3.2:3b          2.0 GB    [preload] │
└─────────────────────────────────────────────┘
```

### API endpoints
```
GET   /api/models                  → { models: [...], vram_total_mb, vram_used_mb }
POST  /api/models/{name}/preload   → sends warmup inference to load model into VRAM
GET   /api/clients                 → list_clients()
POST  /api/clients                 → create_client(...)
GET   /api/clients/active          → { name: "client_acme" }
PUT   /api/clients/active          → { "name": "client_xyz" } → set_active_client()
GET   /api/clients/{name}          → get_client_config(name)
PUT   /api/clients/{name}          → update_client_config(name, ...)
```

### Existing CLI functions to call
```python
from tools.client_manager import (
    list_clients, create_client, get_active_client,
    set_active_client, get_client_config, update_client_config
)
```

### Client switch side effect
When `PUT /api/clients/active` is called, the frontend must:
1. Update `clientStore.activeClient`
2. Refetch `GET /api/schema/all` → update sidebar tree
3. Refetch `GET /api/history` → update recent runs panel
4. Show a toast: "Switched to client_xyz"

---

## Phase 6 — Plan Visualizer

**Goal:** Upload two .sqlplan files → D3 renders side-by-side trees → synchronized zoom/pan → cost improvement overlay.

**Done when:** User uploads before/after .sqlplan files, sees two D3 trees side by side with color-coded nodes, can pan/zoom both simultaneously, sees total cost improvement as a floating card.

### New files to create

**Frontend only** (no new backend needed — plan parsing happens client-side):
```
web/src/components/visualizer/planParser.ts       XML → PlanNode tree (fast-xml-parser)
web/src/components/visualizer/operatorIcons.ts    physicalOp → SVG path map
web/src/components/visualizer/PlanTree.tsx         D3 layout + SVG rendering
web/src/components/visualizer/PlanNode.tsx         SVG node card (cost %, operator icon, warnings)
web/src/components/visualizer/PlanEdge.tsx         Variable-width path proportional to estimateRows
web/src/components/visualizer/PlanDiffContainer.tsx  Side-by-side with shared D3 zoom
web/src/pages/PlanVisualizer.tsx                   Full page layout (replaces stub)
```

### PlanNode TypeScript interface
```typescript
interface PlanNode {
  name: string;          // display name e.g. "Index Seek"
  physicalOp: string;
  logicalOp: string;
  estimateRows: number;
  nodeCost: number;      // subtree cost − sum(children subtree costs)
  relativeCost: number;  // % of total plan cost
  isParallel: boolean;
  warnings: string[];
  children: PlanNode[];
}
```

### XML parsing steps (`planParser.ts`)
1. `fast-xml-parser` ingests `.sqlplan` XML
2. Navigate: `BatchSequence > Batch > Statements > StmtSimple > QueryPlan`
3. Recursively flatten `RelOp` nodes into `PlanNode` tree
4. `nodeCost = EstimatedTotalSubtreeCost - sum(children.EstimatedTotalSubtreeCost)`
5. `relativeCost = nodeCost / rootCost * 100`

### D3 layout
- `d3.hierarchy(root)` → `d3.tree().nodeSize([120, 200])`
- Orientation: **right-to-left** (root = Result on left, table scans on right)
- Node: 180×70px SVG `<rect>` with rounded corners
- Edge: `d3.linkHorizontal()` path, `strokeWidth` proportional to `Math.log(estimateRows + 1)`

### Node color coding
```
relativeCost < 10%:  #64748B border (slate — normal)
10% - 30%:           #D97706 border (amber — warning)
> 30%:               #DC2626 border + drop-shadow (red — bottleneck)
Improved node:       #16A34A border (green — cost lower than baseline)
```

### Shared zoom/pan
```typescript
// PlanDiffContainer.tsx
const zoomRef = useRef<d3.ZoomBehavior<SVGSVGElement, unknown>>();
const beforeSvgRef = useRef<SVGSVGElement>(null);
const afterSvgRef  = useRef<SVGSVGElement>(null);

// Single zoom behavior updates both SVGs simultaneously
zoomRef.current = d3.zoom<SVGSVGElement, unknown>()
  .on("zoom", (event) => {
    d3.select(beforeSvgRef.current).select("g").attr("transform", event.transform);
    d3.select(afterSvgRef.current).select("g").attr("transform", event.transform);
  });
```

### Operator icon map (`operatorIcons.ts`)
```
Table Scan       → cylinder SVG
Index Seek       → funnel SVG
Index Scan       → funnel with strikethrough
Nested Loops     → two overlapping circles
Hash Match       → # symbol
Sort             → sort-ascending arrows
Key Lookup       → key SVG
Parallelism      → parallel lines
```

---

## Phase 7 — Settings

**Goal:** Read and write the main config.py settings from the browser.

**Done when:** Settings page loads current config values, user edits DB connection or model names, saves, and the next pipeline run uses the new values.

### New files to create

**Backend:**
```
bridge/routers/settings.py      GET /api/settings, PUT /api/settings
```

**Frontend:**
```
web/src/api/settings.ts
web/src/pages/Settings.tsx      Full form (replaces stub)
```

### API endpoints
```
GET  /api/settings    → safe subset of config.py
PUT  /api/settings    → partial update, writes back to config.py
```

### GET /api/settings response shape
```json
{
  "db_config": {
    "server":              "localhost",
    "database":            "AcmeDev",
    "driver":              "ODBC Driver 17 for SQL Server",
    "trusted_connection":  "yes"
  },
  "ollama_base_url":  "http://localhost:11434",
  "models": {
    "optimizer": "qwen2.5-coder:14b",
    "reasoner":  "deepseek-r1:14b"
  },
  "benchmark_runs":    10,
  "auto_commit_git":   true,
  "sandbox_bak_path":  "C:\\Backups\\AcmeDev.bak",
  "sandbox_timeout":   300
}
```

### Settings page layout
```
┌─────────────────────────────────────────────┐
│  Database Connection                         │
│  Server:   [localhost              ]         │
│  Database: [AcmeDev               ]         │
│  Driver:   [ODBC Driver 17...     ]         │
│  Auth:     (•) Windows Auth  ( ) SQL Login  │
│  [Test Connection]  ✓ Connected             │
├─────────────────────────────────────────────┤
│  AI Models                                   │
│  Optimizer: [qwen2.5-coder:14b    ]         │
│  Reasoner:  [deepseek-r1:14b      ]         │
├─────────────────────────────────────────────┤
│  Pipeline                                    │
│  Benchmark runs: [10]                        │
│  Auto Git commit: [✓]                        │
├─────────────────────────────────────────────┤
│  Sandbox                                     │
│  .bak path: [C:\Backups\AcmeDev.bak ]       │
│  Timeout:   [300] seconds                   │
├─────────────────────────────────────────────┤
│                             [Save Settings] │
└─────────────────────────────────────────────┘
```

### Safety rule
Never expose `username` or `password` from config.py over the API. The GET response must omit them. The PUT endpoint accepts them only if the user explicitly provides new values.

---

## Phase 8 — Polish + Production Build

**Goal:** Ship-ready. Single command starts everything. All edge cases handled.

**Done when:** `python agent.py serve --no-dev` serves the entire app from one process. Every loading state, empty state, and error is handled gracefully.

### Tasks

**Build:**
```bash
# In web/:
npm run build
# → builds to bridge/static/ (per vite.config.ts outDir)

# Then:
python agent.py serve --no-dev
# → single uvicorn process serves both API and React SPA
```

**Loading states** — every data-fetching component must show `<LoadingSpinner />` until data arrives.

**Empty states** — every list/table must show `<EmptyState />` when result is empty.

**Error boundaries** — wrap each page in a React error boundary to catch render crashes without breaking the whole app.

**Toast notifications:**
- Job completed → green toast with improvement %
- Job failed → red toast with error preview
- Client switched → blue toast
- Settings saved → green toast

**VRAM 90% alert** — already implemented with `animate-pulse-danger` on the VRAM gauge card. Verify it triggers correctly during active inference.

**Stale data indicators** — if `/api/system/stats` hasn't responded in >10s, show a yellow dot on the TopBar refresh timestamp.

**Production `serve` command update:**
```python
@app.command()
def serve(dev: bool = typer.Option(True, "--dev")):
    if dev:
        # start vite dev server subprocess
    else:
        # check bridge/static/ exists and has index.html
        # uvicorn only — FastAPI serves web/dist via StaticFiles
```

**Final Tailwind pass** — ensure no inline styles contradict the design system. All colors should use CSS variables, not hardcoded hex.

---

## Cross-Phase: What Never Changes

The following are **read-only** from the bridge's perspective. The FastAPI layer calls them, never modifies them directly (except Settings which writes config.py carefully):

- `tools/*.py` — all 18 existing CLI tools
- `config.py` — read at bridge startup; Settings router writes it
- `history.db` — extended with `jobs` table only; existing schema untouched
- `migrations/`, `runs/`, `reports/`, `deployments/`, `snapshots/` — written by tools as before
- `agent.py` — only addition is the `serve` command at the bottom

**The CLI stays 100% functional throughout all phases. V4 is additive.**

---

## Complete Final File Tree (all 8 phases)

```
sql-agent/
├── agent.py                            ← +serve command
├── config.py
├── tools/                              ← unchanged
│
├── bridge/
│   ├── __init__.py
│   ├── main.py
│   ├── requirements.txt
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── system.py       ✅ Phase 1
│   │   ├── schema.py       ✅ Phase 1
│   │   ├── jobs.py         ⬅ Phase 2
│   │   ├── history.py         Phase 3
│   │   ├── migrations.py      Phase 3
│   │   ├── deploy.py          Phase 4
│   │   ├── sandbox.py         Phase 4
│   │   ├── models.py          Phase 5
│   │   ├── clients.py         Phase 5
│   │   └── settings.py        Phase 7
│   └── services/
│       ├── __init__.py
│       ├── hardware.py     ✅ Phase 1
│       ├── job_queue.py    ✅ skeleton / ⬅ Phase 2 execution
│       └── sse.py          ⬅ Phase 2
│
└── web/src/
    ├── App.tsx             ✅ Phase 1
    ├── main.tsx            ✅ Phase 1
    ├── index.css           ✅ Phase 1
    ├── api/
    │   ├── client.ts       ✅ Phase 1
    │   ├── system.ts       ✅ Phase 1
    │   ├── schema.ts       ✅ Phase 1
    │   ├── jobs.ts         ⬅ Phase 2
    │   ├── history.ts         Phase 3
    │   ├── migrations.ts      Phase 3
    │   ├── deploy.ts          Phase 4
    │   ├── sandbox.ts         Phase 4
    │   ├── models.ts          Phase 5
    │   ├── clients.ts         Phase 5
    │   └── settings.ts        Phase 7
    ├── pages/
    │   ├── Dashboard.tsx   ✅ Phase 1
    │   ├── Optimizer.tsx   ⬅ Phase 2
    │   ├── History.tsx        Phase 3
    │   ├── DeploymentGate.tsx Phase 4
    │   ├── ModelManager.tsx   Phase 5
    │   ├── ClientManager.tsx  Phase 5
    │   ├── PlanVisualizer.tsx Phase 6
    │   └── Settings.tsx       Phase 7
    ├── components/
    │   ├── layout/
    │   │   ├── Sidebar.tsx     ✅ Phase 1
    │   │   ├── TopBar.tsx      ✅ Phase 1
    │   │   └── PageShell.tsx   ✅ Phase 1
    │   ├── dashboard/
    │   │   ├── HardwareGauges.tsx   ✅ Phase 1
    │   │   ├── SystemStatusRow.tsx  ✅ Phase 1
    │   │   ├── ActiveJobCard.tsx    ✅ skeleton / ⬅ Phase 2 wired
    │   │   └── RecentRunsPanel.tsx  ✅ mock data / Phase 3 wired
    │   ├── optimizer/          ⬅ Phase 2
    │   │   ├── QueryInput.tsx
    │   │   ├── PipelineLog.tsx
    │   │   ├── StepProgress.tsx
    │   │   └── ResultPanel.tsx
    │   ├── history/               Phase 3
    │   │   ├── RunsTable.tsx
    │   │   ├── TrendChart.tsx
    │   │   └── ComparePanel.tsx
    │   ├── deployment/            Phase 4
    │   │   ├── SandboxPipeline.tsx
    │   │   ├── DeployConfirmModal.tsx
    │   │   ├── SqlDiffViewer.tsx
    │   │   └── RollbackPanel.tsx
    │   ├── models/                Phase 5
    │   │   ├── ModelCard.tsx
    │   │   └── VramBar.tsx
    │   ├── clients/               Phase 5
    │   │   ├── ClientList.tsx
    │   │   └── ClientEditForm.tsx
    │   ├── visualizer/            Phase 6
    │   │   ├── planParser.ts
    │   │   ├── operatorIcons.ts
    │   │   ├── PlanTree.tsx
    │   │   ├── PlanNode.tsx
    │   │   ├── PlanEdge.tsx
    │   │   └── PlanDiffContainer.tsx
    │   └── shared/
    │       ├── StatusBadge.tsx     ✅ Phase 1
    │       ├── LoadingSpinner.tsx  ✅ Phase 1
    │       └── EmptyState.tsx      ✅ Phase 1
    ├── hooks/
    │   ├── useInterval.ts      ✅ Phase 1
    │   ├── useSystemStats.ts   ✅ Phase 1
    │   ├── useSSE.ts           ⬅ Phase 2
    │   └── useJob.ts           ⬅ Phase 2
    ├── store/
    │   ├── systemStore.ts      ✅ Phase 1
    │   ├── clientStore.ts      ✅ Phase 1
    │   └── jobStore.ts         ⬅ Phase 2
    └── types/
        ├── system.ts           ✅ Phase 1
        ├── schema.ts           ✅ Phase 1
        └── index.ts            ✅ Phase 1 (stubs for job, history, client types)
```

---

*V4 Complete Phase Plan — 2026-03-21*
*Phase 1 complete: 48 files, 0 errors*
*8 phases total — CLI remains fully functional throughout*
