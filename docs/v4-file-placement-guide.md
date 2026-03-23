# V4 Phase 1 — File Placement Guide
> Every file you received, where it goes, and what it does.
> 48 files total. 3 actions to set up.

---

## The 3 Setup Actions

```
ACTION 1 — Copy bridge/ folder into project root
ACTION 2 — Copy web/ folder into project root
ACTION 3 — Paste serve command into agent.py
```

---

## Final Project Structure After Setup

```
sql-agent/                                     ← YOUR EXISTING PROJECT ROOT
│
│  ╔══════════════════════════════════════╗
│  ║  EXISTING — do not touch            ║
│  ╠══════════════════════════════════════╣
├── agent.py                               ← MODIFY: paste serve command block at bottom
├── config.py                              ← unchanged
├── tools/                                 ← unchanged (all 18 tools)
├── migrations/                            ← unchanged
├── runs/                                  ← unchanged
├── reports/                               ← unchanged
├── deployments/                           ← unchanged
├── snapshots/                             ← unchanged
├── history.db                             ← unchanged (jobs table added automatically on first run)
│  ╚══════════════════════════════════════╝
│
│  ╔══════════════════════════════════════╗
│  ║  NEW — copy from v4/bridge/         ║
│  ╠══════════════════════════════════════╣
├── bridge/
│   ├── __init__.py
│   ├── main.py
│   ├── requirements.txt
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── system.py
│   │   └── schema.py
│   └── services/
│       ├── __init__.py
│       ├── hardware.py
│       └── job_queue.py
│  ╚══════════════════════════════════════╝
│
│  ╔══════════════════════════════════════╗
│  ║  NEW — copy from v4/web/            ║
│  ╠══════════════════════════════════════╣
└── web/
    ├── index.html
    ├── package.json
    ├── vite.config.ts
    ├── tailwind.config.ts
    ├── tsconfig.json
    ├── tsconfig.node.json
    ├── postcss.config.js
    └── src/
        ├── main.tsx
        ├── App.tsx
        ├── index.css
        ├── api/
        │   ├── client.ts
        │   ├── system.ts
        │   └── schema.ts
        ├── components/
        │   ├── dashboard/
        │   │   ├── ActiveJobCard.tsx
        │   │   ├── HardwareGauges.tsx
        │   │   ├── RecentRunsPanel.tsx
        │   │   └── SystemStatusRow.tsx
        │   ├── layout/
        │   │   ├── PageShell.tsx
        │   │   ├── Sidebar.tsx
        │   │   └── TopBar.tsx
        │   └── shared/
        │       ├── EmptyState.tsx
        │       ├── LoadingSpinner.tsx
        │       └── StatusBadge.tsx
        ├── hooks/
        │   ├── useInterval.ts
        │   └── useSystemStats.ts
        ├── pages/
        │   ├── Dashboard.tsx
        │   ├── Optimizer.tsx         ← stub, replaced in Phase 2
        │   ├── PlanVisualizer.tsx    ← stub, replaced in Phase 6
        │   ├── DeploymentGate.tsx    ← stub, replaced in Phase 4
        │   ├── History.tsx           ← stub, replaced in Phase 3
        │   ├── ModelManager.tsx      ← stub, replaced in Phase 5
        │   ├── ClientManager.tsx     ← stub, replaced in Phase 5
        │   └── Settings.tsx          ← stub, replaced in Phase 7
        ├── store/
        │   ├── clientStore.ts
        │   └── systemStore.ts
        └── types/
            ├── index.ts
            ├── schema.ts
            └── system.ts
   ╚══════════════════════════════════════╝
```

---

## Every File — What It Does

### ACTION 3 — Special file (not copied, pasted)

| File | What to do |
|---|---|
| `serve_command_for_agent_py.py` | Open it, copy everything inside, paste into `agent.py` just above the final `if __name__ == "__main__":` line |

---

### bridge/ — 9 files (copy entire folder as-is)

| File | What it does |
|---|---|
| `bridge/__init__.py` | Makes bridge/ a Python package (empty file, required) |
| `bridge/main.py` | FastAPI app — registers routers, sets up CORS, serves the built React app in production |
| `bridge/requirements.txt` | Run `pip install -r bridge/requirements.txt` to install FastAPI, uvicorn, psutil, pynvml |
| `bridge/routers/__init__.py` | Makes routers/ a Python package (empty file, required) |
| `bridge/routers/system.py` | API endpoints: `GET /api/system/stats`, `GET /api/system/check`, `PUT /api/system/poll` |
| `bridge/routers/schema.py` | API endpoints: `GET /api/schema/all`, `/tables`, `/views`, `/table/{name}`, `/view/{name}` |
| `bridge/services/__init__.py` | Makes services/ a Python package (empty file, required) |
| `bridge/services/hardware.py` | Background thread that polls CPU/RAM every 2s, VRAM via pynvml with nvidia-smi fallback |
| `bridge/services/job_queue.py` | Job state machine — Phase 1 skeleton (stores jobs in history.db), Phase 2 adds execution |

---

### web/ — 7 config files (copy as-is, sit in web/ root)

| File | What it does |
|---|---|
| `web/index.html` | HTML entry point — loads the React app |
| `web/package.json` | npm dependencies: React, Vite, Tailwind, Zustand, Recharts, D3, Monaco, etc. |
| `web/vite.config.ts` | Vite config — proxies `/api/*` to `localhost:8000`, builds output to `bridge/static/` |
| `web/tailwind.config.ts` | Tailwind config — registers DM Sans + JetBrains Mono, custom color palette |
| `web/tsconfig.json` | TypeScript config — enables `@/` path alias for `src/` |
| `web/tsconfig.node.json` | TypeScript config for Vite/Tailwind config files themselves |
| `web/postcss.config.js` | PostCSS — runs Tailwind and Autoprefixer during build |

---

### web/src/ — 30 source files

#### Entry points (2 files)

| File | What it does |
|---|---|
| `web/src/main.tsx` | React app entry — mounts `<App />` into `#root`, imports global CSS |
| `web/src/App.tsx` | React Router setup — 8 routes mapping URLs to page components |

#### Global styles (1 file)

| File | What it does |
|---|---|
| `web/src/index.css` | Design system — CSS custom properties (colors, spacing), Tailwind imports, utility classes (`.card`, `.badge`, `.nav-item`, animations) |

#### API layer — `web/src/api/` (3 files)

| File | What it does |
|---|---|
| `api/client.ts` | Base fetch wrapper — handles JSON, throws typed `ApiError` on non-2xx responses |
| `api/system.ts` | Typed functions for `/api/system/*` endpoints |
| `api/schema.ts` | Typed functions for `/api/schema/*` endpoints |

#### Type definitions — `web/src/types/` (3 files)

| File | What it does |
|---|---|
| `types/system.ts` | TypeScript interfaces: `HardwareStats`, `GpuStats`, `OllamaStatus`, `DbStatus`, `SystemCheckResult` |
| `types/schema.ts` | TypeScript interfaces: `TableSchema`, `ColumnDef`, `IndexDef`, `ViewDefinition`, `SchemaAll` |
| `types/index.ts` | Shared types: `JobType`, `JobStatus`, `JobSummary`, `RunRecord`, `HistoryStats`, `ClientSummary` |

#### Zustand stores — `web/src/store/` (2 files)

| File | What it does |
|---|---|
| `store/systemStore.ts` | Global hardware stats state — `stats`, `lastUpdated`, `isInference` flag for poll rate switching |
| `store/clientStore.ts` | Active client state — `activeClient` name, `clients` list |

#### Hooks — `web/src/hooks/` (2 files)

| File | What it does |
|---|---|
| `hooks/useInterval.ts` | `setInterval` wrapper with React cleanup — pass `null` to pause |
| `hooks/useSystemStats.ts` | Polls `/api/system/stats` every 2s (idle) or 500ms (during inference), writes to systemStore |

#### Layout components — `web/src/components/layout/` (3 files)

| File | What it does |
|---|---|
| `components/layout/Sidebar.tsx` | Left nav — logo, client switcher dropdown, 8 nav links with active state, schema tree (tables/views from API), system status dots |
| `components/layout/TopBar.tsx` | Top bar — page title, optional action slot, last-refreshed timestamp |
| `components/layout/PageShell.tsx` | Main content wrapper — consistent padding, flex column, gap between sections |

#### Dashboard components — `web/src/components/dashboard/` (4 files)

| File | What it does |
|---|---|
| `components/dashboard/HardwareGauges.tsx` | Three donut gauges (CPU, RAM, VRAM) using Recharts RadialBarChart — VRAM pulses red above 90% |
| `components/dashboard/SystemStatusRow.tsx` | Row of status pills showing DB / Ollama / Git / snapshot health |
| `components/dashboard/ActiveJobCard.tsx` | 9-step pipeline progress track with live log output — Phase 1 shows "no active job", Phase 2 wires to jobStore |
| `components/dashboard/RecentRunsPanel.tsx` | Last 5 runs table with improvement badges — Phase 1 uses mock data, Phase 3 wires to history API |

#### Shared components — `web/src/components/shared/` (3 files)

| File | What it does |
|---|---|
| `components/shared/StatusBadge.tsx` | Pill badge in success/warning/danger/info/neutral variants |
| `components/shared/LoadingSpinner.tsx` | Spinning ring in sm/md/lg sizes |
| `components/shared/EmptyState.tsx` | Centered empty state with icon, title, description, optional action button |

#### Pages — `web/src/pages/` (8 files)

| File | Phase | What it does |
|---|---|---|
| `pages/Dashboard.tsx` | 1 — FULL | Live hardware gauges + active job + recent runs. Starts hardware stats polling on mount |
| `pages/Optimizer.tsx` | 2 — stub | Shows "Phase 2" empty state until replaced |
| `pages/History.tsx` | 3 — stub | Shows "Phase 3" empty state until replaced |
| `pages/DeploymentGate.tsx` | 4 — stub | Shows "Phase 4" empty state until replaced |
| `pages/ModelManager.tsx` | 5 — stub | Shows "Phase 5" empty state until replaced |
| `pages/ClientManager.tsx` | 5 — stub | Shows "Phase 5" empty state until replaced |
| `pages/PlanVisualizer.tsx` | 6 — stub | Shows "Phase 6" empty state until replaced |
| `pages/Settings.tsx` | 7 — stub | Shows "Phase 7" empty state until replaced |

---

## Reference Files — Keep Separately, Don't Copy Into Project

These 4 files are documentation only. They don't affect the running app. Keep them somewhere easy to find so you can paste them into new chats.

| File | Purpose |
|---|---|
| `v4-architecture.md` | Full architecture decisions, API contract, component map, D3 spec, design system reference |
| `v4-phase-plan.md` | All 8 phases — scope, layouts, API endpoints, implementation notes per phase |
| `v4-phase2-handoff.md` | Everything a new chat needs to start Phase 2 without re-explaining anything |
| `sql_agent_dashboard_mockup.html` | Standalone HTML mockup — open in browser to review the approved design |

---

## Setup Commands (In Order)

```bash
# 1. From your sql-agent/ project root:
pip install -r bridge/requirements.txt

# 2. Install frontend dependencies:
cd web
npm install
cd ..

# 3. Start everything:
python agent.py serve
# Opens http://localhost:5173
```

---

## Folder Count Summary

```
bridge/         9 files   (Python backend)
web/            7 files   (config, sits in web/ root)
web/src/       30 files   (React source)
──────────────────────────
Total:         46 files   + serve_command_for_agent_py.py (paste into agent.py)
               48 files delivered across the phase
```

*Phase 1 file placement guide — 2026-03-21*
