# ============================================================
# tools/optimizer.py
# Tool 3: optimize_query      — rewrites a slow query
# Tool 4: optimize_view       — refactors a slow view
# Tool 5: generate_index_scripts — produces CREATE INDEX T-SQL
#
# HOW THE TWO-MODEL CHAIN WORKS:
#   Step 1 → DeepSeek-R1 (reasoner) diagnoses WHY it's slow
#   Step 2 → Qwen2.5-Coder (writer) produces the actual fix
#
# This gives better results than one model doing both tasks.
# ============================================================

import json
import re
from datetime import datetime

import requests
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

from config import OLLAMA_BASE_URL, MODELS

console = Console()


# ============================================================
# LOW-LEVEL: talk to Ollama
# ============================================================

def _ask_ollama(model: str, prompt: str, system: str = "") -> str:
    """
    Send a prompt to a local Ollama model and return the response text.
    Uses the /api/generate endpoint (no streaming, waits for full response).

    Args:
        model:  model name e.g. "qwen2.5-coder:14b"
        prompt: the user message
        system: optional system prompt to set behaviour

    Returns:
        The model's response as a plain string.
    """
    payload = {
        "model":  model,
        "prompt": prompt,
        "stream": False,
    }
    if system:
        payload["system"] = system

    try:
        response = requests.post(
            f"{OLLAMA_BASE_URL}/api/generate",
            json=payload,
            timeout=300,   # 5 min timeout — large models can be slow first run
        )
        response.raise_for_status()
        return response.json().get("response", "").strip()

    except requests.exceptions.ConnectionError:
        console.print("[red]✗ Cannot reach Ollama. Is it running?[/red]")
        console.print("  Start it with: [cyan]ollama serve[/cyan]")
        return ""

    except requests.exceptions.Timeout:
        console.print("[red]✗ Ollama timed out. Model may still be loading — try again.[/red]")
        return ""

    except Exception as e:
        console.print(f"[red]✗ Ollama error: {e}[/red]")
        return ""


def _check_ollama_ready(model: str) -> bool:
    """Check if a model is available in Ollama before calling it."""
    try:
        response = requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=5)
        models = [m["name"] for m in response.json().get("models", [])]
        if model not in models:
            console.print(f"[yellow]⚠ Model '{model}' not found in Ollama.[/yellow]")
            console.print(f"  Pull it with: [cyan]ollama pull {model}[/cyan]")
            return False
        return True
    except Exception:
        console.print("[red]✗ Cannot reach Ollama at localhost:11434[/red]")
        console.print("  Start it with: [cyan]ollama serve[/cyan]")
        return False


# ============================================================
# HELPERS: format context for prompts
# ============================================================

def _format_schema_for_prompt(schema_list: list) -> str:
    """
    Converts a list of schema dicts (from get_schema) into
    a clean text block the AI can read easily.
    """
    lines = []
    for s in schema_list:
        lines.append(f"\n-- Table: {s['table_name']} (~{s['estimated_row_count']} rows)")
        lines.append("-- Columns:")
        for col in s["columns"]:
            pk   = " [PRIMARY KEY]" if col["primary_key"] == "YES" else ""
            null = " NULL" if col["nullable"] == "YES" else " NOT NULL"
            lines.append(f"--   {col['name']}  {col['type']}{pk}{null}")

        if s["indexes"]:
            lines.append("-- Existing Indexes:")
            for idx in s["indexes"]:
                incl = f" INCLUDE({idx['included_columns']})" if idx["included_columns"] else ""
                lines.append(f"--   {idx['name']}: ({idx['key_columns']}){incl}")
        else:
            lines.append("-- Existing Indexes: NONE")

    return "\n".join(lines)


def _extract_sql_blocks(text: str) -> list:
    """
    Pulls out all SQL code blocks from a markdown-style response.
    Returns a list of SQL strings.
    """
    # Match ```sql ... ``` blocks
    pattern = r"```(?:sql|SQL)?\s*(.*?)```"
    blocks  = re.findall(pattern, text, re.DOTALL)
    # Also catch bare SQL if no code blocks found
    if not blocks and "SELECT" in text.upper():
        blocks = [text]
    return [b.strip() for b in blocks]


# ============================================================
# TOOL 3: optimize_query
# ============================================================

def optimize_query(query: str, schema_list: list, context: str = "") -> dict:
    """
    Full two-model optimization pipeline for a SQL query.

    Step 1: DeepSeek-R1 diagnoses what's wrong and why.
    Step 2: Qwen2.5-Coder rewrites the query based on that diagnosis.

    Args:
        query:       the SQL query to optimize
        schema_list: list of schema dicts from get_schema()
        context:     optional extra context e.g. "called from LabVIEW every 5 seconds"

    Returns:
        dict with keys:
            original_query    — unchanged input
            diagnosis         — DeepSeek-R1's explanation of the problem
            optimized_query   — Qwen's rewritten query
            changes_explained — list of what changed and why
            index_scripts     — ready-to-run CREATE INDEX statements
            timestamp         — when this ran
    """
    console.print(Panel.fit(
        "[bold cyan]Query Optimizer[/bold cyan] — Two-Model Chain",
        border_style="cyan"
    ))

    schema_text = _format_schema_for_prompt(schema_list)
    labview_ctx = context or "This query is used by a LabVIEW dashboard application for data display."

    # ----------------------------------------------------------
    # STEP 1 — DeepSeek-R1: diagnose the problem
    # ----------------------------------------------------------
    console.print("\n[bold]Step 1/2[/bold] — DeepSeek-R1 diagnosing root cause...")

    if not _check_ollama_ready(MODELS["reasoner"]):
        return {"error": f"Model {MODELS['reasoner']} not available"}

    diagnosis_system = """You are a senior SQL Server DBA specializing in query performance.
Your job is to diagnose performance problems in SQL queries.
Be specific and technical. Focus on root causes, not symptoms.
Always consider: sargability, implicit conversions, index usage, 
lock contention, and cardinality estimation."""

    diagnosis_prompt = f"""Analyze this SQL Server query for performance problems.

CONTEXT:
{labview_ctx}

SCHEMA:
{schema_text}

QUERY TO ANALYZE:
{query}

Diagnose ALL performance issues. For each issue:
1. Name the problem (e.g. "Non-sargable predicate", "Implicit type conversion")
2. Explain exactly why it causes slow performance
3. State what the fix is (conceptually, not code yet)

Also flag if WITH (NOLOCK) is appropriate given the read-only dashboard context."""

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        transient=True,
    ) as progress:
        progress.add_task("Reasoning through the query...", total=None)
        diagnosis = _ask_ollama(MODELS["reasoner"], diagnosis_prompt, diagnosis_system)

    if not diagnosis:
        return {"error": "DeepSeek-R1 returned no response"}

    console.print("[green]✓[/green] Diagnosis complete")

    # ----------------------------------------------------------
    # STEP 2 — Qwen2.5-Coder: write the fix
    # ----------------------------------------------------------
    console.print("\n[bold]Step 2/2[/bold] — Qwen2.5-Coder writing optimized query...")

    if not _check_ollama_ready(MODELS["optimizer"]):
        return {"error": f"Model {MODELS['optimizer']} not available"}

    rewrite_system = """You are a SQL Server query optimization expert.
You write clean, high-performance T-SQL.
Always respond with:
1. The optimized query in a ```sql code block
2. A bullet list of exactly what you changed and why
3. CREATE INDEX scripts in separate ```sql blocks if indexes are needed

Be precise. Never explain what you didn't change."""

    rewrite_prompt = f"""Rewrite this SQL Server query for maximum performance.

CONTEXT:
{labview_ctx}

SCHEMA:
{schema_text}

ORIGINAL QUERY:
{query}

DIAGNOSIS FROM ANALYSIS:
{diagnosis}

Produce:
1. The fully optimized query (```sql block)
2. Bullet list: what changed and why (be specific, reference column names)
3. Any CREATE INDEX statements needed (separate ```sql blocks)
   - Include INCLUDE columns to make covering indexes
   - Add a comment on each index explaining what query pattern it targets"""

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        transient=True,
    ) as progress:
        progress.add_task("Writing optimized query...", total=None)
        rewrite_response = _ask_ollama(MODELS["optimizer"], rewrite_prompt, rewrite_system)

    if not rewrite_response:
        return {"error": "Qwen2.5-Coder returned no response"}

    console.print("[green]✓[/green] Optimization complete\n")

    # Extract SQL blocks from response
    sql_blocks      = _extract_sql_blocks(rewrite_response)
    optimized_query = sql_blocks[0] if sql_blocks else ""
    index_scripts   = sql_blocks[1:] if len(sql_blocks) > 1 else []

    # Build result
    result = {
        "original_query":    query,
        "diagnosis":         diagnosis,
        "optimized_query":   optimized_query,
        "full_response":     rewrite_response,
        "index_scripts":     index_scripts,
        "timestamp":         datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }

    # Print summary to terminal
    _print_optimization_summary(result)

    return result


# ============================================================
# TOOL 4: optimize_view
# ============================================================

def optimize_view(view_def: dict, schema_list: list) -> dict:
    """
    Optimizes a view definition using the two-model chain.

    Args:
        view_def:    dict from get_view_definition()
        schema_list: list of schema dicts for tables the view references

    Returns:
        dict with diagnosis, optimized view DDL, and index suggestions
    """
    console.print(Panel.fit(
        f"[bold cyan]View Optimizer[/bold cyan] — {view_def['view_name']}",
        border_style="cyan"
    ))

    schema_text = _format_schema_for_prompt(schema_list)

    # ----------------------------------------------------------
    # STEP 1 — DeepSeek-R1: diagnose the view
    # ----------------------------------------------------------
    console.print("\n[bold]Step 1/2[/bold] — DeepSeek-R1 analyzing view structure...")

    diagnosis_prompt = f"""Analyze this SQL Server view for performance problems.

CONTEXT:
This view is queried by a LabVIEW dashboard. Users apply filters 
(WHERE clauses) on top of the view. It needs to return data fast.

SCHEMA OF REFERENCED TABLES:
{schema_text}

VIEW DEFINITION:
{view_def['definition']}

Identify:
1. Hidden performance traps (e.g. SELECT *, subqueries, functions on columns)
2. Whether this could be an Indexed View (materialized)
3. Non-sargable patterns that prevent filter pushdown
4. Any joins that could be simplified"""

    with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), transient=True) as p:
        p.add_task("Analyzing view...", total=None)
        diagnosis = _ask_ollama(MODELS["reasoner"], diagnosis_prompt)

    console.print("[green]✓[/green] View analysis complete")

    # ----------------------------------------------------------
    # STEP 2 — Qwen2.5-Coder: rewrite the view
    # ----------------------------------------------------------
    console.print("\n[bold]Step 2/2[/bold] — Qwen2.5-Coder rewriting view...")

    rewrite_prompt = f"""Rewrite this SQL Server view for maximum read performance.

SCHEMA:
{schema_text}

ORIGINAL VIEW:
{view_def['definition']}

DIAGNOSIS:
{diagnosis}

Produce:
1. The optimized CREATE OR ALTER VIEW statement (```sql block)
2. Bullet list of what changed and why
3. Any supporting indexes needed (separate ```sql blocks)
4. If Indexed View is recommended, explain the WITH SCHEMABINDING requirement"""

    with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), transient=True) as p:
        p.add_task("Rewriting view...", total=None)
        rewrite_response = _ask_ollama(MODELS["optimizer"], rewrite_prompt)

    console.print("[green]✓[/green] View rewrite complete\n")

    sql_blocks    = _extract_sql_blocks(rewrite_response)
    optimized_ddl = sql_blocks[0] if sql_blocks else ""
    index_scripts = sql_blocks[1:] if len(sql_blocks) > 1 else []

    result = {
        "view_name":       view_def["view_name"],
        "original_ddl":    view_def["definition"],
        "diagnosis":       diagnosis,
        "optimized_ddl":   optimized_ddl,
        "full_response":   rewrite_response,
        "index_scripts":   index_scripts,
        "timestamp":       datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }

    _print_view_summary(result)
    return result


# ============================================================
# TOOL 5: generate_index_scripts
# ============================================================

def generate_index_scripts(queries: list, schema_list: list) -> dict:
    """
    Analyzes a WORKLOAD of multiple queries together and designs
    the minimum set of indexes that benefit all of them.

    This is smarter than per-query index suggestions — it avoids
    creating redundant indexes and considers write overhead.

    Args:
        queries:     list of query strings (your most common queries)
        schema_list: schema context for relevant tables

    Returns:
        dict with index scripts and reasoning
    """
    console.print(Panel.fit(
        f"[bold cyan]Workload Index Designer[/bold cyan] — {len(queries)} queries",
        border_style="cyan"
    ))

    schema_text    = _format_schema_for_prompt(schema_list)
    queries_text   = "\n\n".join([f"-- Query {i+1}\n{q}" for i, q in enumerate(queries)])

    prompt = f"""Design the optimal set of SQL Server indexes for this query workload.

SCHEMA:
{schema_text}

QUERIES (design indexes that benefit ALL of these together):
{queries_text}

Rules:
1. Minimize the number of indexes — fewer is better for write performance
2. Use composite keys where one index can serve multiple queries
3. Include INCLUDE columns to create covering indexes and avoid Key Lookups
4. For each index, note which queries it helps and the expected benefit

Produce:
- CREATE INDEX statements (```sql blocks)
- For each index: a comment explaining which query patterns it serves
- A warning if any index will significantly hurt INSERT/UPDATE performance
- A summary table: Index Name | Queries Helped | Write Impact"""

    if not _check_ollama_ready(MODELS["optimizer"]):
        return {"error": f"Model {MODELS['optimizer']} not available"}

    with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), transient=True) as p:
        p.add_task("Designing workload indexes...", total=None)
        response = _ask_ollama(MODELS["optimizer"], prompt)

    sql_blocks = _extract_sql_blocks(response)

    console.print("[green]✓[/green] Index design complete\n")
    console.print(response)

    return {
        "queries":       queries,
        "index_scripts": sql_blocks,
        "full_response": response,
        "timestamp":     datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }


# ============================================================
# TERMINAL OUTPUT HELPERS
# ============================================================

def _print_optimization_summary(result: dict):
    """Print a clean before/after summary to terminal."""

    console.print("[bold green]━━━ DIAGNOSIS ━━━[/bold green]")
    console.print(result["diagnosis"])

    console.print("\n[bold green]━━━ OPTIMIZED QUERY ━━━[/bold green]")
    if result["optimized_query"]:
        console.print(f"[cyan]{result['optimized_query']}[/cyan]")
    else:
        console.print(result["full_response"])

    if result["index_scripts"]:
        console.print("\n[bold green]━━━ INDEX SCRIPTS (ready to run in SSMS) ━━━[/bold green]")
        for script in result["index_scripts"]:
            console.print(f"[yellow]{script}[/yellow]")

    console.print(f"\n[dim]Completed: {result['timestamp']}[/dim]")
    console.print("[dim]Tip: Run 'python agent.py save-last' to save this as a migration file[/dim]")


def _print_view_summary(result: dict):
    """Print view optimization results to terminal."""

    console.print(f"[bold green]━━━ VIEW: {result['view_name']} — DIAGNOSIS ━━━[/bold green]")
    console.print(result["diagnosis"])

    console.print(f"\n[bold green]━━━ OPTIMIZED VIEW DDL ━━━[/bold green]")
    if result["optimized_ddl"]:
        console.print(f"[cyan]{result['optimized_ddl']}[/cyan]")
    else:
        console.print(result["full_response"])

    if result["index_scripts"]:
        console.print("\n[bold green]━━━ SUPPORTING INDEXES ━━━[/bold green]")
        for script in result["index_scripts"]:
            console.print(f"[yellow]{script}[/yellow]")
