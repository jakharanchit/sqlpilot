# ============================================================
# tools/planner.py
# Tool 6: analyze_execution_plan
#
# HOW TO GET A .sqlplan FILE FROM SSMS:
#   1. Run your slow query in SSMS
#   2. Click "Include Actual Execution Plan" (Ctrl+M)
#   3. After query runs, click the "Execution Plan" tab
#   4. Right-click the plan → "Save Execution Plan As..."
#   5. Save as .sqlplan
#   6. Run: python agent.py plan path/to/file.sqlplan
# ============================================================

import xml.etree.ElementTree as ET
from pathlib import Path

import requests
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from config import OLLAMA_BASE_URL, MODELS

console = Console()


# ============================================================
# XML PARSING — extract key operators before sending to AI
# ============================================================

# SQL Server execution plan XML namespaces
NS = {
    "sql": "http://schemas.microsoft.com/sqlserver/2004/07/showplan"
}


def _parse_execution_plan(xml_path: str) -> dict:
    """
    Parses a .sqlplan XML file and extracts the most important
    performance-relevant operators WITHOUT sending everything to AI.

    This pre-processing step:
    - Finds expensive operators (Table Scan, Index Scan, Key Lookup)
    - Ranks operators by cost percentage
    - Extracts warnings (missing indexes, implicit conversions)
    - Summarizes before AI analysis (keeps prompts focused)

    Returns a dict with structured plan data.
    """
    path = Path(xml_path)
    if not path.exists():
        return {"error": f"File not found: {xml_path}"}
    if path.suffix.lower() != ".sqlplan":
        return {"error": f"Expected a .sqlplan file, got: {path.suffix}"}

    console.print(f"[cyan]→ Parsing execution plan:[/cyan] {path.name}")

    try:
        tree = ET.parse(xml_path)
        root = tree.getroot()
    except ET.ParseError as e:
        return {"error": f"Invalid XML in plan file: {e}"}

    operators      = []
    warnings       = []
    missing_indexes = []

    # Walk every element in the plan tree
    for elem in root.iter():
        tag = elem.tag.split("}")[-1]  # strip namespace prefix

        # --- Collect RelOps (the actual operators) ---
        if tag == "RelOp":
            op_name     = elem.get("PhysicalOp", elem.get("LogicalOp", "Unknown"))
            cost        = float(elem.get("EstimatedTotalSubtreeCost", 0))
            est_rows    = float(elem.get("EstimateRows", 0))
            est_rebinds = float(elem.get("EstimateRebinds", 0))

            operators.append({
                "operator":    op_name,
                "cost":        cost,
                "est_rows":    est_rows,
                "est_rebinds": est_rebinds,
            })

        # --- Collect Warnings ---
        if tag == "Warnings":
            for child in elem:
                child_tag = child.tag.split("}")[-1]
                if child_tag == "PlanAffectingConvert":
                    warnings.append({
                        "type":    "ImplicitConversion",
                        "detail":  f"Column: {child.get('Column', '?')} — "
                                   f"ConvertIssue: {child.get('ConvertIssue', '?')} — "
                                   f"Expression: {child.get('Expression', '?')}",
                    })
                elif child_tag == "NoJoinPredicate":
                    warnings.append({"type": "NoJoinPredicate", "detail": "Missing JOIN predicate — cross join risk"})

        # --- Collect Missing Index Hints ---
        if tag == "MissingIndex":
            impact = elem.get("Impact", "?")
            cols   = []
            for col_group in elem.findall(".//sql:ColumnGroup", NS):
                usage   = col_group.get("Usage", "")
                col_names = [c.get("Name", "") for c in col_group.findall("sql:Column", NS)]
                cols.append(f"{usage}: {', '.join(col_names)}")
            missing_indexes.append({
                "impact":  impact,
                "columns": cols,
            })

    # Sort operators by cost descending, take top 10
    operators.sort(key=lambda x: x["cost"], reverse=True)
    max_cost = operators[0]["cost"] if operators else 1

    # Add cost percentage to each operator
    for op in operators:
        op["cost_pct"] = round((op["cost"] / max_cost) * 100, 1) if max_cost > 0 else 0

    top_operators = operators[:10]

    # Flag expensive operator types
    expensive_types = {
        "Table Scan":        "HIGH — no index being used, reading entire table",
        "Index Scan":        "MEDIUM — reading entire index, filter may not be sargable",
        "Key Lookup":        "HIGH — index found row but fetched extra columns from heap",
        "Hash Match":        "MEDIUM — large data set join, consider index on join columns",
        "Sort":              "MEDIUM — result set being sorted in memory, index could eliminate",
        "Nested Loops":      "LOW/HIGH — depends on row count, watch for high est_rebinds",
        "Parallelism":       "INFO — query went parallel, may indicate large data scan",
        "Clustered Index Scan": "MEDIUM — scanning clustered index, similar to Table Scan",
    }

    flagged = []
    for op in top_operators:
        if op["operator"] in expensive_types:
            flagged.append({
                **op,
                "flag": expensive_types[op["operator"]]
            })

    console.print(f"[green]✓[/green] Plan parsed — "
                  f"{len(operators)} operators, "
                  f"{len(flagged)} flagged, "
                  f"{len(warnings)} warnings, "
                  f"{len(missing_indexes)} missing index hints")

    return {
        "source_file":      path.name,
        "total_operators":  len(operators),
        "top_operators":    top_operators,
        "flagged_operators": flagged,
        "warnings":         warnings,
        "missing_indexes":  missing_indexes,
        "raw_xml_snippet":  _get_xml_snippet(xml_path),  # first 4000 chars for AI
    }


def _get_xml_snippet(xml_path: str, max_chars: int = 4000) -> str:
    """Read the first N characters of the plan XML for AI context."""
    with open(xml_path, "r", encoding="utf-8", errors="ignore") as f:
        return f.read(max_chars)


# ============================================================
# AI ANALYSIS — DeepSeek-R1 interprets the parsed plan
# ============================================================

def analyze_execution_plan(plan_path: str, query: str = "") -> dict:
    """
    Full execution plan analysis pipeline.

    Step 1: Parse the XML — extract operators, warnings, missing indexes
    Step 2: Display structured summary in terminal
    Step 3: Send to DeepSeek-R1 for plain-English diagnosis + fix suggestions

    Args:
        plan_path: path to your .sqlplan file
        query:     optional — the original query (improves AI analysis)

    Returns:
        dict with parsed data and AI diagnosis

    Usage:
        result = analyze_execution_plan("plans/slow_query.sqlplan")
        result = analyze_execution_plan("plans/slow.sqlplan", query="SELECT ...")
    """
    console.print(Panel.fit(
        "[bold cyan]Execution Plan Analyzer[/bold cyan]",
        border_style="cyan"
    ))

    # Step 1 — Parse XML
    parsed = _parse_execution_plan(plan_path)
    if "error" in parsed:
        console.print(f"[red]✗ {parsed['error']}[/red]")
        return parsed

    # Step 2 — Print structured summary
    _print_plan_summary(parsed)

    # Step 3 — AI analysis
    console.print("\n[bold]AI Analysis[/bold] — DeepSeek-R1 interpreting plan...")

    try:
        response = requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=5)
        models   = [m["name"] for m in response.json().get("models", [])]
        if MODELS["reasoner"] not in models:
            console.print(f"[yellow]⚠ {MODELS['reasoner']} not available — skipping AI analysis[/yellow]")
            console.print("[dim]Pull it with: ollama pull deepseek-r1:14b[/dim]")
            return parsed
    except Exception:
        console.print("[yellow]⚠ Ollama not reachable — returning parsed data only[/yellow]")
        return parsed

    # Build a focused prompt from the parsed data
    flagged_text = "\n".join([
        f"- {op['operator']} (cost: {op['cost_pct']}%) — {op['flag']}"
        for op in parsed["flagged_operators"]
    ]) or "None flagged"

    warnings_text = "\n".join([
        f"- {w['type']}: {w['detail']}"
        for w in parsed["warnings"]
    ]) or "None"

    missing_text = "\n".join([
        f"- Impact {mi['impact']}%: {'; '.join(mi['columns'])}"
        for mi in parsed["missing_indexes"]
    ]) or "None"

    query_section = f"\nORIGINAL QUERY:\n{query}" if query else ""

    ai_prompt = f"""Analyze this SQL Server execution plan and provide specific optimization recommendations.

FLAGGED EXPENSIVE OPERATORS:
{flagged_text}

WARNINGS:
{warnings_text}

SQL SERVER MISSING INDEX HINTS:
{missing_text}

TOP OPERATORS BY COST:
{chr(10).join([f"- {op['operator']}: {op['cost_pct']}% of total cost ({op['est_rows']:.0f} estimated rows)" for op in parsed['top_operators'][:5]])}

XML SNIPPET (first portion of plan):
{parsed['raw_xml_snippet']}
{query_section}

Provide:
1. Root cause — what is the #1 performance problem and why
2. Specific fixes — exact changes to make (index names, query changes)
3. CREATE INDEX scripts for any missing indexes (```sql blocks)
4. Priority order — which fix will have the biggest impact first
5. Expected improvement — rough estimate if indexes are added"""

    with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), transient=True) as p:
        p.add_task("Analyzing plan with AI...", total=None)
        ai_analysis = _ask_ollama_plan(ai_prompt)

    console.print("\n[bold green]━━━ AI DIAGNOSIS ━━━[/bold green]")
    console.print(ai_analysis)

    parsed["ai_analysis"] = ai_analysis
    return parsed


def _ask_ollama_plan(prompt: str) -> str:
    """Calls DeepSeek-R1 specifically for plan analysis."""
    system = """You are a SQL Server execution plan expert.
You interpret execution plan operators and translate them into 
specific, actionable fixes. Always provide CREATE INDEX scripts
when indexes are the solution. Be direct and precise."""

    payload = {
        "model":  MODELS["reasoner"],
        "prompt": prompt,
        "system": system,
        "stream": False,
    }
    try:
        r = requests.post(f"{OLLAMA_BASE_URL}/api/generate", json=payload, timeout=300)
        r.raise_for_status()
        return r.json().get("response", "").strip()
    except Exception as e:
        return f"AI analysis failed: {e}"


# ============================================================
# TERMINAL OUTPUT
# ============================================================

def _print_plan_summary(parsed: dict):
    """Print a clean structured table of the execution plan findings."""

    # Flagged operators table
    if parsed["flagged_operators"]:
        table = Table(title="⚠  Flagged Operators", show_header=True, header_style="bold red")
        table.add_column("Operator",  style="red")
        table.add_column("Cost %",    justify="right")
        table.add_column("Est. Rows", justify="right")
        table.add_column("Issue",     style="yellow")

        for op in parsed["flagged_operators"]:
            table.add_row(
                op["operator"],
                f"{op['cost_pct']}%",
                f"{op['est_rows']:,.0f}",
                op["flag"],
            )
        console.print(table)
    else:
        console.print("[green]✓ No severely expensive operators detected[/green]")

    # Warnings
    if parsed["warnings"]:
        console.print("\n[bold red]Warnings:[/bold red]")
        for w in parsed["warnings"]:
            console.print(f"  [red]•[/red] {w['type']}: {w['detail']}")

    # Missing index hints from SQL Server itself
    if parsed["missing_indexes"]:
        console.print("\n[bold yellow]SQL Server Missing Index Hints:[/bold yellow]")
        for mi in parsed["missing_indexes"]:
            console.print(f"  [yellow]•[/yellow] Impact: {mi['impact']}%")
            for col in mi["columns"]:
                console.print(f"    {col}")
