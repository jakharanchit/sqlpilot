# ============================================================
# tools/optimizer.py
# Core optimization pipeline — query, view, and workload.
#
# PIPELINE (what happens when you run analyze):
#
#   Step 1  Extract tables referenced in query
#   Step 2  Pull schema (columns, indexes, row counts)
#   Step 3  Fetch execution plan XML from SQL Server
#   Step 4  Parse plan — flag expensive operators + warnings
#   Step 5  DeepSeek-R1 diagnoses root cause using schema + plan
#   Step 6  Qwen2.5-Coder rewrites the query based on diagnosis
#   Step 7  Extract optimized SQL + index scripts from response
#   Step 8  Save full run log to runs/
#   Step 9  Display results in terminal
#
# Each step prints a status message so you always know
# exactly what the agent is doing and why.
# ============================================================

import re
import time
from datetime import datetime

import requests
from rich.console import Console
from rich.panel import Panel
from rich.rule import Rule

from config import OLLAMA_BASE_URL, MODELS

console = Console()


# ============================================================
# STEP PRINTER
# ============================================================

def _step(n, total, msg):
    console.print(f"\n[bold cyan]Step {n}/{total}[/bold cyan] — {msg}")

def _ok(msg):
    console.print(f"  [green]✓[/green] {msg}")

def _warn(msg):
    console.print(f"  [yellow]⚠[/yellow]  {msg}")

def _fail(msg):
    console.print(f"  [red]✗[/red] {msg}")

def _info(msg):
    console.print(f"  [dim]{msg}[/dim]")


# ============================================================
# OLLAMA
# ============================================================

def _ask_ollama(model, prompt, system="", label=""):
    import json as _json
    payload = {"model": model, "prompt": prompt, "stream": True}
    if system:
        payload["system"] = system

    try:
        response = requests.post(
            f"{OLLAMA_BASE_URL}/api/generate",
            json=payload, stream=True, timeout=300,
        )
        response.raise_for_status()

        full_text   = ""
        token_count = 0
        console.print(f"  [dim]Streaming response[/dim]", end="")

        for line in response.iter_lines():
            if line:
                chunk = _json.loads(line)
                full_text  += chunk.get("response", "")
                token_count += 1
                if token_count % 50 == 0:
                    console.print(".", end="", highlight=False)
                if chunk.get("done"):
                    break

        console.print()
        return full_text.strip()

    except requests.exceptions.ConnectionError:
        _fail("Cannot reach Ollama. Start it with: ollama serve")
        return ""
    except requests.exceptions.Timeout:
        _fail("Ollama timed out — model may still be loading, try again")
        return ""
    except Exception as e:
        _fail(f"Ollama error: {e}")
        return ""


def _check_model(model):
    try:
        r      = requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=5)
        models = [m["name"] for m in r.json().get("models", [])]
        if model not in models:
            _warn(f"Model '{model}' not pulled yet")
            _info(f"Run: ollama pull {model}")
            return False
        return True
    except Exception:
        _fail("Cannot reach Ollama at localhost:11434")
        _info("Run: ollama serve")
        return False


# ============================================================
# HELPERS
# ============================================================

def _extract_sql_blocks(text):
    blocks = re.findall(r"```(?:sql|SQL)?\s*(.*?)```", text, re.DOTALL)
    if not blocks and re.search(r"\b(SELECT|CREATE|INSERT|UPDATE|ALTER)\b", text, re.I):
        blocks = [text]
    return [b.strip() for b in blocks if b.strip()]


def _format_schema(schema_list):
    lines = []
    for s in schema_list:
        lines.append(f"\n-- Table: {s['table_name']} (~{s.get('estimated_row_count','?')} rows)")
        lines.append("-- Columns:")
        for col in s["columns"]:
            pk   = " [PK]"  if col["primary_key"] == "YES" else ""
            null = " NULL"  if col["nullable"]    == "YES" else " NOT NULL"
            lines.append(f"--   {col['name']}  {col['type']}{pk}{null}")
        if s.get("indexes"):
            lines.append("-- Existing Indexes:")
            for idx in s["indexes"]:
                inc = f" INCLUDE({idx['included_columns']})" if idx.get("included_columns") else ""
                lines.append(f"--   {idx['name']} ({idx['type']}): ({idx['key_columns']}){inc}")
        else:
            lines.append("-- Existing Indexes: NONE")
    return "\n".join(lines)


# ============================================================
# MAIN PIPELINE: optimize_query
# ============================================================

def optimize_query(query, schema_list):
    """
    Full 9-step optimization pipeline for a SQL query.
    Fetches execution plan automatically. Saves run log.
    """
    TOTAL  = 9
    t0     = time.time()

    console.print()
    console.print(Panel(
        "[bold cyan]SQL Query Optimization Pipeline[/bold cyan]\n"
        "[dim]Schema analysis · Execution plan · Two-model AI chain · Auto-logged[/dim]",
        border_style="cyan", expand=False,
    ))

    result = {
        "original_query":    query,
        "schema_list":       schema_list,
        "plan":              {},
        "diagnosis":         "",
        "optimized_query":   "",
        "full_ai_response":  "",
        "index_scripts":     [],
        "timestamp":         datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "log_path":          "",
    }

    # ── Step 1 ──────────────────────────────────────────────
    _step(1, TOTAL, "Identifying tables and objects referenced in query")
    table_names = [s["table_name"] for s in schema_list]
    _ok(f"Found {len(table_names)} object(s): {', '.join(table_names)}")

    # ── Step 2 ──────────────────────────────────────────────
    _step(2, TOTAL, "Reviewing schema — columns, indexes, row counts")
    total_cols    = sum(len(s["columns"]) for s in schema_list)
    total_indexes = sum(len(s.get("indexes", [])) for s in schema_list)
    total_rows    = sum(
        s.get("estimated_row_count", 0) for s in schema_list
        if isinstance(s.get("estimated_row_count"), int)
    )
    _ok(f"{total_cols} columns · {total_indexes} existing indexes · ~{total_rows:,} total rows")
    if total_indexes == 0:
        _warn("No indexes found on any referenced table — likely the primary performance issue")
    for s in schema_list:
        rc  = s.get("estimated_row_count", "?")
        idx = len(s.get("indexes", []))
        _info(f"{s['table_name']}: ~{rc:,} rows · {idx} index(es)" if isinstance(rc, int) else f"{s['table_name']}: {idx} index(es)")

    # ── Step 3 ──────────────────────────────────────────────
    _step(3, TOTAL, "Fetching actual execution plan from SQL Server")
    _info("Running query with SET STATISTICS XML ON — captures real operator costs and row counts...")

    try:
        from tools.executor import fetch_execution_plan, format_plan_for_prompt
        plan = fetch_execution_plan(query, actual=True)
        if "error" in plan:
            _warn(f"Actual plan failed: {plan['error']}")
            _info("Trying estimated plan instead (query won't run, plan only)...")
            plan = fetch_execution_plan(query, actual=False)
            if "error" in plan:
                _warn("Could not capture any plan — analysis will rely on schema only")
                plan = {}
    except Exception as e:
        _warn(f"Plan capture error: {e}")
        plan = {}

    result["plan"] = plan

    # ── Step 4 ──────────────────────────────────────────────
    _step(4, TOTAL, "Parsing plan — scanning for expensive operators, warnings, missing index hints")

    if plan and "error" not in plan:
        flagged  = plan.get("flagged", [])
        warnings = plan.get("warnings", [])
        missing  = plan.get("missing_indexes", [])

        if flagged:
            console.print(f"  [red]  {len(flagged)} problematic operator(s) found:[/red]")
            for op in flagged:
                color = "red" if op["severity"] == "HIGH" else "yellow"
                console.print(f"  [{color}]  [{op['severity']}] {op['name']}[/{color}] — {op['reason']}")
        else:
            _ok("No severely expensive operators in plan")

        for w in warnings:
            if w["type"] == "ImplicitConversion":
                _warn(f"Implicit type conversion on column '{w['column']}' — this blocks index use")
            else:
                _warn(f"{w['type']}: {w['issue']}")

        for mi in missing:
            _info(f"SQL Server missing index hint — Impact {mi['impact']}%: {', '.join(mi['columns'])}")
    else:
        _info("No plan data available — continuing with schema-only analysis")

    # ── Step 5 ──────────────────────────────────────────────
    _step(5, TOTAL, "DeepSeek-R1 diagnosing root cause")
    _info(f"Model: {MODELS['reasoner']}")
    _info("Feeding schema + execution plan data into reasoning model...")

    diagnosis = ""
    if _check_model(MODELS["reasoner"]):
        schema_text = _format_schema(schema_list)
        plan_text   = format_plan_for_prompt(plan) if plan and "error" not in plan else "[No plan data available]"

        diag_sys = """You are a senior SQL Server DBA and performance specialist.
Diagnose query performance problems precisely.
Focus on: sargability, implicit conversions, missing indexes,
cardinality estimation errors, lock contention."""

        diag_prompt = f"""Diagnose ALL performance problems in this SQL Server query.

SCHEMA:
{schema_text}

EXECUTION PLAN:
{plan_text}

QUERY:
{query}

For each problem:
1. Name it precisely (e.g. "Non-sargable predicate on column X due to CAST")
2. Explain the performance impact
3. State the fix (conceptual — not code yet)

Order by performance impact, highest first."""

        diagnosis = _ask_ollama(MODELS["reasoner"], diag_prompt, diag_sys)

    result["diagnosis"] = diagnosis
    _ok(f"Diagnosis complete ({len(diagnosis.split())} words)") if diagnosis else _warn("No diagnosis produced")

    # ── Step 6 ──────────────────────────────────────────────
    _step(6, TOTAL, "Qwen2.5-Coder writing optimized query and index scripts")
    _info(f"Model: {MODELS['optimizer']}")
    _info("Using diagnosis + plan data to produce the most accurate rewrite...")

    full_response = ""
    if _check_model(MODELS["optimizer"]):
        schema_text = _format_schema(schema_list)
        plan_text   = format_plan_for_prompt(plan) if plan and "error" not in plan else "[No plan data]"

        rewrite_sys = """You are a SQL Server query optimization expert.
Write clean, high-performance T-SQL.
Always produce:
1. The optimized query in a ```sql block
2. Bullet list: what changed and exactly why (reference column names)
3. CREATE INDEX scripts in separate ```sql blocks with INCLUDE columns"""

        rewrite_prompt = f"""Rewrite this SQL Server query for maximum performance.

SCHEMA:
{schema_text}

EXECUTION PLAN:
{plan_text}

ORIGINAL QUERY:
{query}

DIAGNOSIS:
{diagnosis or "No diagnosis — rely on schema and plan data."}

Produce:
1. Fully optimized query (```sql block)
2. What changed and why — be specific, name exact columns
3. CREATE INDEX scripts (```sql blocks)
   — composite keys for actual filter/join columns
   — INCLUDE columns to eliminate Key Lookups
   — comment on each index: which pattern it targets"""

        full_response = _ask_ollama(MODELS["optimizer"], rewrite_prompt, rewrite_sys)

    result["full_ai_response"] = full_response

    # ── Step 7 ──────────────────────────────────────────────
    _step(7, TOTAL, "Extracting optimized SQL and CREATE INDEX scripts from response")

    sql_blocks      = _extract_sql_blocks(full_response)
    optimized_query = sql_blocks[0] if sql_blocks else ""
    index_scripts   = [
        b for b in sql_blocks[1:]
        if re.search(r"\bCREATE\s+(UNIQUE\s+)?INDEX\b", b, re.I)
    ]

    result["optimized_query"] = optimized_query
    result["index_scripts"]   = index_scripts

    _ok(f"Optimized query: {len(optimized_query.splitlines())} lines") if optimized_query else _warn("Could not extract clean optimized query — review full response in log")
    _ok(f"{len(index_scripts)} index script(s) extracted") if index_scripts else _info("No CREATE INDEX scripts in response")

    # ── Step 8 ──────────────────────────────────────────────
    _step(8, TOTAL, "Saving full run log to runs/")

    try:
        from tools.logger import log_optimization
        log_path = log_optimization(
            query            = query,
            schema_list      = schema_list,
            plan             = plan,
            diagnosis        = diagnosis,
            optimized_query  = optimized_query,
            full_ai_response = full_response,
            index_scripts    = index_scripts,
            run_type         = "query",
        )
        result["log_path"] = log_path
        name = log_path.split("runs/")[-1] if "runs/" in log_path else log_path
        _ok(f"Saved: runs/{name}")
    except Exception as e:
        _warn(f"Could not save log: {e}")

    # ── Step 9 ──────────────────────────────────────────────
    _step(9, TOTAL, "Done — displaying results")
    elapsed = round(time.time() - t0, 1)
    _print_results(result, elapsed)

    return result


# ============================================================
# VIEW PIPELINE
# ============================================================

def optimize_view(view_def, schema_list):
    """5-step view optimization pipeline."""
    TOTAL = 5
    console.print()
    console.print(Panel(
        f"[bold cyan]View Optimization Pipeline[/bold cyan] — {view_def['view_name']}\n"
        "[dim]Two-model chain · Auto-logged[/dim]",
        border_style="cyan", expand=False,
    ))

    result = {
        "view_name":        view_def["view_name"],
        "original_ddl":     view_def["definition"],
        "schema_list":      schema_list,
        "diagnosis":        "",
        "optimized_ddl":    "",
        "full_ai_response": "",
        "index_scripts":    [],
        "timestamp":        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "log_path":         "",
    }

    schema_text = _format_schema(schema_list)

    _step(1, TOTAL, f"Reviewing view: {view_def['view_name']}")
    ref = view_def.get("referenced_tables", [])
    _ok(f"References {len(ref)} table(s): {', '.join(ref)}")
    _info(f"View DDL: {view_def['definition'].count(chr(10))} lines")

    _step(2, TOTAL, "Reviewing schema of referenced tables")
    for s in schema_list:
        _info(f"{s['table_name']}: ~{s.get('estimated_row_count','?')} rows · {len(s.get('indexes',[]))} indexes")

    _step(3, TOTAL, "DeepSeek-R1 analyzing view structure and performance traps")
    _info(f"Model: {MODELS['reasoner']} — checking for hidden costs, sargability, and index opportunities...")

    diagnosis = ""
    if _check_model(MODELS["reasoner"]):
        diag_prompt = f"""Analyze this SQL Server VIEW for performance problems.

CONTEXT: View is queried with WHERE filters on top. Needs fast reads.

SCHEMA:
{schema_text}

VIEW:
{view_def['definition']}

Find: SELECT *, functions on columns, subqueries, non-sargable joins,
Indexed View candidates, unnecessary columns, hidden JOIN costs."""

        diagnosis = _ask_ollama(MODELS["reasoner"], diag_prompt)

    result["diagnosis"] = diagnosis
    _ok("Analysis complete") if diagnosis else _warn("No analysis produced")

    _step(4, TOTAL, "Qwen2.5-Coder rewriting view DDL")
    _info(f"Model: {MODELS['optimizer']} — writing optimized CREATE OR ALTER VIEW...")

    full_response = ""
    if _check_model(MODELS["optimizer"]):
        rewrite_prompt = f"""Rewrite this SQL Server view for maximum read performance.

SCHEMA:
{schema_text}

ORIGINAL VIEW:
{view_def['definition']}

DIAGNOSIS:
{diagnosis or "Rely on schema context."}

Produce:
1. CREATE OR ALTER VIEW statement (```sql block)
2. What changed and why
3. Supporting CREATE INDEX scripts (```sql blocks)
4. If Indexed View: explain WITH SCHEMABINDING requirement"""

        full_response = _ask_ollama(MODELS["optimizer"], rewrite_prompt)

    result["full_ai_response"] = full_response
    sql_blocks              = _extract_sql_blocks(full_response)
    result["optimized_ddl"] = sql_blocks[0] if sql_blocks else ""
    result["index_scripts"] = [b for b in sql_blocks[1:] if "INDEX" in b.upper()]

    _step(5, TOTAL, "Saving log and displaying results")

    try:
        from tools.logger import log_optimization
        log_path = log_optimization(
            query=view_def["definition"], schema_list=schema_list,
            plan={}, diagnosis=diagnosis,
            optimized_query=result["optimized_ddl"],
            full_ai_response=full_response,
            index_scripts=result["index_scripts"],
            run_type="view", label=view_def["view_name"],
        )
        result["log_path"] = log_path
        name = log_path.split("runs/")[-1] if "runs/" in log_path else log_path
        _ok(f"Saved: runs/{name}")
    except Exception as e:
        _warn(f"Could not save log: {e}")

    console.print()
    console.print(Rule(f"[bold cyan]VIEW DIAGNOSIS — {result['view_name']}[/bold cyan]"))
    console.print(result["diagnosis"] or "[dim]No diagnosis[/dim]")
    console.print()
    console.print(Rule("[bold cyan]OPTIMIZED VIEW DDL[/bold cyan]"))
    console.print(result["optimized_ddl"] or "[dim]No DDL extracted[/dim]")
    if result["index_scripts"]:
        console.print()
        console.print(Rule("[bold yellow]SUPPORTING INDEXES[/bold yellow]"))
        for s in result["index_scripts"]:
            console.print(f"[yellow]{s}[/yellow]")

    return result


# ============================================================
# WORKLOAD INDEX DESIGNER
# ============================================================

def generate_index_scripts(queries, schema_list):
    """Design minimal index set for a workload of multiple queries."""
    console.print()
    console.print(Panel(
        f"[bold cyan]Workload Index Designer[/bold cyan] — {len(queries)} queries\n"
        "[dim]Designing minimum index set across all queries[/dim]",
        border_style="cyan", expand=False,
    ))

    schema_text  = _format_schema(schema_list)
    queries_text = "\n\n".join([f"-- Query {i+1}\n{q}" for i, q in enumerate(queries)])

    _step(1, 2, "Reviewing all queries and existing indexes")
    for s in schema_list:
        _info(f"{s['table_name']}: {len(s.get('indexes',[]))} existing indexes")

    _step(2, 2, "Qwen2.5-Coder designing workload-optimal index set")
    _info("Analyzing all queries together to avoid redundant indexes...")

    if not _check_model(MODELS["optimizer"]):
        return {"error": f"Model {MODELS['optimizer']} not available"}

    prompt = f"""Design the optimal SQL Server index set for this query workload.

SCHEMA:
{schema_text}

ALL QUERIES:
{queries_text}

Rules:
1. Minimize index count — fewer = better write performance
2. Composite keys where one index serves multiple queries
3. INCLUDE columns to make covering indexes
4. Per index: note which queries it helps

Produce CREATE INDEX statements (```sql blocks) with comments.
Include write impact warnings. Add a summary table."""

    response   = _ask_ollama(MODELS["optimizer"], prompt)
    sql_blocks = _extract_sql_blocks(response)

    console.print()
    console.print(Rule("[bold cyan]Workload Index Recommendations[/bold cyan]"))
    console.print(response)

    return {
        "queries": queries, "index_scripts": sql_blocks,
        "full_response": response,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }


# ============================================================
# TERMINAL OUTPUT
# ============================================================

def _print_results(result, elapsed):
    console.print()
    console.print(Rule("[bold cyan]DIAGNOSIS (DeepSeek-R1)[/bold cyan]"))
    console.print(result["diagnosis"] or "[dim]No diagnosis produced[/dim]")

    console.print()
    console.print(Rule("[bold cyan]OPTIMIZED QUERY (Qwen2.5-Coder)[/bold cyan]"))
    if result["optimized_query"]:
        console.print(f"[green]{result['optimized_query']}[/green]")
    else:
        console.print("[dim]No clean query extracted — full response saved in run log[/dim]")
        if result["full_ai_response"]:
            console.print(result["full_ai_response"])

    if result["index_scripts"]:
        console.print()
        console.print(Rule("[bold yellow]INDEX SCRIPTS — paste into SSMS to apply[/bold yellow]"))
        for i, s in enumerate(result["index_scripts"], 1):
            console.print(f"\n[yellow]-- Index {i}[/yellow]")
            console.print(f"[yellow]{s}[/yellow]")

    console.print()
    console.print(Rule())
    console.print(f"[dim]Completed in {elapsed}s · Log: {result.get('log_path','not saved')}[/dim]")
    console.print("[dim]Next: [cyan]python agent.py benchmark --before '...' --after '...'[/cyan] to measure improvement[/dim]")
