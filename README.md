# SQL Optimization Agent Toolkit

A fully offline, local AI-powered CLI agent for SQL Server optimization.
Runs entirely on your machine via Ollama — no data leaves your system.

## Quick Start

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. Edit config.py
Fill in your SQL Server connection details.

### 3. Test connection
```bash
python -c "from tools.schema import test_connection; test_connection()"
```

### 4. Run your first optimization
```bash
python agent.py --analyze "SELECT * FROM your_view WHERE your_filter = 1"
```

---

## Common Commands

```bash
# Optimize a query
python agent.py --analyze "your query here"

# Optimize a .sql file
python agent.py --file path/to/query.sql

# Analyze an execution plan
python agent.py --plan path/to/plan.sqlplan

# Refactor a view
python agent.py --view vw_your_view_name

# Generate client deployment package
python agent.py --deploy --client client_acme

# Add a new client
python agent.py --new-client "ClientName"

# Test DB connection
python agent.py --test-connection
```

---

## Project Structure

```
sql-agent/
├── agent.py           ← entry point — run everything from here
├── config.py          ← YOUR settings (DB connection, client name)
├── requirements.txt
├── tools/
│   ├── schema.py      ← get_schema, get_view_definition
│   ├── planner.py     ← analyze_execution_plan (Phase 3)
│   ├── optimizer.py   ← optimize_query, generate_index_scripts (Phase 2)
│   ├── benchmarker.py ← before/after timing (Phase 4)
│   └── reporter.py    ← generate reports (Phase 5)
├── migrations/        ← numbered SQL change files
├── projects/          ← per-client workspaces
├── reports/           ← generated optimization reports
└── deployments/       ← client deployment packages
```

---

## Models Required (install via Ollama)

```bash
ollama pull qwen2.5-coder:14b    # query writing and optimization
ollama pull deepseek-r1:14b      # execution plan reasoning
```

---

## Build Phases

- [x] Phase 1 — Project structure, Git, config, DB connection
- [ ] Phase 2 — Core optimizer (schema + query tools)
- [ ] Phase 3 — Execution plan analyzer
- [ ] Phase 4 — Benchmarker
- [ ] Phase 5 — Report generator
- [ ] Phase 6 — Deployment packager
- [ ] Phase 7 — Query interceptor (LabVIEW logging)
- [ ] Phase 8 — Schema watcher
- [ ] Phase 9 — Multi-client system
