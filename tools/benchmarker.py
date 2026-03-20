# ============================================================
# tools/benchmarker.py
# Measures real execution time of SQL queries against your
# actual SQL Server database.
#
# HOW IT WORKS:
#   1. Runs the original query N times, records each time
#   2. Runs the optimized query N times, records each time
#   3. Calculates avg, min, max, std deviation for both
#   4. Produces a comparison with % improvement
#   5. Saves a benchmark result you can include in reports
#
# WHY N RUNS (default 10):
#   First run is often slower due to cold cache.
#   Averaging 10 runs gives a fair, reproducible number.
#   SQL Server's plan cache means runs 2-10 are "warm" — 
#   this reflects real LabVIEW repeated polling behaviour.
# ============================================================

import statistics
import time
from datetime import datetime
from pathlib import Path

import pyodbc
from rich.console import Console
from rich.panel import Panel
from rich.progress import (
    BarColumn,
    MofNCompleteColumn,
    Progress,
    TaskProgressColumn,
    TextColumn,
    TimeElapsedColumn,
)
from rich.table import Table

from config import DB_CONFIG, BENCHMARK_RUNS, REPORTS_DIR

console = Console()


# ============================================================
# LOW-LEVEL: run a query and time it
# ============================================================

def _get_connection():
    """Return a pyodbc connection using config.py settings."""
    cfg = DB_CONFIG
    if cfg.get("trusted_connection", "no").lower() == "yes":
        conn_str = (
            f"DRIVER={{{cfg['driver']}}};"
            f"SERVER={cfg['server']};"
            f"DATABASE={cfg['database']};"
            f"Trusted_Connection=yes;"
        )
    else:
        conn_str = (
            f"DRIVER={{{cfg['driver']}}};"
            f"SERVER={cfg['server']};"
            f"DATABASE={cfg['database']};"
            f"UID={cfg['username']};"
            f"PWD={cfg['password']};"
        )
    return pyodbc.connect(conn_str)


def _run_once(cursor, query: str) -> tuple:
    """
    Execute a query once and return (elapsed_ms, row_count).
    Uses time.perf_counter for high-resolution timing.
    Fetches all results to simulate real application behaviour.
    """
    start    = time.perf_counter()
    cursor.execute(query)
    rows     = cursor.fetchall()
    elapsed  = (time.perf_counter() - start) * 1000  # convert to ms
    return round(elapsed, 2), len(rows)


def _run_query_n_times(query: str, n: int, label: str) -> dict:
    """
    Run a query N times and collect timing statistics.

    Returns dict with:
        times      — list of all individual run times (ms)
        avg_ms     — average across all runs
        min_ms     — fastest run
        max_ms     — slowest run
        std_ms     — standard deviation (consistency indicator)
        p50_ms     — median
        row_count  — number of rows returned
        error      — error message if query failed
    """
    conn   = _get_connection()
    cursor = conn.cursor()
    times  = []
    row_count = 0

    try:
        with Progress(
            TextColumn(f"  [cyan]{label}[/cyan]"),
            BarColumn(),
            MofNCompleteColumn(),
            TaskProgressColumn(),
            TimeElapsedColumn(),
            transient=True,
        ) as progress:
            task = progress.add_task("Running...", total=n)

            for i in range(n):
                try:
                    elapsed, rows = _run_once(cursor, query)
                    times.append(elapsed)
                    if i == 0:
                        row_count = rows
                    progress.advance(task)
                except Exception as e:
                    conn.close()
                    return {"error": f"Query failed on run {i+1}: {e}"}

    finally:
        conn.close()

    if not times:
        return {"error": "No timing data collected"}

    return {
        "times":     times,
        "avg_ms":    round(statistics.mean(times), 2),
        "min_ms":    round(min(times), 2),
        "max_ms":    round(max(times), 2),
        "std_ms":    round(statistics.stdev(times) if len(times) > 1 else 0, 2),
        "p50_ms":    round(statistics.median(times), 2),
        "row_count": row_count,
        "run_count": n,
    }


# ============================================================
# MAIN TOOL: benchmark_query
# ============================================================

def benchmark_query(
    original_query: str,
    optimized_query: str,
    label: str = "Query",
    runs: int = None,
) -> dict:
    """
    Benchmark original vs optimized query and return comparison.

    Args:
        original_query:  the slow query (before)
        optimized_query: the rewritten query (after)
        label:           name for the benchmark (used in reports)
        runs:            number of runs each (default from config.py)

    Returns:
        dict with full stats + improvement metrics

    Usage:
        result = benchmark_query(
            original_query  = "SELECT * FROM vw_dashboard WHERE machine_id=1",
            optimized_query = "SELECT id, value FROM measurements WITH(NOLOCK) WHERE machine_id=1",
            label           = "vw_dashboard machine filter",
        )
    """
    n = runs or BENCHMARK_RUNS

    console.print(Panel.fit(
        f"[bold cyan]Benchmarker[/bold cyan] — {label}\n"
        f"[dim]Running each query {n} times against your SQL Server[/dim]",
        border_style="cyan"
    ))

    # --- Run original ---
    console.print(f"\n[bold]Before[/bold] — original query ({n} runs):")
    before = _run_query_n_times(original_query, n, "Before")
    if "error" in before:
        console.print(f"[red]✗ Original query failed: {before['error']}[/red]")
        console.print("[yellow]Tip: Make sure the original query runs in SSMS first[/yellow]")
        return {"error": before["error"]}
    console.print(f"  [green]✓[/green] avg {before['avg_ms']}ms  |  {before['row_count']} rows returned")

    # --- Run optimized ---
    console.print(f"\n[bold]After[/bold] — optimized query ({n} runs):")
    after = _run_query_n_times(optimized_query, n, "After")
    if "error" in after:
        console.print(f"[red]✗ Optimized query failed: {after['error']}[/red]")
        console.print("[yellow]Tip: Test the optimized query in SSMS before benchmarking[/yellow]")
        return {"error": after["error"]}
    console.print(f"  [green]✓[/green] avg {after['avg_ms']}ms  |  {after['row_count']} rows returned")

    # --- Calculate improvement ---
    improvement_pct = round(
        ((before["avg_ms"] - after["avg_ms"]) / before["avg_ms"]) * 100, 1
    ) if before["avg_ms"] > 0 else 0

    speedup = round(before["avg_ms"] / after["avg_ms"], 1) if after["avg_ms"] > 0 else 0

    # Row count mismatch warning
    row_mismatch = before["row_count"] != after["row_count"]

    result = {
        "label":            label,
        "before":           before,
        "after":            after,
        "improvement_pct":  improvement_pct,
        "speedup":          speedup,
        "row_mismatch":     row_mismatch,
        "original_query":   original_query,
        "optimized_query":  optimized_query,
        "timestamp":        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "runs":             n,
    }

    _print_benchmark_results(result)
    return result


def benchmark_single(query: str, label: str = "Query", runs: int = None) -> dict:
    """
    Benchmark a single query (no before/after comparison).
    Useful for establishing a baseline before optimization.

    Args:
        query: SQL query to time
        label: name for reporting
        runs:  number of runs (default from config.py)

    Usage:
        baseline = benchmark_single("SELECT * FROM vw_dashboard", "vw_dashboard baseline")
    """
    n = runs or BENCHMARK_RUNS

    console.print(Panel.fit(
        f"[bold cyan]Baseline Benchmark[/bold cyan] — {label}\n"
        f"[dim]Running {n} times to establish baseline[/dim]",
        border_style="cyan"
    ))

    result = _run_query_n_times(query, n, label)
    if "error" in result:
        console.print(f"[red]✗ {result['error']}[/red]")
        return result

    console.print(f"\n  [green]✓[/green] {label}")
    console.print(f"  avg: {result['avg_ms']}ms  |  "
                  f"min: {result['min_ms']}ms  |  "
                  f"max: {result['max_ms']}ms  |  "
                  f"rows: {result['row_count']}")

    return {"label": label, "stats": result, "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}


# ============================================================
# MULTI-QUERY BENCHMARK — test a whole workload
# ============================================================

def benchmark_workload(query_pairs: list, runs: int = None) -> list:
    """
    Benchmark multiple before/after query pairs at once.
    Useful for proving improvements across your whole LabVIEW workload.

    Args:
        query_pairs: list of dicts, each with:
            { "label": "name", "before": "original SQL", "after": "optimized SQL" }
        runs: number of runs per query

    Returns:
        list of benchmark result dicts

    Usage:
        results = benchmark_workload([
            {"label": "dashboard filter",  "before": "...", "after": "..."},
            {"label": "sensor summary",    "before": "...", "after": "..."},
        ])
    """
    n       = runs or BENCHMARK_RUNS
    results = []

    console.print(Panel.fit(
        f"[bold cyan]Workload Benchmarker[/bold cyan]\n"
        f"[dim]{len(query_pairs)} query pairs · {n} runs each[/dim]",
        border_style="cyan"
    ))

    for i, pair in enumerate(query_pairs, 1):
        console.print(f"\n[bold]Query {i}/{len(query_pairs)}:[/bold] {pair['label']}")
        result = benchmark_query(
            original_query  = pair["before"],
            optimized_query = pair["after"],
            label           = pair["label"],
            runs            = n,
        )
        results.append(result)

    _print_workload_summary(results)
    return results


# ============================================================
# SAVE BENCHMARK TO FILE
# ============================================================

def save_benchmark(result: dict, filename: str = None) -> str:
    """
    Saves a benchmark result as a markdown file in the reports/ folder.
    This file is used by the report generator in Phase 5.

    Returns the path to the saved file.
    """
    reports_dir = Path(REPORTS_DIR)
    reports_dir.mkdir(parents=True, exist_ok=True)

    ts       = datetime.now().strftime("%Y%m%d_%H%M%S")
    label    = result.get("label", "benchmark").replace(" ", "_").lower()
    filename = filename or f"benchmark_{label}_{ts}.md"
    filepath = reports_dir / filename

    lines = [
        f"# Benchmark: {result.get('label', 'Query')}",
        f"**Date:** {result.get('timestamp', '')}",
        f"**Runs:** {result.get('runs', BENCHMARK_RUNS)} per query\n",
    ]

    if "before" in result and "after" in result:
        b = result["before"]
        a = result["after"]
        lines += [
            "## Results",
            "",
            "| Metric | Before | After | Improvement |",
            "|--------|--------|-------|-------------|",
            f"| Average | {b['avg_ms']}ms | {a['avg_ms']}ms | **{result['improvement_pct']}% faster** |",
            f"| Fastest | {b['min_ms']}ms | {a['min_ms']}ms | — |",
            f"| Slowest | {b['max_ms']}ms | {a['max_ms']}ms | — |",
            f"| Median  | {b['p50_ms']}ms | {a['p50_ms']}ms | — |",
            f"| Std Dev | {b['std_ms']}ms | {a['std_ms']}ms | — |",
            f"| Rows returned | {b['row_count']} | {a['row_count']} | {'⚠ MISMATCH' if result.get('row_mismatch') else '✓ Match'} |",
            "",
            f"**Speedup: {result['speedup']}x faster**",
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
        ]

    filepath.write_text("\n".join(lines), encoding="utf-8")
    console.print(f"\n[green]✓ Benchmark saved:[/green] {filepath}")
    return str(filepath)


# ============================================================
# TERMINAL OUTPUT HELPERS
# ============================================================

def _print_benchmark_results(result: dict):
    """Print a clean before/after comparison table."""
    b   = result["before"]
    a   = result["after"]
    pct = result["improvement_pct"]
    spd = result["speedup"]

    console.print()

    # Main comparison table
    table = Table(
        title=f"Benchmark Results — {result['label']}",
        show_header=True,
        header_style="bold white",
        border_style="cyan",
    )
    table.add_column("Metric",       style="dim",   width=14)
    table.add_column("Before",       justify="right", style="red")
    table.add_column("After",        justify="right", style="green")
    table.add_column("Difference",   justify="right", style="bold")

    def diff(b_val, a_val, unit="ms"):
        d = round(b_val - a_val, 2)
        return f"[green]-{d}{unit}[/green]" if d > 0 else f"[red]+{abs(d)}{unit}[/red]"

    table.add_row("Average",  f"{b['avg_ms']}ms", f"{a['avg_ms']}ms",  diff(b["avg_ms"],  a["avg_ms"]))
    table.add_row("Median",   f"{b['p50_ms']}ms", f"{a['p50_ms']}ms",  diff(b["p50_ms"],  a["p50_ms"]))
    table.add_row("Fastest",  f"{b['min_ms']}ms", f"{a['min_ms']}ms",  diff(b["min_ms"],  a["min_ms"]))
    table.add_row("Slowest",  f"{b['max_ms']}ms", f"{a['max_ms']}ms",  diff(b["max_ms"],  a["max_ms"]))
    table.add_row("Std Dev",  f"{b['std_ms']}ms", f"{a['std_ms']}ms",  "")
    table.add_row("Rows",     str(b["row_count"]), str(a["row_count"]),
                  "[red]⚠ MISMATCH[/red]" if result["row_mismatch"] else "[green]✓ Match[/green]")

    console.print(table)

    # Headline result
    if pct > 0:
        console.print(
            f"\n  [bold green]✓ {pct}% faster[/bold green]  "
            f"[dim]({spd}x speedup · avg {b['avg_ms']}ms → {a['avg_ms']}ms)[/dim]"
        )
    elif pct < 0:
        console.print(
            f"\n  [bold red]⚠ {abs(pct)}% slower[/bold red]  "
            f"[dim]The optimized query is slower — review before applying[/dim]"
        )
    else:
        console.print("\n  [yellow]No measurable difference[/yellow]")

    # Row mismatch warning — critical
    if result["row_mismatch"]:
        console.print(
            f"\n  [bold red]⚠ ROW COUNT MISMATCH[/bold red]\n"
            f"  Before returned {b['row_count']} rows, after returned {a['row_count']} rows.\n"
            f"  [red]DO NOT apply this optimization — the queries return different data.[/red]\n"
            f"  Review the optimized query carefully in SSMS before proceeding."
        )

    console.print(f"\n  [dim]Run 'python agent.py save-benchmark' to save this result[/dim]")


def _print_workload_summary(results: list):
    """Print a summary table for a multi-query workload benchmark."""
    valid = [r for r in results if "improvement_pct" in r]
    if not valid:
        return

    console.print()
    table = Table(
        title="Workload Benchmark Summary",
        show_header=True,
        header_style="bold white",
        border_style="cyan",
    )
    table.add_column("Query",       style="cyan", min_width=25)
    table.add_column("Before (avg)", justify="right", style="red")
    table.add_column("After (avg)",  justify="right", style="green")
    table.add_column("Improvement",  justify="right", style="bold")
    table.add_column("Rows OK",      justify="center")

    for r in valid:
        rows_ok = "[green]✓[/green]" if not r["row_mismatch"] else "[red]⚠[/red]"
        improvement = (
            f"[green]{r['improvement_pct']}%[/green]"
            if r["improvement_pct"] > 0
            else f"[red]{r['improvement_pct']}%[/red]"
        )
        table.add_row(
            r["label"],
            f"{r['before']['avg_ms']}ms",
            f"{r['after']['avg_ms']}ms",
            improvement,
            rows_ok,
        )

    console.print(table)

    # Overall average improvement
    avg_improvement = round(
        sum(r["improvement_pct"] for r in valid) / len(valid), 1
    )
    console.print(f"\n  Overall average improvement: [bold green]{avg_improvement}%[/bold green]")
