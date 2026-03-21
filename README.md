# SQL Optimization Agent Toolkit

A fully offline, local AI-powered CLI agent for SQL Server optimization.
Runs entirely on your machine via Ollama — no data leaves your system.

---

## Features

- **AI-Powered Query Optimization** — auto-detects tables, fetches schemas & execution plans, and rewrites queries via local LLMs
- **View Refactoring** — analyzes view definitions and rewrites them for better read performance
- **Execution Plan Analysis** — parses `.sqlplan` files from SSMS and diagnoses bottlenecks
- **Workload-Aware Index Design** — analyzes a folder of `.sql` files and generates optimal index scripts
- **Full Pipeline** — single command runs: optimize → benchmark → migrate → report → deploy
- **Before/After Benchmarking** — times original vs. optimized queries across configurable runs
- **Migration Tracking** — auto-generates numbered migration scripts with apply/rollback SQL
- **Run History & Trends** — SQLite-backed history with filtering, regressions, trend analysis, and run comparison
- **Deployment Packaging** — generates `deploy.sql`, `rollback.sql`, walkthrough docs, and client reports
- **Shadow DB Sandbox** — restores a `.bak` to a shadow database, applies migrations, benchmarks, and runs regression checks before deploying
- **Schema Watcher** — daily schema snapshots with diff alerting; auto-schedulable via Windows Task Scheduler
- **Git Integration** — auto-commits after every optimization with typed commit messages
- **Terminal UI (TUI)** — OpenCode-style four-panel interface (schema tree, live output, recent runs, query input)
- **Structured Logging** — rotating daily log files with level filtering and statistics
- **Config Validation** — `check` command verifies DB, Ollama, permissions, directories, and registry health
- **Test Suite** — pytest tests for core modules (schema, pipeline, migrator, reporter, history, watcher, sandbox, error handler)

---

## Quick Start

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. Edit `config.py`
Fill in your SQL Server connection details, Ollama model names, and (optionally) sandbox `.bak` path.

### 3. Run health check
```bash
python agent.py check
```
Verifies config, DB connectivity, permissions, Ollama, directories, migration registry, and schema snapshot age.

### 4. Run your first optimization
```bash
python agent.py full-run --query "SELECT * FROM your_view WHERE your_filter = 1"
```

---

## All Commands

### Setup & Health
| Command | Description |
|---|---|
| `python agent.py check` | Run all configuration and connectivity checks |
| `python agent.py test-connection` | Test DB connection |
| `python agent.py git-init` | Initialize Git in the project |

### Database Inspection
| Command | Description |
|---|---|
| `python agent.py list-objects` | List all tables and views |
| `python agent.py schema <TABLE>` | Show columns and indexes for a table |
| `python agent.py show-view <VIEW>` | Show the SQL definition of a view |

### AI Optimization
| Command | Description |
|---|---|
| `python agent.py analyze "SQL"` | Optimize a SQL query (auto-detects tables) |
| `python agent.py optimize-file path/to/query.sql` | Optimize a `.sql` file |
| `python agent.py optimize-view <VIEW>` | Refactor a view for performance |
| `python agent.py plan path/to/plan.sqlplan` | Analyze an SSMS execution plan |
| `python agent.py workload queries/` | Design indexes for a folder of `.sql` files |

### Full Pipeline
| Command | Description |
|---|---|
| `python agent.py full-run --query "SQL"` | Optimize → benchmark → migrate → report → deploy |
| `python agent.py full-run --folder queries/` | Batch process a folder of `.sql` files |
| `python agent.py full-run --query "SQL" --safe` | Same as above but sandbox-tests migrations first |

### Benchmarking
| Command | Description |
|---|---|
| `python agent.py benchmark --before "SQL" --after "SQL"` | Compare before vs after query timing |
| `python agent.py baseline "SQL"` | Time a single query to establish a baseline |
| `python agent.py benchmark-files original.sql optimized.sql` | Compare two `.sql` files |

### Migrations & Deployment
| Command | Description |
|---|---|
| `python agent.py migrations` | List all migration files and their status |
| `python agent.py mark-applied <N>` | Mark a migration as applied |
| `python agent.py mark-rolled-back <N>` | Mark a migration as rolled back |
| `python agent.py deploy` | Generate a full client deployment package |

### Sandbox (Shadow DB)
| Command | Description |
|---|---|
| `python agent.py sandbox-test --all-pending` | Test pending migrations against a shadow DB |
| `python agent.py sandbox-create` | Manually create a shadow database |
| `python agent.py sandbox-run "SQL"` | Run a query against the shadow DB |
| `python agent.py sandbox-list` | List all shadow databases |
| `python agent.py sandbox-destroy` | Destroy a shadow database |

### Schema Watcher
| Command | Description |
|---|---|
| `python agent.py watch` | Diff today's schema against yesterday's |
| `python agent.py watch-report` | Show most recent schema watch report |
| `python agent.py watch-schedule` | Generate Windows Task Scheduler files for daily 07:00 runs |
| `python agent.py snapshot` | Take a manual schema snapshot |

### History & Analysis
| Command | Description |
|---|---|
| `python agent.py history` | View run history (filterable by query, table) |
| `python agent.py history --top` | Show top improvements |
| `python agent.py history --regressions` | Show runs that got worse |
| `python agent.py history --stats` | Overall statistics |
| `python agent.py trend --table <TABLE>` | Show improvement trend over time |
| `python agent.py compare <ID_A> <ID_B>` | Compare two runs side by side |

### Run Logs, Reports & Git
| Command | Description |
|---|---|
| `python agent.py runs` | List recent run logs |
| `python agent.py report` | Show the last optimization run report |
| `python agent.py logs` | View the agent log file |
| `python agent.py logs --stats` | Show log statistics |
| `python agent.py git-log` | Show recent Git commits |

### Terminal UI
| Command | Description |
|---|---|
| `python agent.py ui` | Launch the four-panel TUI |

---

## Project Structure

```
SQL Toolkit/
├── agent.py               ← CLI entry point (Typer) — run everything from here
├── config.py              ← your settings (DB, Ollama models, sandbox, paths)
├── requirements.txt       ← Python dependencies
├── pytest.ini             ← test configuration
├── query_history.db       ← SQLite history database
│
├── tools/                 ← core modules
│   ├── schema.py          ← DB inspection: tables, views, columns, indexes
│   ├── optimizer.py       ← AI query optimization & index script generation
│   ├── planner.py         ← execution plan analysis
│   ├── benchmarker.py     ← before/after query timing
│   ├── pipeline.py        ← full-run orchestration (single + batch)
│   ├── migrator.py        ← migration file management and status tracking
│   ├── reporter.py        ← report & deployment package generation
│   ├── sandbox.py         ← shadow DB create/destroy/benchmark/regression
│   ├── watcher.py         ← schema snapshot, diff, and scheduling
│   ├── history.py         ← run history, trends, comparisons, stats
│   ├── git_manager.py     ← Git init, auto-commit, log
│   ├── executor.py        ← safe SQL execution helpers
│   ├── logger.py          ← run log file management
│   ├── app_logger.py      ← structured application logging
│   ├── config_validator.py← health check logic
│   └── error_handler.py   ← centralized error handling
│
├── tui/
│   └── app.py             ← Textual-based terminal UI
│
├── tests/                 ← pytest test suite
│   ├── conftest.py
│   ├── test_schema.py
│   ├── test_pipeline.py
│   ├── test_migrator.py
│   ├── test_reporter.py
│   ├── test_history.py
│   ├── test_watcher.py
│   ├── test_sandbox.py
│   └── test_error_handler.py
│
├── migrations/            ← numbered SQL change files (auto-generated)
├── projects/              ← per-client workspaces
├── reports/               ← saved optimization reports
├── deployments/           ← client deployment packages
├── plans/                 ← saved execution plans
├── runs/                  ← run log files (.md)
├── logs/                  ← daily application log files
└── snapshots/             ← schema snapshots for the watcher
```

---

## Models Required (via Ollama)

```bash
ollama pull qwen2.5-coder:14b    # query writing and optimization
ollama pull deepseek-r1:14b      # execution plan reasoning
```

---

## Configuration

All settings live in `config.py`:

| Setting | Purpose |
|---|---|
| `ACTIVE_CLIENT` | Switch between client workspaces |
| `DB_CONFIG` | SQL Server connection (Windows or SQL auth) |
| `OLLAMA_BASE_URL` | Ollama API endpoint |
| `MODELS` | Which Ollama models to use for optimization and reasoning |
| `SANDBOX_BAK_PATH` | `.bak` file for shadow DB testing |
| `BENCHMARK_RUNS` | Number of timing runs (default 10) |
| `AUTO_COMMIT_GIT` | Auto-commit after optimizations |
| `SAVE_REPORTS` | Auto-save reports to `/reports` |

---

## Build Phases

- [x] Phase 1 — Project structure, Git, config, DB connection
- [x] Phase 2 — Core optimizer (schema + query + view + workload tools)
- [x] Phase 2.1 — Migration tracking and Git automation
- [x] Phase 2.5 — Run history, trends, comparisons, statistics
- [x] Phase 2.6 — Schema watcher with diff alerting and scheduling
- [x] Phase 2.7 — Terminal UI (Textual four-panel interface)
- [x] Phase 3 — Execution plan analyzer + benchmarker
- [x] Phase 3.1 — Config validator, structured logging, error handling
- [x] Phase 3.2 — Full pipeline orchestration (single + batch)
- [x] Phase 3.3 — Shadow DB sandbox testing
- [x] Phase 4 — Deployment package generator
- [x] Phase 5 — Report generator
- [ ] Phase 7 — Query interceptor (LabVIEW logging)
- [ ] Phase 8 — Schema watcher CI integration
- [ ] Phase 9 — Multi-client system
