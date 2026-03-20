# ============================================================
# tools/logger.py
# Saves a full record of every optimization run as a
# timestamped markdown file in the runs/ folder.
#
# WHY LOG EVERY RUN:
#   - Debugging: see exactly what AI diagnosed and why
#   - Reference: compare past runs if same query comes back
#   - Audit trail: know what was suggested and when
#   - Client proof: attach run logs to deployment packages
#
# FILE NAMING:
#   runs/2026_03_20_14_32_01_vw_dashboard_optimize.md
#   runs/2026_03_20_15_10_45_measurements_benchmark.md
# ============================================================

import re
from datetime import datetime
from pathlib import Path

from config import BASE_DIR

RUNS_DIR = Path(BASE_DIR) / "runs"


def _ensure_runs_dir():
    RUNS_DIR.mkdir(parents=True, exist_ok=True)


def _slug(text: str, max_len: int = 30) -> str:
    """Convert text to a safe filename slug."""
    text = re.sub(r"[^\w\s-]", "", text.lower())
    text = re.sub(r"[\s_-]+", "_", text).strip("_")
    return text[:max_len]


def _ts() -> str:
    return datetime.now().strftime("%Y_%m_%d_%H_%M_%S")


# ============================================================
# LOG: optimization run
# ============================================================

def log_optimization(
    query:            str,
    schema_list:      list,
    plan:             dict,
    diagnosis:        str,
    optimized_query:  str,
    full_ai_response: str,
    index_scripts:    list,
    run_type:         str = "query",   # "query" | "view" | "workload"
    label:            str = "",
) -> str:
    """
    Saves a full optimization run log to runs/.

    Args:
        query:            the original SQL
        schema_list:      list of schema dicts used as context
        plan:             execution plan dict from executor.py
        diagnosis:        DeepSeek-R1's diagnosis text
        optimized_query:  Qwen's rewritten query
        full_ai_response: complete raw AI response
        index_scripts:    list of CREATE INDEX strings
        run_type:         "query", "view", or "workload"
        label:            optional short name for the run

    Returns:
        path to the saved file
    """
    _ensure_runs_dir()

    slug     = _slug(label or query[:40])
    filename = f"{_ts()}_{slug}_{run_type}.md"
    filepath = RUNS_DIR / filename

    lines = [
        f"# Run Log — {run_type.title()} Optimization",
        f"**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"**Label:** {label or '(none)'}",
        f"**Run type:** {run_type}",
        "",
        "---",
        "",
        "## Original Query",
        "```sql",
        query.strip(),
        "```",
        "",
        "## Schema Context",
    ]

    for s in schema_list:
        lines.append(f"### Table: `{s['table_name']}`")
        lines.append(f"Estimated rows: ~{s.get('estimated_row_count', '?')}")
        lines.append("")
        lines.append("| Column | Type | PK | Nullable |")
        lines.append("|--------|------|----|---------|")
        for col in s["columns"]:
            pk   = "✓" if col["primary_key"] == "YES" else ""
            null = "NULL" if col["nullable"] == "YES" else "NOT NULL"
            lines.append(f"| {col['name']} | {col['type']} | {pk} | {null} |")
        lines.append("")

        if s.get("indexes"):
            lines.append("**Existing indexes:**")
            for idx in s["indexes"]:
                incl = f" INCLUDE({idx['included_columns']})" if idx.get("included_columns") else ""
                lines.append(f"- `{idx['name']}` ({idx['type']}) — keys: `{idx['key_columns']}`{incl}")
        else:
            lines.append("**Existing indexes:** None")
        lines.append("")

    lines += [
        "---",
        "",
        "## Execution Plan",
    ]

    if plan and "error" not in plan:
        lines += [
            f"**Plan type:** {plan.get('plan_type', '?')}",
            f"**Execution time:** {plan.get('elapsed_ms', '?')}ms",
            f"**Rows returned:** {plan.get('row_count', '?')}",
            "",
        ]
        if plan.get("flagged"):
            lines.append("**Flagged operators:**")
            for op in plan["flagged"]:
                act = f" | actual rows: {op['act_rows']}" if op.get("act_rows") is not None else ""
                lines.append(
                    f"- [{op['severity']}] `{op['name']}` "
                    f"(est: {op['est_rows']}{act}) — {op['reason']}"
                )
            lines.append("")

        if plan.get("warnings"):
            lines.append("**Warnings:**")
            for w in plan["warnings"]:
                if w["type"] == "ImplicitConversion":
                    lines.append(f"- ⚠ Implicit conversion: column `{w['column']}` — {w['issue']}")
                else:
                    lines.append(f"- ⚠ {w['type']}: {w['issue']}")
            lines.append("")

        if plan.get("missing_indexes"):
            lines.append("**Missing index hints from SQL Server:**")
            for mi in plan["missing_indexes"]:
                lines.append(f"- Impact {mi['impact']}%: {', '.join(mi['columns'])}")
            lines.append("")
    elif plan and "error" in plan:
        lines.append(f"**Plan capture failed:** {plan['error']}")
        lines.append("")
    else:
        lines.append("*No execution plan captured for this run.*")
        lines.append("")

    lines += [
        "---",
        "",
        "## AI Diagnosis (DeepSeek-R1)",
        "",
        diagnosis.strip() if diagnosis else "*No diagnosis recorded.*",
        "",
        "---",
        "",
        "## Optimized Query (Qwen2.5-Coder)",
        "```sql",
        optimized_query.strip() if optimized_query else "-- No optimized query produced",
        "```",
        "",
    ]

    if index_scripts:
        lines += ["## Index Scripts", ""]
        for i, script in enumerate(index_scripts, 1):
            lines.append(f"### Index {i}")
            lines.append("```sql")
            lines.append(script.strip())
            lines.append("```")
            lines.append("")

    lines += [
        "---",
        "",
        "## Full AI Response (raw)",
        "<details>",
        "<summary>Click to expand</summary>",
        "",
        full_ai_response.strip() if full_ai_response else "*No response recorded.*",
        "",
        "</details>",
        "",
        "---",
        f"*Generated by SQL Optimization Agent · {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*",
    ]

    filepath.write_text("\n".join(lines), encoding="utf-8")
    return str(filepath)


# ============================================================
# LOG: benchmark run
# ============================================================

def log_benchmark(result: dict) -> str:
    """
    Saves a benchmark comparison run to runs/.

    Args:
        result: dict from benchmarker.benchmark_query()

    Returns:
        path to the saved file
    """
    _ensure_runs_dir()

    label    = result.get("label", "benchmark")
    slug     = _slug(label)
    filename = f"{_ts()}_{slug}_benchmark.md"
    filepath = RUNS_DIR / filename

    b   = result.get("before", {})
    a   = result.get("after",  {})
    pct = result.get("improvement_pct", 0)
    spd = result.get("speedup", 0)

    lines = [
        f"# Benchmark Log — {label}",
        f"**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"**Runs each:** {result.get('runs', '?')}",
        "",
        "---",
        "",
        "## Results",
        "",
        "| Metric | Before | After | Δ |",
        "|--------|--------|-------|---|",
        f"| **Average** | {b.get('avg_ms','?')}ms | {a.get('avg_ms','?')}ms | **{pct}% faster** |",
        f"| Median      | {b.get('p50_ms','?')}ms | {a.get('p50_ms','?')}ms | — |",
        f"| Fastest     | {b.get('min_ms','?')}ms | {a.get('min_ms','?')}ms | — |",
        f"| Slowest     | {b.get('max_ms','?')}ms | {a.get('max_ms','?')}ms | — |",
        f"| Std Dev     | {b.get('std_ms','?')}ms | {a.get('std_ms','?')}ms | — |",
        f"| Rows        | {b.get('row_count','?')} | {a.get('row_count','?')} | "
        f"{'⚠ MISMATCH' if result.get('row_mismatch') else '✓ Match'} |",
        "",
        f"**Speedup: {spd}x faster**",
        "",
    ]

    if result.get("row_mismatch"):
        lines += [
            "> ⚠ **ROW COUNT MISMATCH** — queries return different data.",
            "> Do not apply this optimization without investigating.",
            "",
        ]

    lines += [
        "## All Run Times",
        "",
        "**Before (ms):** " + ", ".join(str(t) for t in b.get("times", [])),
        "",
        "**After (ms):** "  + ", ".join(str(t) for t in a.get("times", [])),
        "",
        "---",
        "",
        "## Original Query",
        "```sql",
        result.get("original_query", ""),
        "```",
        "",
        "## Optimized Query",
        "```sql",
        result.get("optimized_query", ""),
        "```",
        "",
        "---",
        f"*Generated by SQL Optimization Agent · {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*",
    ]

    filepath.write_text("\n".join(lines), encoding="utf-8")
    return str(filepath)


# ============================================================
# LOG: execution plan only (standalone plan capture)
# ============================================================

def log_plan(query: str, plan: dict, label: str = "") -> str:
    """
    Saves just an execution plan analysis to runs/.
    Used when running plan analysis without a full optimization.
    """
    _ensure_runs_dir()

    slug     = _slug(label or query[:40])
    filename = f"{_ts()}_{slug}_plan.md"
    filepath = RUNS_DIR / filename

    lines = [
        f"# Execution Plan Log — {label or 'Query'}",
        f"**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        "## Query",
        "```sql",
        query.strip(),
        "```",
        "",
        "## Plan Results",
        f"**Type:** {plan.get('plan_type', '?')}",
        f"**Execution time:** {plan.get('elapsed_ms', '?')}ms",
        f"**Rows returned:** {plan.get('row_count', '?')}",
        "",
    ]

    if plan.get("flagged"):
        lines.append("## Flagged Operators")
        for op in plan["flagged"]:
            act = f" | actual: {op['act_rows']}" if op.get("act_rows") is not None else ""
            lines.append(f"- [{op['severity']}] `{op['name']}` (est: {op['est_rows']}{act}) — {op['reason']}")
        lines.append("")

    if plan.get("warnings"):
        lines.append("## Warnings")
        for w in plan["warnings"]:
            lines.append(f"- {w['type']}: {w.get('issue', w.get('column', ''))}")
        lines.append("")

    if plan.get("missing_indexes"):
        lines.append("## Missing Index Hints")
        for mi in plan["missing_indexes"]:
            lines.append(f"- Impact {mi['impact']}%: {', '.join(mi['columns'])}")
        lines.append("")

    lines.append(f"*Generated by SQL Optimization Agent · {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*")

    filepath.write_text("\n".join(lines), encoding="utf-8")
    return str(filepath)


# ============================================================
# LIST RUNS
# ============================================================

def list_runs(run_type: str = None, limit: int = 10) -> list:
    """
    Returns a list of recent run log files.

    Args:
        run_type: filter by "optimize", "benchmark", "plan" — or None for all
        limit:    max number of results

    Returns:
        list of dicts with filename, path, size, date
    """
    _ensure_runs_dir()

    pattern = f"*_{run_type}.md" if run_type else "*.md"
    files   = sorted(RUNS_DIR.glob(pattern), reverse=True)[:limit]

    return [
        {
            "filename": f.name,
            "path":     str(f),
            "size_kb":  round(f.stat().st_size / 1024, 1),
            "date":     datetime.fromtimestamp(f.stat().st_mtime).strftime("%Y-%m-%d %H:%M"),
        }
        for f in files
    ]
