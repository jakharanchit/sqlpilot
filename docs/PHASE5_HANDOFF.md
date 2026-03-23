# SQL Optimization Agent — V4 Web UI · Phase 5 Handoff
> Paste this entire document at the start of the new chat.
> Everything needed to build Phase 5 without re-explaining anything.

---

## What This Project Is

A fully **offline, local** AI-powered web UI for a Python CLI tool called the **SQL Optimization Agent**. The CLI optimizes SQL Server queries using local Ollama models. V4 adds a React web UI on top. The CLI is never modified — the web UI calls into it via a FastAPI bridge.

**Hardware:** HP Omen Max 16, RTX 5070, Windows + WSL, SQL Server local dev.

---

## Locked Stack (unchanged)

| Layer | Choice |
|---|---|
| Frontend | React 18 + Vite + TypeScript |
| Styling | Tailwind CSS + CSS custom properties (no Tailwind compiler — use inline `<style>` injection in components) |
| Charts | **Recharts** |
| SQL Editor | **Monaco Editor** (`@monaco-editor/react`) — introduced in Phase 4 |
| State | Zustand |
| Backend bridge | FastAPI + Uvicorn |
| Fonts | `DM Sans` (UI), `JetBrains Mono` (code) — loaded via Google Fonts in `index.html` |
| Out of scope | Mobile, multi-user, cloud, dark mode toggle, PDF export |

---

## Complete Project File Structure (state after Phase 4)

```
sql-agent/
├── agent.py                    ← CLI entry point (unmodified forever)
├── config.py                   ← global settings (unmodified forever)
├── tools/                      ← 18 existing Python tools (unmodified forever)
│
├── bridge/
│   ├── __init__.py
│   ├── main.py                 ← DONE (Phase 4 — v4.0.0); update to v5.0.0 + 2 new routers
│   ├── requirements.txt
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── system.py           ← DONE (Phase 1)
│   │   ├── schema.py           ← DONE (Phase 1)
│   │   ├── jobs.py             ← DONE (Phase 2)
│   │   ├── history.py          ← DONE (Phase 3)
│   │   ├── migrations.py       ← DONE (Phase 3)
│   │   ├── deploy.py           ← DONE (Phase 4)
│   │   ├── sandbox.py          ← DONE (Phase 4)
│   │   ├── clients.py          ← Phase 5: STUB → full implementation
│   │   └── models.py           ← Phase 5: STUB → full implementation
│   └── services/
│       ├── __init__.py
│       ├── hardware.py         ← DONE (Phase 1)
│       ├── job_queue.py        ← DONE (Phase 4); add "pull_model" branch in Phase 5
│       └── sse.py              ← DONE (Phase 2)
│
└── web/
    ├── package.json            ← DONE (all deps present)
    ├── vite.config.ts          ← DONE
    ├── tailwind.config.ts      ← DONE
    ├── tsconfig.json           ← DONE
    ├── index.html              ← DONE
    └── src/
        ├── main.tsx            ← DONE
        ├── App.tsx             ← DONE (React Router, 8 routes)
        ├── index.css           ← DONE (design tokens, animations)
        ├── api/
        │   ├── client.ts       ← DONE
        │   ├── system.ts       ← DONE
        │   ├── schema.ts       ← DONE
        │   ├── jobs.ts         ← DONE
        │   ├── history.ts      ← DONE (Phase 3)
        │   ├── migrations.ts   ← DONE (Phase 3)
        │   ├── deploy.ts       ← DONE (Phase 4)
        │   ├── sandbox.ts      ← DONE (Phase 4)
        │   ├── clients.ts      ← Phase 5: STUB → full implementation
        │   └── models.ts       ← Phase 5: STUB → full implementation
        ├── pages/
        │   ├── Dashboard.tsx         ← DONE (Phase 1)
        │   ├── Optimizer.tsx         ← DONE (Phase 2)
        │   ├── History.tsx           ← DONE (Phase 3)
        │   ├── DeploymentGate.tsx    ← DONE (Phase 4)
        │   ├── PlanVisualizer.tsx    ← Phase 6: stub
        │   ├── ModelManager.tsx      ← Phase 5: STUB → full implementation
        │   ├── ClientManager.tsx     ← Phase 5: STUB → full implementation
        │   └── Settings.tsx          ← Phase 7: stub
        ├── components/
        │   ├── layout/               ← DONE (Phase 1)
        │   ├── dashboard/            ← DONE (Phase 1–2)
        │   ├── optimizer/            ← DONE (Phase 2)
        │   ├── history/              ← DONE (Phase 3)
        │   ├── migrations/           ← DONE (Phase 3)
        │   ├── deployment/           ← DONE (Phase 4)
        │   ├── visualizer/           ← Phase 6: stub
        │   ├── models/               ← Phase 5: CREATE all 4 components
        │   │   ├── ActiveModelsPanel.tsx
        │   │   ├── ModelCard.tsx
        │   │   ├── PullModelPanel.tsx
        │   │   └── RunningModelsPanel.tsx
        │   ├── clients/              ← Phase 5: CREATE all 3 components
        │   │   ├── ClientTable.tsx
        │   │   ├── NewClientModal.tsx
        │   │   └── ClientDetailPanel.tsx
        │   └── shared/               ← DONE (Phase 1)
        ├── hooks/
        │   ├── useInterval.ts        ← DONE (Phase 1)
        │   ├── useSystemStats.ts     ← DONE (Phase 1)
        │   ├── useSSE.ts             ← DONE (Phase 2)
        │   └── useJob.ts             ← DONE (Phase 2)
        ├── store/
        │   ├── systemStore.ts        ← DONE (Phase 1)
        │   ├── clientStore.ts        ← DONE (Phase 1)
        │   └── jobStore.ts           ← DONE (Phase 2)
        └── types/
            └── index.ts              ← DONE (Phase 4); append Phase 5 types
```

---

## Design System (unchanged — apply consistently)

### CSS Variables (defined in `index.css`)
```css
--bg-base:        #F8FAFC;
--bg-surface:     #FFFFFF;
--bg-elevated:    #F1F5F9;
--border:         #E2E8F0;
--border-strong:  #CBD5E1;
--text-primary:   #0F172A;
--text-secondary: #475569;
--text-muted:     #94A3B8;
--accent:         #2563EB;
--accent-light:   #DBEAFE;
--accent-hover:   #1D4ED8;
--success:        #16A34A;
--success-light:  #DCFCE7;
--warning:        #D97706;
--warning-light:  #FEF3C7;
--danger:         #DC2626;
--danger-light:   #FEE2E2;
--sidebar-width:  232px;
--topbar-height:  54px;
```

### Component Patterns
```css
.card           → white bg, 0.5px border, 10px radius
.badge          → inline pill label
.badge-success  → green
.badge-warning  → amber
.badge-danger   → red
.badge-info     → blue
.badge-neutral  → grey
.status-dot     → 8px circle indicator
.font-mono      → JetBrains Mono
```

### Styling Rule
**All component-specific styles go inside a `<style>` tag injected via a JS snippet at the bottom of each component** — same pattern as every Phase 1–4 component. Do not create separate CSS files.

```typescript
const _styles = `
.my-component { ... }
`;
if (typeof document !== 'undefined') {
  const id = 'my-component-styles';
  if (!document.getElementById(id)) {
    const el = document.createElement('style');
    el.id = id;
    el.textContent = _styles;
    document.head.appendChild(el);
  }
}
```

---

## Existing Types (from `web/src/types/index.ts` — Phases 1–4)

All previously defined. Do NOT remove or rename any of these:

```typescript
// Phase 1
SystemStats, CheckResult, SchemaTable, SchemaColumn, SchemaIndex, ViewDefinition

// Phase 2
JobStatus, JobType, JobRequest, MigrationRef, JobResult, Job, SSEEvent

// Phase 3
RunRecord, HistoryStats, TrendPoint, RunComparison, Migration

// Phase 4
ShadowDB, SandboxStep, SandboxResult, DeployPreview, DeployPackage
```

**Append these new types** to `types/index.ts` for Phase 5:

```typescript
// ── Phase 5 — Model Manager ───────────────────────────────────────────────────

// One pulled Ollama model
export interface OllamaModel {
  name:         string;       // "qwen2.5-coder:14b"
  size:         number;       // bytes
  size_gb:      string;       // "8.2 GB"
  digest:       string;       // sha256 hash prefix
  modified_at:  string;       // ISO timestamp
  family?:      string;       // "qwen2", "deepseek", etc. from details
  parameter_size?: string;    // "14B"
  quantization?:   string;    // "Q4_K_M"
}

// A model currently loaded in Ollama memory
export interface RunningModel {
  name:          string;
  size_vram:     number;    // bytes
  size_vram_gb:  string;    // "8.2 GB"
  expires_at:    string;    // ISO timestamp
}

// The configured model pair from config.py
export interface ActiveModels {
  optimizer: string;    // MODELS["optimizer"]
  reasoner:  string;    // MODELS["reasoner"]
  optimizer_available: boolean;   // true if pulled in Ollama
  reasoner_available:  boolean;
}

// Result from Ollama pull progress
export interface PullProgress {
  status:     string;   // "pulling manifest" | "downloading" | "verifying" | "success"
  completed?: number;   // bytes downloaded
  total?:     number;   // total bytes
  pct?:       number;   // 0–100
}

// ── Phase 5 — Client Manager ──────────────────────────────────────────────────

// One client workspace
export interface ClientRecord {
  name:          string;     // folder name e.g. "client_acme"
  display_name:  string;     // "Acme Corp"
  created:       string;     // "YYYY-MM-DD"
  database:      string;     // DB name from client.json
  server:        string;     // SQL Server name
  bak_path:      string;     // path to .bak
  migrations:    number;     // count of migration files
  runs:          number;     // count of run log files
  active:        boolean;    // is this the currently active client?
}

// Full config for one client (from client.json)
export interface ClientConfig {
  name:          string;
  display_name:  string;
  created:       string;
  notes:         string;
  db_config: {
    server:             string;
    database:           string;
    driver:             string;
    trusted_connection: string;
    username?:          string;
  };
  bak_path:       string;
  sandbox_data_dir: string;
  sandbox_timeout:  number;
}

// Paths for a client workspace
export interface ClientPaths {
  name:        string;
  base:        string;
  migrations:  string;
  reports:     string;
  deployments: string;
  snapshots:   string;
  runs:        string;
  history_db:  string;
  config_file: string;
}

// Payload for creating a new client
export interface NewClientRequest {
  name:          string;
  display_name?: string;
  server?:       string;
  database?:     string;
  bak_path?:     string;
  notes?:        string;
}

// Payload for updating a client
export interface UpdateClientRequest {
  display_name?: string;
  server?:       string;
  database?:     string;
  bak_path?:     string;
  notes?:        string;
}
```

Also add `'pull_model'` to the `JobType` union in `types/index.ts`:
```typescript
export type JobType =
  | 'full_run'
  | 'analyze'
  | 'optimize_file'
  | 'optimize_view'
  | 'benchmark'
  | 'workload'
  | 'plan'
  | 'sandbox_test'
  | 'pull_model';    // Phase 5
```

---

## Existing Tools Phase 5 Calls

All live in `tools/` at project root — never modify them.

```python
# Client management
from tools.client_manager import (
    list_clients,           # () → list[dict]
    get_active_client,      # () → str
    set_active_client,      # (name: str) → None  (raises ConfigError if not found)
    get_client_config,      # (client: str = None) → dict
    get_client_paths,       # (client: str = None) → dict
    create_client,          # (name, display_name, server, database, bak_path, notes, set_active) → dict
    update_client_config,   # (client, display_name, server, database, bak_path, notes) → dict
)
from tools.error_handler import ConfigError

# Ollama models — interact with Ollama API directly from the bridge
# No existing Python tool — call Ollama's HTTP API:
#   GET  http://localhost:11434/api/tags          → list pulled models
#   POST http://localhost:11434/api/pull          → pull model (streaming NDJSON)
#   DELETE http://localhost:11434/api/delete      → delete model
#   GET  http://localhost:11434/api/show          → model details
#   GET  http://localhost:11434/api/ps            → currently loaded models
```

### Exact `list_clients()` return shape
```python
list_clients() -> [
    {
        "name":         str,    # "client_acme"
        "display_name": str,    # "Acme Corp"
        "created":      str,    # "2026-03-21" (first 10 chars of created timestamp)
        "database":     str,    # "AcmeDev"
        "server":       str,    # "localhost"
        "bak_path":     str,    # path or ""
        "migrations":   int,    # count
        "runs":         int,    # count
        "active":       bool,   # is this the active client?
    },
    ...
]
```

### Exact `get_client_config()` return shape
```python
get_client_config(client=None) -> {
    "name":         str,
    "display_name": str,
    "created":      str,
    "notes":        str,
    "db_config": {
        "server":             str,
        "database":           str,
        "driver":             str,
        "trusted_connection": str,
        "username":           str,   # only if SQL auth
        "password":           str,   # only if SQL auth
    },
    "bak_path":        str,
    "sandbox_data_dir":str,
    "sandbox_timeout": int,
}
```

### Exact `create_client()` return shape
```python
create_client(
    name, display_name="", server="", database="",
    bak_path="", notes="", set_active=True
) -> {
    "name":   str,
    "paths":  dict,   # same shape as get_client_paths()
    "config": dict,   # same shape as get_client_config()
}
# Raises ConfigError if name contains invalid characters or already exists.
```

### Ollama API used directly from the bridge

```python
import requests

OLLAMA_BASE = "http://localhost:11434"

# List available models
r = requests.get(f"{OLLAMA_BASE}/api/tags")
# r.json() → {
#   "models": [
#     {
#       "name": "qwen2.5-coder:14b",
#       "size": 8828590080,          # bytes
#       "digest": "sha256:abc...",
#       "modified_at": "2026-03-01T...",
#       "details": {
#         "family": "qwen2",
#         "parameter_size": "14B",
#         "quantization_level": "Q4_K_M"
#       }
#     },
#     ...
#   ]
# }

# Delete model
r = requests.delete(f"{OLLAMA_BASE}/api/delete", json={"name": "model:tag"})

# Show model info
r = requests.post(f"{OLLAMA_BASE}/api/show", json={"name": "model:tag"})

# Currently loaded (running) models
r = requests.get(f"{OLLAMA_BASE}/api/ps")
# r.json() → {
#   "models": [
#     {
#       "name": "qwen2.5-coder:14b",
#       "size_vram": 8500000000,
#       "expires_at": "2026-03-22T..."
#     }
#   ]
# }

# Pull model — streaming NDJSON (used by the job_queue pull_model branch)
r = requests.post(f"{OLLAMA_BASE}/api/pull", json={"name": "model:tag"}, stream=True)
for line in r.iter_lines():
    if line:
        data = json.loads(line)
        # data = {"status": "downloading", "completed": 1234, "total": 8828590080}
        # data = {"status": "success"}         ← final line
```

---

## Existing API (Phases 1–4 — working, do not change)

```
GET  /api/health
GET  /api/system/stats
GET  /api/system/check
PUT  /api/system/poll?interval_ms=N
GET  /api/schema/all
GET  /api/schema/tables
GET  /api/schema/views
GET  /api/schema/table/{name}
GET  /api/schema/view/{name}
POST   /api/jobs
GET    /api/jobs
GET    /api/jobs/{job_id}
GET    /api/jobs/{job_id}/stream    ← SSE
DELETE /api/jobs/{job_id}
GET    /api/history
GET    /api/history/stats
GET    /api/history/trend
GET    /api/history/compare
GET    /api/history/{run_id}
DELETE /api/history/{run_id}
GET    /api/migrations
GET    /api/migrations/{number}
POST   /api/migrations/{number}/apply
POST   /api/migrations/{number}/rollback
GET    /api/deploy/preview
POST   /api/deploy/generate
GET    /api/deploy/packages
GET    /api/deploy/packages/{folder}/files/{filename}
POST   /api/sandbox/test
GET    /api/sandbox/shadows
DELETE /api/sandbox/shadows/{name}
GET    /api/sandbox/config
```

---

## Phase 5 Scope

**Goal:** Two management pages — Model Manager lets the user see which Ollama models are pulled, pull new ones with live download progress via SSE, and delete unused ones. Client Manager lets the user see all client workspaces, switch between them, create new ones, and edit per-client DB config (server, database, .bak path).

**Done when:**
- Model Manager: user can see pulled models with sizes, see which models are configured as optimizer/reasoner, pull a new model by name and watch live download progress, delete a model.
- Client Manager: user can see all clients with the active one highlighted, switch to a different client (reflected instantly in the sidebar), create a new client via a form modal, and edit a client's connection settings.

---

## Phase 5 API to Build

### `bridge/routers/models.py`

```python
GET  /api/models
     # Returns all models pulled in Ollama + which are configured as active.
     → { models: OllamaModel[], active: ActiveModels }

GET  /api/models/running
     # Returns models currently loaded in Ollama memory.
     → RunningModel[]

POST /api/models/pull
     # Enqueues a pull job via job_queue (job type: "pull_model").
     # Client streams download progress via /api/jobs/{id}/stream.
     body: { name: str }
     → Job

DELETE /api/models/{model_name}
     # Deletes model from Ollama. model_name may include colon, URL-encode it.
     → { deleted: bool, name: str }
```

### `bridge/routers/clients.py`

```python
GET  /api/clients
     → ClientRecord[]

GET  /api/clients/active
     → { name: str, config: ClientConfig, paths: ClientPaths }

POST /api/clients/{name}/switch
     # Calls set_active_client(name). Returns updated active client info.
     → { name: str, config: ClientConfig, paths: ClientPaths }

POST /api/clients
     # Creates a new client workspace.
     body: NewClientRequest
     → { name: str, config: ClientConfig, paths: ClientPaths }

GET  /api/clients/{name}
     # Full config + paths for a named client.
     → { name: str, config: ClientConfig, paths: ClientPaths }

PUT  /api/clients/{name}
     # Update client settings. Only fields present in body are changed.
     body: UpdateClientRequest
     → ClientConfig

DELETE /api/clients/{name}
     # Delete a client workspace. Blocked if it is the currently active client.
     → { deleted: bool, name: str }
```

### Update `bridge/main.py`
```python
from bridge.routers import clients, models   # Phase 5
app.include_router(clients.router)
app.include_router(models.router)
# Version bump: "5.0.0"
```

---

## `bridge/routers/models.py` Implementation Guide

```python
from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import requests
import json

try:
    from config import OLLAMA_BASE_URL, MODELS
except ImportError:
    OLLAMA_BASE_URL = "http://localhost:11434"
    MODELS = {}

router = APIRouter(prefix="/api/models", tags=["models"])


def _bytes_to_gb(b: int) -> str:
    return f"{b / 1_073_741_824:.1f} GB"


def _ollama(path: str, method="GET", **kwargs):
    """Simple wrapper around Ollama HTTP API."""
    url = f"{OLLAMA_BASE_URL}{path}"
    try:
        r = requests.request(method, url, timeout=10, **kwargs)
        r.raise_for_status()
        return r
    except requests.exceptions.ConnectionError:
        raise HTTPException(503, "Ollama is not running. Start it with: ollama serve")
    except requests.exceptions.HTTPError as e:
        raise HTTPException(r.status_code, str(e))


@router.get("")
def list_models():
    r = _ollama("/api/tags")
    raw_models = r.json().get("models", [])

    models = []
    for m in raw_models:
        details = m.get("details", {})
        models.append({
            "name":           m["name"],
            "size":           m.get("size", 0),
            "size_gb":        _bytes_to_gb(m.get("size", 0)),
            "digest":         m.get("digest", "")[:12],
            "modified_at":    m.get("modified_at", ""),
            "family":         details.get("family", ""),
            "parameter_size": details.get("parameter_size", ""),
            "quantization":   details.get("quantization_level", ""),
        })

    pulled_names = {m["name"] for m in models}
    active = {
        "optimizer":           MODELS.get("optimizer", ""),
        "reasoner":            MODELS.get("reasoner", ""),
        "optimizer_available": MODELS.get("optimizer", "") in pulled_names,
        "reasoner_available":  MODELS.get("reasoner", "") in pulled_names,
    }

    return {"models": models, "active": active}


@router.get("/running")
def running_models():
    r = _ollama("/api/ps")
    raw = r.json().get("models", [])
    return [
        {
            "name":         m["name"],
            "size_vram":    m.get("size_vram", 0),
            "size_vram_gb": _bytes_to_gb(m.get("size_vram", 0)),
            "expires_at":   m.get("expires_at", ""),
        }
        for m in raw
    ]


class PullRequest(BaseModel):
    name: str


@router.post("/pull")
def pull_model(body: PullRequest):
    """
    Enqueues a model pull as a background job.
    The pull streams NDJSON progress from Ollama and forwards via SSE.
    Client streams: GET /api/jobs/{id}/stream
    """
    from bridge.services.job_queue import enqueue_job
    job = enqueue_job({
        "type":       "pull_model",
        "model_name": body.name.strip(),
    })
    return job


@router.delete("/{model_name:path}")
def delete_model(model_name: str):
    """
    Deletes a model from Ollama.
    model_name may contain colon (e.g. "qwen2.5-coder:14b") — use :path matcher.
    """
    _ollama("/api/delete", method="DELETE", json={"name": model_name})
    return {"deleted": True, "name": model_name}
```

**Important:** Add the `pull_model` branch to `bridge/services/job_queue.py` `_execute_job()`:

```python
elif jtype == "pull_model":
    import requests as _req
    import json as _json

    model_name = job.request.get("model_name", "")
    _emit(job, "log", {"line": f"Pulling model: {model_name}"})

    try:
        from config import OLLAMA_BASE_URL
    except ImportError:
        OLLAMA_BASE_URL = "http://localhost:11434"

    r = _req.post(
        f"{OLLAMA_BASE_URL}/api/pull",
        json={"name": model_name},
        stream=True,
        timeout=600,   # pulling can take minutes
    )

    last_pct = -1
    for line in r.iter_lines():
        if not line:
            continue
        data = _json.loads(line)
        status    = data.get("status", "")
        completed = data.get("completed", 0)
        total     = data.get("total", 0)

        if total and completed:
            pct = int((completed / total) * 100)
            if pct != last_pct:
                last_pct = pct
                _emit(job, "step", {
                    "step":    pct,
                    "total":   100,
                    "label":   f"{status} — {pct}%",
                })
                _emit(job, "log", {
                    "line": f"  {status}: {pct}% ({completed/1e9:.1f}GB / {total/1e9:.1f}GB)"
                })
        else:
            _emit(job, "log", {"line": f"  {status}"})

        if status == "success":
            break

    job.result = {"model_name": model_name, "status": "pulled"}
    job.status = "complete"
    _emit(job, "complete", {"result": job.result})
```

---

## `bridge/routers/clients.py` Implementation Guide

```python
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from tools.client_manager import (
    list_clients, get_active_client, set_active_client,
    get_client_config, get_client_paths, create_client, update_client_config,
)
from tools.error_handler import ConfigError

router = APIRouter(prefix="/api/clients", tags=["clients"])


class NewClientBody(BaseModel):
    name:          str
    display_name:  Optional[str] = ""
    server:        Optional[str] = ""
    database:      Optional[str] = ""
    bak_path:      Optional[str] = ""
    notes:         Optional[str] = ""


class UpdateClientBody(BaseModel):
    display_name:  Optional[str] = None
    server:        Optional[str] = None
    database:      Optional[str] = None
    bak_path:      Optional[str] = None
    notes:         Optional[str] = None


def _client_detail(name: str) -> dict:
    """Returns a consistent {name, config, paths} dict for any client."""
    config = get_client_config(name)
    paths  = get_client_paths(name)
    # Strip password from config for safety
    if "db_config" in config and "password" in config["db_config"]:
        config["db_config"]["password"] = "***"
    return {"name": name, "config": config, "paths": paths}


@router.get("")
def get_clients():
    return list_clients()


@router.get("/active")
def get_active():
    name = get_active_client()
    return _client_detail(name)


@router.post("/{name}/switch")
def switch_client(name: str):
    try:
        set_active_client(name)
    except ConfigError as e:
        raise HTTPException(404, str(e))
    return _client_detail(name)


@router.post("")
def new_client(body: NewClientBody):
    try:
        result = create_client(
            name         = body.name,
            display_name = body.display_name or "",
            server       = body.server       or "",
            database     = body.database     or "",
            bak_path     = body.bak_path     or "",
            notes        = body.notes        or "",
            set_active   = False,   # don't auto-switch — let user decide
        )
    except ConfigError as e:
        raise HTTPException(400, str(e))
    return _client_detail(result["name"])


@router.get("/{name}")
def get_client(name: str):
    try:
        return _client_detail(name)
    except Exception as e:
        raise HTTPException(404, str(e))


@router.put("/{name}")
def update_client(name: str, body: UpdateClientBody):
    try:
        cfg = update_client_config(
            client       = name,
            display_name = body.display_name,
            server       = body.server,
            database     = body.database,
            bak_path     = body.bak_path,
            notes        = body.notes,
        )
    except ConfigError as e:
        raise HTTPException(400, str(e))
    # Strip password
    if "db_config" in cfg and "password" in cfg["db_config"]:
        cfg["db_config"]["password"] = "***"
    return cfg


@router.delete("/{name}")
def delete_client(name: str):
    """
    Delete a client workspace folder.
    Safety rule: cannot delete the currently active client.
    """
    active = get_active_client()
    if name == active:
        raise HTTPException(400, f"Cannot delete the active client '{name}'. Switch to another client first.")

    import shutil
    from pathlib import Path
    try:
        from config import PROJECTS_DIR
    except ImportError:
        from config import BASE_DIR
        PROJECTS_DIR = str(Path(BASE_DIR) / "projects")

    client_dir = Path(PROJECTS_DIR) / name
    if not client_dir.exists():
        raise HTTPException(404, f"Client '{name}' not found")

    shutil.rmtree(str(client_dir))
    return {"deleted": True, "name": name}
```

---

## `api/models.ts` Shape

```typescript
import { apiFetch } from './client';
import type { OllamaModel, RunningModel, ActiveModels, Job } from '../types';

export const modelsApi = {
  /** List all pulled models + active config. */
  list: (): Promise<{ models: OllamaModel[]; active: ActiveModels }> =>
    apiFetch('/api/models'),

  /** Models currently loaded in Ollama memory. */
  running: (): Promise<RunningModel[]> =>
    apiFetch('/api/models/running'),

  /** Enqueue a pull job. Stream progress via /api/jobs/{id}/stream. */
  pull: (name: string): Promise<Job> =>
    apiFetch<Job>('/api/models/pull', {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify({ name }),
    }),

  /** Delete a model from Ollama. */
  delete: (name: string): Promise<{ deleted: boolean; name: string }> =>
    apiFetch(`/api/models/${encodeURIComponent(name)}`, { method: 'DELETE' }),
};
```

## `api/clients.ts` Shape

```typescript
import { apiFetch } from './client';
import type {
  ClientRecord, ClientConfig, ClientPaths,
  NewClientRequest, UpdateClientRequest,
} from '../types';

interface ClientDetail {
  name:   string;
  config: ClientConfig;
  paths:  ClientPaths;
}

export const clientsApi = {
  list: (): Promise<ClientRecord[]> =>
    apiFetch('/api/clients'),

  active: (): Promise<ClientDetail> =>
    apiFetch('/api/clients/active'),

  switchTo: (name: string): Promise<ClientDetail> =>
    apiFetch(`/api/clients/${encodeURIComponent(name)}/switch`, { method: 'POST' }),

  create: (body: NewClientRequest): Promise<ClientDetail> =>
    apiFetch('/api/clients', {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify(body),
    }),

  get: (name: string): Promise<ClientDetail> =>
    apiFetch(`/api/clients/${encodeURIComponent(name)}`),

  update: (name: string, body: UpdateClientRequest): Promise<ClientConfig> =>
    apiFetch(`/api/clients/${encodeURIComponent(name)}`, {
      method:  'PUT',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify(body),
    }),

  delete: (name: string): Promise<{ deleted: boolean; name: string }> =>
    apiFetch(`/api/clients/${encodeURIComponent(name)}`, { method: 'DELETE' }),
};
```

---

## Model Manager Page Layout

```
┌──────────────────────────────────────────────────────────────┐
│  MODEL MANAGER                                               │
│  subtitle: Manage local Ollama models                        │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  ACTIVE MODELS (from config.py)                      │   │
│  │                                                      │   │
│  │  Optimizer  qwen2.5-coder:14b  [● available]         │   │
│  │  Reasoner   deepseek-r1:14b    [● available]         │   │
│  │                                                      │   │
│  │  ⓘ Edit config.py to change which models are used    │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  AVAILABLE MODELS (2 pulled)        [↻ Refresh]      │   │
│  │                                                      │   │
│  │  ┌──────────────────────────────────────────────┐   │   │
│  │  │  qwen2.5-coder:14b                           │   │   │
│  │  │  8.2 GB · Q4_K_M · qwen2 · modified 3d ago  │   │   │
│  │  │  [used as optimizer]              [Delete]   │   │   │
│  │  ├──────────────────────────────────────────────┤   │   │
│  │  │  deepseek-r1:14b                             │   │   │
│  │  │  9.1 GB · Q4_K_M · deepseek · modified 3d   │   │   │
│  │  │  [used as reasoner]               [Delete]   │   │   │
│  │  └──────────────────────────────────────────────┘   │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  PULL NEW MODEL                                      │   │
│  │  [  model name e.g. llama3.2:3b  ]   [▶ Pull]       │   │
│  │                                                      │   │
│  │  (after pull starts — shows job progress)            │   │
│  │  Downloading deepseek-r1:7b                          │   │
│  │  ████████████░░░░░  61% — 5.6 GB / 9.1 GB           │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  CURRENTLY LOADED (in Ollama memory)                 │   │
│  │  qwen2.5-coder:14b  8.2 GB VRAM  expires in 4 min   │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

---

## Client Manager Page Layout

```
┌──────────────────────────────────────────────────────────────┐
│  CLIENT MANAGER                   [+ New Client]             │
│  subtitle: Manage isolated client workspaces                 │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  CLIENT TABLE                                        │   │
│  │                                                      │   │
│  │  ★  client_acme  Acme Corp   AcmeDev  2 mig  5 runs │   │
│  │     client_xyz   XYZ Corp    XYZDev   0 mig  0 runs │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  SELECTED: client_acme   [★ Active]                  │   │
│  │                                                      │   │
│  │  Display name   Acme Corp                            │   │
│  │  Server         localhost                            │   │
│  │  Database       AcmeDev                              │   │
│  │  BAK path       C:\Backups\AcmeDev.bak               │   │
│  │  Auth           Windows                              │   │
│  │  Notes          —                                    │   │
│  │  Migrations     migrations/  (2 files)               │   │
│  │  History DB     history.db                           │   │
│  │                                                      │   │
│  │  [Edit Settings]    [Switch to This Client]          │   │
│  │                     [Delete Client]  (disabled if    │   │
│  │                                       active)        │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
└──────────────────────────────────────────────────────────────┘

[NEW CLIENT MODAL — appears when + New Client clicked]
┌────────────────────────────────────┐
│  New Client Workspace              │
│                                    │
│  Folder name *   [client_xyz     ] │
│  Display name    [XYZ Corp       ] │
│  Server          [localhost      ] │
│  Database        [XYZDev         ] │
│  BAK path        [C:\Backups\... ] │
│  Notes           [               ] │
│                                    │
│  [Cancel]    [Create Workspace]    │
└────────────────────────────────────┘

[EDIT SETTINGS — inline in ClientDetailPanel, or a small modal]
Same fields as New Client, pre-filled with existing values.
```

---

## Component Specifications

### `ActiveModelsPanel.tsx`
- Fetches `GET /api/models` on mount
- Shows two rows: Optimizer and Reasoner
- Each row: model name in monospace + availability badge (green "● available" / red "✗ not pulled")
- If a configured model is not pulled: shows a warning with the pull command
- Static info note: "Edit MODELS in config.py to change which models are used"
- No edit capability in the UI — config.py is the source of truth

### `ModelCard.tsx`
Props:
```typescript
interface Props {
  model:       OllamaModel;
  activeRoles: string[];     // e.g. ["optimizer"] or [] — derived from ActiveModels
  onDelete:    (name: string) => void;
  deleting:    boolean;
}
```
- Displays: name (monospace), size_gb, parameter_size, quantization, family, modified date
- If model is active (in `activeRoles`): shows a coloured badge e.g. `[optimizer]`, `[reasoner]`
- Delete button — shows confirm-inline (replace button text with "Confirm?" for 3 seconds before calling `onDelete`)
- Delete is disabled if the model is currently configured as active (show tooltip: "Remove from config.py first")

### `PullModelPanel.tsx`
State machine: `idle → pulling → complete | failed`
- Text input for model name with placeholder `e.g. llama3.2:3b`
- Suggested models list (static): `qwen2.5-coder:14b`, `deepseek-r1:14b`, `llama3.2:3b`, `phi4:14b`, `codellama:13b` — click to fill input
- Pull button → calls `modelsApi.pull(name)` → gets back a Job
- Subscribes to `/api/jobs/{id}/stream` (reuse existing SSE pattern — same as optimizer/sandbox)
- Progress bar driven by `step` SSE events (step=pct, total=100)
- Live log shows download status lines
- On complete: "✓ Model pulled successfully" + reset to idle
- On failed: error message + retry button

### `RunningModelsPanel.tsx`
- Fetches `GET /api/models/running` on mount + polls every 30s via `useInterval`
- Shows loaded models with VRAM usage and expiry time
- If empty: `"No models currently loaded — models load automatically when a job runs"`
- Small panel, low visual weight

### `ClientTable.tsx`
Props:
```typescript
interface Props {
  clients:          ClientRecord[];
  selectedName:     string | null;
  onSelect:         (name: string) => void;
  onSwitch:         (name: string) => void;
  loading:          boolean;
}
```
- Full-width table: ★ (active indicator), Name, Display Name, Database, Migrations, Runs, Created
- Active client row highlighted with left border accent
- Clicking a row calls `onSelect` — loads detail panel
- [Switch] button on active row is disabled with label "Active"
- [Switch] on non-active rows calls `onSwitch`

### `NewClientModal.tsx`
Props:
```typescript
interface Props {
  isOpen:    boolean;
  onCancel:  () => void;
  onCreated: (name: string) => void;
}
```
- Modal form with fields: name (required, slug validated), display_name, server, database, bak_path, notes
- Name field: validates slug format (`/^[a-zA-Z0-9_-]+$/`) inline as user types
- On submit: calls `clientsApi.create(body)` → on success calls `onCreated(name)`
- Loading state on Create button
- Error display if API returns 400

### `ClientDetailPanel.tsx`
Props:
```typescript
interface Props {
  name:      string;
  onSwitch:  (name: string) => void;
  onDeleted: (name: string) => void;
  onUpdated: () => void;
  isActive:  boolean;
}
```
State: `viewing | editing`

**Viewing mode:**
- Shows all config fields read-only
- [Edit Settings] button → switches to editing mode
- [Switch to This Client] button → calls `onSwitch(name)` — disabled if already active
- [Delete Client] button → confirm inline before calling delete — always disabled if active (tooltip: "Cannot delete the active client")

**Editing mode:**
- Inline form with same fields as NewClientModal (except name — name is immutable)
- [Save] / [Cancel] buttons
- On save: calls `clientsApi.update(name, body)` → on success calls `onUpdated()` and returns to viewing

---

## `ModelManager.tsx` Page Structure

```typescript
export default function ModelManager() {
  const [data,       setData]       = useState<{ models: OllamaModel[]; active: ActiveModels } | null>(null);
  const [running,    setRunning]    = useState<RunningModel[]>([]);
  const [loading,    setLoading]    = useState(true);
  const [deleting,   setDeleting]   = useState<string | null>(null);

  async function load() {
    setLoading(true);
    try {
      const [modelsData, runningData] = await Promise.all([
        modelsApi.list(),
        modelsApi.running(),
      ]);
      setData(modelsData);
      setRunning(runningData);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { load(); }, []);

  async function handleDelete(name: string) {
    setDeleting(name);
    try {
      await modelsApi.delete(name);
      await load();   // refresh list
    } finally {
      setDeleting(null);
    }
  }

  // Active roles lookup: which models fill which roles
  const activeRoles = (modelName: string): string[] => {
    if (!data) return [];
    const roles = [];
    if (data.active.optimizer === modelName) roles.push('optimizer');
    if (data.active.reasoner  === modelName) roles.push('reasoner');
    return roles;
  };

  return (
    <div className="mm-page">
      <PageHeader title="Model Manager" subtitle="Manage local Ollama models" />
      {data && <ActiveModelsPanel active={data.active} />}
      <section>
        <div className="mm-section-header">
          Available Models ({data?.models.length ?? 0} pulled)
          <button onClick={load}>↻ Refresh</button>
        </div>
        {loading && <LoadingSpinner />}
        {data?.models.map(m => (
          <ModelCard
            key={m.name}
            model={m}
            activeRoles={activeRoles(m.name)}
            onDelete={handleDelete}
            deleting={deleting === m.name}
          />
        ))}
      </section>
      <PullModelPanel onPulled={load} />
      <RunningModelsPanel running={running} />
    </div>
  );
}
```

## `ClientManager.tsx` Page Structure

```typescript
export default function ClientManager() {
  const [clients,      setClients]      = useState<ClientRecord[]>([]);
  const [selectedName, setSelectedName] = useState<string | null>(null);
  const [activeClient, setActiveClient] = useState<string>('');
  const [showNewModal, setShowNewModal] = useState(false);
  const [loading,      setLoading]      = useState(true);

  async function load() {
    setLoading(true);
    try {
      const [list, active] = await Promise.all([
        clientsApi.list(),
        clientsApi.active(),
      ]);
      setClients(list);
      setActiveClient(active.name);
      // Auto-select the active client on first load
      if (!selectedName) setSelectedName(active.name);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { load(); }, []);

  async function handleSwitch(name: string) {
    await clientsApi.switchTo(name);
    await load();
    // TODO Phase 5: update clientStore so sidebar updates instantly
  }

  return (
    <div className="cm-page">
      <PageHeader
        title="Client Manager"
        subtitle="Manage isolated client workspaces"
        action={<button onClick={() => setShowNewModal(true)}>+ New Client</button>}
      />
      <ClientTable
        clients={clients}
        selectedName={selectedName}
        onSelect={setSelectedName}
        onSwitch={handleSwitch}
        loading={loading}
      />
      {selectedName && (
        <ClientDetailPanel
          name={selectedName}
          isActive={selectedName === activeClient}
          onSwitch={handleSwitch}
          onDeleted={(name) => {
            setSelectedName(null);
            load();
          }}
          onUpdated={load}
        />
      )}
      <NewClientModal
        isOpen={showNewModal}
        onCancel={() => setShowNewModal(false)}
        onCreated={(name) => {
          setShowNewModal(false);
          load();
          setSelectedName(name);
        }}
      />
    </div>
  );
}
```

**Zustand clientStore update:** After a successful client switch, update `clientStore` so the sidebar active client label updates immediately. The `clientStore` from Phase 1 already tracks the active client — call its `setActiveClient` action after `handleSwitch` resolves.

---

## SSE Reuse Pattern for `PullModelPanel`

Same pattern as `SandboxRunner` in Phase 4. The pull progress arrives as SSE events:
```typescript
// step events drive the progress bar:
// { type: "step", payload: { step: 61, total: 100, label: "downloading — 61%" } }

// log events show status text:
// { type: "log",  payload: { line: "  downloading: 61% (5.6GB / 9.1GB)" } }

// complete:
// { type: "complete", payload: { result: { model_name: "...", status: "pulled" } } }
```

The progress bar in `PullModelPanel` should use `payload.step / payload.total * 100` directly as the `%` fill width (CSS `width: ${pct}%` on a bar element). No need for the `ProgressBar` Textual widget — just a simple `<div>` with dynamic width.

---

## Clientstore Note (from Phase 1)

`clientStore.ts` already exists from Phase 1. It tracks the currently active client name for the sidebar. After a `clientsApi.switchTo()` succeeds in `ClientManager`, call:

```typescript
import { useClientStore } from '../store/clientStore';
const { setActiveClient } = useClientStore();
// ... after switch:
setActiveClient(newName);
```

This ensures the sidebar shows the correct active client name without a full page reload.

---

## What Phase 5 Does NOT Touch

- `agent.py` — never modified
- `tools/` — read-only from bridge
- Any Phase 1–4 components or pages
- `index.css` — do not modify (use inline `<style>` in components)
- `useSSE.ts`, `useJob.ts` — use as-is, do not modify
- `bridge/services/sse.py` — do not modify
- `types/index.ts` — only append new types, never remove existing ones

---

## Phase 4 Bug Fixed (already in outputs)

The following bug existed in the Phase 4 deliverables and was corrected before this handoff was written. The corrected files are in the Phase 4 outputs — apply them:

**Bug:** `SandboxRunner.tsx` Props only had `onPassed`. When the sandbox failed, `DeploymentGate`'s `sandboxRan` state was never set to `true`, so the Generate button stayed in the "not tested" state instead of showing "Fix sandbox failures first".

**Fix applied:**
1. Added `onFailed?: () => void` to `SandboxRunner` Props
2. `onFailed?.()` called when `phase` transitions to `'failed'` (both SSE `complete` and `error` paths)
3. `DeploymentGate.tsx` wired: `onFailed={() => handleSandboxFailed()}`

---

## How to Start Phase 5

```bash
# Backend:
# 1. Create bridge/routers/models.py
# 2. Create bridge/routers/clients.py
# 3. Update bridge/main.py (2 lines: import + include_router, version → 5.0.0)
# 4. Add "pull_model" branch to bridge/services/job_queue.py _execute_job()
# 5. Restart: uvicorn bridge.main:app --reload

# Frontend:
# 6. Append Phase 5 types + "pull_model" JobType to web/src/types/index.ts
# 7. Create web/src/api/models.ts
# 8. Create web/src/api/clients.ts
# 9. Create 4 model components (models/)
# 10. Create 3 client components (clients/)
# 11. Replace web/src/pages/ModelManager.tsx stub
# 12. Replace web/src/pages/ClientManager.tsx stub
```

---

## Build Phases Overview

| Phase | Scope | Status |
|---|---|---|
| 1 | FastAPI bridge + React scaffold + Dashboard with live hardware gauges | **COMPLETE** |
| 2 | Query Optimizer — SSE job streaming, full pipeline execution | **COMPLETE** |
| 3 | History & Trends — runs table, Recharts trend chart, compare, migrations | **COMPLETE** |
| 4 | Deployment Gate — sandbox lifecycle, Monaco SQL preview, confirm modal | **COMPLETE** |
| 5 | Model Manager + Client Manager | **← BUILD THIS** |
| 6 | Plan Visualizer — D3 tree layout of execution plan operators | Pending |
| 7 | Settings page — config.py editable from UI | Pending |
| 8 | Polish + production build | Pending |

---

## Phase 5 File Checklist (14 files total)

**Backend (4 files):**
- [ ] `bridge/routers/models.py` — 4 endpoints
- [ ] `bridge/routers/clients.py` — 6 endpoints
- [ ] `bridge/main.py` — 2 lines added, version bumped to 5.0.0
- [ ] `bridge/services/job_queue.py` — add `pull_model` branch

**Frontend (10 files):**
- [ ] `web/src/types/index.ts` — append 9 new types + add `pull_model` to `JobType`
- [ ] `web/src/api/models.ts` — 4 methods
- [ ] `web/src/api/clients.ts` — 7 methods
- [ ] `web/src/components/models/ActiveModelsPanel.tsx`
- [ ] `web/src/components/models/ModelCard.tsx`
- [ ] `web/src/components/models/PullModelPanel.tsx`
- [ ] `web/src/components/models/RunningModelsPanel.tsx`
- [ ] `web/src/components/clients/ClientTable.tsx`
- [ ] `web/src/components/clients/NewClientModal.tsx`
- [ ] `web/src/components/clients/ClientDetailPanel.tsx`
- [ ] `web/src/pages/ModelManager.tsx` — replace stub
- [ ] `web/src/pages/ClientManager.tsx` — replace stub

That's 14 files (12 new + 2 updated).

---

*Phase 5 Handoff · SQL Optimization Agent V4 · 2026-03-22*
*Phase 1 + Phase 2 + Phase 3 + Phase 4 complete · 42 files total*
