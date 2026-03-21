# ============================================================
# tools/pipeline.py
# Full-run pipeline — single entry point that chains:
#
#   Phase A: SINGLE QUERY
#     1.  Validate input and connection
#     2.  Auto-detect tables, pull schema
#     3.  Optimize (execution plan + two-model AI chain)
#     4.  Benchmark before vs after
#     5.  Generate migration file
#     6.  Git commit
#     7.  Generate quick report
#     8.  Print summary
#
#   Phase B: BATCH FOLDER
#     Same as above but loops over every .sql file in a folder.
#     Produces one migration per file, then one combined
#     deployment package at the end covering all of them.
#
# USAGE:
#   from tools.pipeline import run_single, run_batch
#
#   run_single("SELECT * FROM vw_dashboard WHERE machine_id=1")
#   run_batch("queries/")
#
# The agent.py full-run command calls these directly.
# ============================================================

import time
from datetime import datetime
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.rule import Rule
from rich.table import Table

console = Console()


def _ok(msg):   console.print(f"  [green]✓[/green] {msg}")
def _warn(msg): console.print(f"  [yellow]⚠[/yellow]  {msg}")
def _info(msg): console.print(f"  [dim]{msg}[/dim]")
def _fail(msg): console.print(f"  [red]✗[/red] {msg}")

def _phase(label: str):
    """Print a phase header — visually separates major stages."""
    console.print()
    console.print(Rule(f"[bold cyan]{label}[/bold cyan]"))




# ============================================================
# SCHEMA HELPER — auto-detects tables in query and pulls schema
# (Duplicated from agent.py to avoid circular import)
# ============================================================

def _fetch_schemas_for_query(query: str) -> list:
    """
    Auto-detect which tables/views a query references,
    pull their schema, and return a list of schema dicts.
    """
    from tools.schema import get_schema, list_all_tables, list_all_views, get_view_definition

    all_tables  = list_all_tables()
    all_views   = list_all_views()
    all_objects = all_tables + all_views
    query_upper = query.upper()

    found = [obj for obj in all_objects if obj.upper() in query_upper]
    if not found:
        console.print("  [yellow]⚠ Could not auto-detect tables — pulling all schemas[/yellow]")
        found = all_tables

    console.print(f"  [cyan]→ Schema for:[/cyan] {', '.join(found)}")

    schemas = []
    for obj in found:
        if obj in all_tables:
            schemas.append(get_schema(obj))
        else:
            # View — get schemas of underlying tables
            vd = get_view_definition(obj)
            for ref_table in vd.get("referenced_tables", []):
                if ref_table in all_tables:
                    s = get_schema(ref_table)
                    if s not in schemas:
                        schemas.append(s)
    return schemas


# ============================================================
# SINGLE QUERY PIPELINE
# ============================================================

def run_single(
    query:          str,
    label:          str  = "",
    benchmark_runs: int  = None,
    skip_deploy:    bool = False,
) -> dict:
    """
    Full pipeline for a single query.

    Args:
        query:          SQL query to optimize
        label:          optional short name (used in report filenames)
        benchmark_runs: override default benchmark run count from config
        skip_deploy:    skip generating the deployment package at the end

    Returns:
        dict with all results across every stage

    Usage:
        result = run_single("SELECT * FROM vw_dashboard WHERE machine_id=1")
        result = run_single("SELECT ...", label="dashboard filter", skip_deploy=True)
    """
    t0     = time.time()
    result = {
        "query":              query,
        "label":              label or query[:50],
        "optimization":       None,
        "benchmark":          None,
        "migration":          None,
        "report_path":        None,
        "deployment_package": None,
        "success":            False,
        "errors":             [],
        "timestamp":          datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }

    console.print()
    console.print(Panel(
        "[bold cyan]Full-Run Pipeline[/bold cyan]\n"
        "[dim]Optimize → Benchmark → Migrate → Report → Deploy Package[/dim]",
        border_style="cyan", expand=False,
    ))

    # ── A1: Validate connection ───────────────────────────
    _phase("A1 — Connection Check")
    try:
        from tools.schema import test_connection
        connected = test_connection()
        if not connected:
            _fail("Cannot connect to SQL Server — aborting pipeline")
            result["errors"].append("DB connection failed")
            return result
    except Exception as e:
        _fail(f"Connection check failed: {e}")
        result["errors"].append(str(e))
        return result

    # ── A2: Schema ────────────────────────────────────────
    _phase("A2 — Schema Detection")
    try:
        schema_list = _fetch_schemas_for_query(query)
        if not schema_list:
            _warn("No schema found — optimization may be less accurate")
    except Exception as e:
        _warn(f"Schema fetch failed: {e} — continuing without schema")
        schema_list = []

    # ── A3: Optimize ─────────────────────────────────────
    _phase("A3 — Query Optimization")
    try:
        from tools.optimizer import optimize_query
        opt_result = optimize_query(query, schema_list)
        result["optimization"] = opt_result
        _ok("Optimization complete")
    except Exception as e:
        _fail(f"Optimization failed: {e}")
        result["errors"].append(f"Optimization: {e}")
        return result

    optimized_query = opt_result.get("optimized_query", "")
    if not optimized_query:
        _warn("No optimized query produced — skipping benchmark")
        result["success"] = True
        _print_single_summary(result, time.time() - t0)
        return result

    # ── A4: Benchmark ─────────────────────────────────────
    _phase("A4 — Benchmark: Before vs After")
    try:
        from tools.benchmarker import benchmark_query, save_benchmark
        bench_result = benchmark_query(
            original_query  = query,
            optimized_query = optimized_query,
            label           = label or "full-run",
            runs            = benchmark_runs,
        )
        result["benchmark"] = bench_result

        # Save benchmark log
        if "error" not in bench_result:
            save_benchmark(bench_result)
            _ok(
                f"Benchmark saved — "
                f"{bench_result['before']['avg_ms']}ms → "
                f"{bench_result['after']['avg_ms']}ms "
                f"({bench_result['improvement_pct']}% improvement)"
            )

            # Warn if row counts differ — do not proceed to deploy
            if bench_result.get("row_mismatch"):
                _fail("Row count mismatch — optimized query returns different data")
                _fail("Stopping before migration and deployment. Review the optimized query.")
                result["errors"].append("Row count mismatch — optimization returns different data")
                _print_single_summary(result, time.time() - t0)
                return result
        else:
            _warn(f"Benchmark failed: {bench_result.get('error')} — continuing")
    except Exception as e:
        _warn(f"Benchmark error: {e} — continuing without timing data")
        bench_result = {}

    # ── A5: Migration ─────────────────────────────────────
    _phase("A5 — Migration File")
    try:
        # Migration was already auto-generated inside optimizer (Step 8b)
        # Retrieve it from the optimization result if present
        migration = opt_result.get("migration")

        if not migration and opt_result.get("index_scripts"):
            # Re-generate with benchmark data attached
            from tools.migrator import migration_from_optimization
            migration = migration_from_optimization(opt_result, bench_result)

        if migration:
            result["migration"] = migration
            # Update migration with benchmark data if not already set
            _ok(f"Migration: migrations/{migration['filename']}")
        else:
            _info("No schema changes (no CREATE INDEX) — migration not generated")
    except Exception as e:
        _warn(f"Migration error: {e}")

    # ── A6: Git commit ────────────────────────────────────
    _phase("A6 — Git Commit")
    try:
        from tools.git_manager import commit_optimization

        b_ms  = bench_result.get("before", {}).get("avg_ms") if bench_result else None
        a_ms  = bench_result.get("after",  {}).get("avg_ms") if bench_result else None
        pct   = bench_result.get("improvement_pct")           if bench_result else None
        label_str = label or ", ".join(s["table_name"] for s in schema_list)
        mig_path  = result["migration"]["path"] if result.get("migration") else None

        commit_optimization(
            query_label     = label_str,
            migration_path  = mig_path,
            before_ms       = b_ms,
            after_ms        = a_ms,
            improvement_pct = pct,
        )
    except Exception as e:
        _warn(f"Git commit skipped: {e}")

    # ── A7: Quick report ──────────────────────────────────
    _phase("A7 — Report")
    try:
        from tools.reporter import quick_report
        report_text = quick_report(opt_result, bench_result if bench_result else None)
        _ok("Report saved to reports/")
        result["report_path"] = "reports/"
    except Exception as e:
        _warn(f"Report generation failed: {e}")

    # ── A7b: Record to history ─────────────────────────────
    try:
        from tools.history import record_from_pipeline
        run_id = record_from_pipeline(result)
        result["history_id"] = run_id
        _ok(f"Recorded to history (run #{run_id})")
    except Exception as e:
        _warn(f"History record failed: {e}")

    # ── A8: Deployment package ────────────────────────────
    if not skip_deploy and result.get("migration"):
        _phase("A8 — Deployment Package")
        try:
            from tools.reporter import generate_deployment_package
            package = generate_deployment_package()
            result["deployment_package"] = package
        except Exception as e:
            _warn(f"Deployment package failed: {e}")
    elif skip_deploy:
        _info("Deployment package skipped (--no-deploy flag)")
    else:
        _info("No migration generated — deployment package skipped")

    result["success"] = True
    _print_single_summary(result, time.time() - t0)
    return result


# ============================================================
# BATCH FOLDER PIPELINE
# ============================================================

def run_batch(
    folder:         str,
    benchmark_runs: int  = None,
    skip_deploy:    bool = False,
) -> dict:
    """
    Full pipeline for a folder of .sql files.
    Processes each file independently then generates one combined
    deployment package covering all changes.

    Args:
        folder:         path to folder containing .sql files
        benchmark_runs: override benchmark run count
        skip_deploy:    skip final deployment package

    Returns:
        dict with results per file + combined summary

    Usage:
        results = run_batch("queries/")
    """
    folder_path = Path(folder)
    sql_files   = sorted(folder_path.glob("*.sql"))

    if not sql_files:
        console.print(f"[red]✗ No .sql files found in: {folder}[/red]")
        return {"error": f"No .sql files in {folder}"}

    console.print()
    console.print(Panel(
        f"[bold cyan]Batch Full-Run Pipeline[/bold cyan]\n"
        f"[dim]{len(sql_files)} .sql files in {folder}[/dim]",
        border_style="cyan", expand=False,
    ))

    results    = []
    successful = 0
    failed     = 0
    t0         = time.time()

    for i, sql_file in enumerate(sql_files, 1):
        console.print()
        console.print(Panel(
            f"[bold]File {i}/{len(sql_files)}[/bold] — {sql_file.name}",
            border_style="blue", expand=False,
        ))

        query = sql_file.read_text(encoding="utf-8").strip()
        if not query:
            _warn(f"Skipping empty file: {sql_file.name}")
            continue

        # Run single pipeline per file, skip individual deploy packages
        file_result = run_single(
            query          = query,
            label          = sql_file.stem,
            benchmark_runs = benchmark_runs,
            skip_deploy    = True,   # batch deploy is done at the end
        )

        file_result["source_file"] = sql_file.name
        results.append(file_result)

        if file_result["success"]:
            successful += 1
        else:
            failed += 1
            _warn(f"File {sql_file.name} had errors: {file_result['errors']}")

    # ── Combined deployment package ───────────────────────
    if not skip_deploy and successful > 0:
        _phase("BATCH COMPLETE — Generating Combined Deployment Package")
        try:
            from tools.reporter import generate_deployment_package
            package = generate_deployment_package()
            console.print()
            _ok(f"Combined package: {package.get('folder_name', 'deployments/')}")
        except Exception as e:
            _warn(f"Combined deployment package failed: {e}")
    elif skip_deploy:
        _info("Combined deployment package skipped (--no-deploy flag)")

    elapsed = round(time.time() - t0, 1)
    _print_batch_summary(results, successful, failed, elapsed)

    return {
        "files_processed": len(sql_files),
        "successful":      successful,
        "failed":          failed,
        "results":         results,
        "elapsed_s":       elapsed,
    }


# ============================================================
# TERMINAL SUMMARIES
# ============================================================

def _print_single_summary(result: dict, elapsed: float):
    """Print final summary panel after single-query full-run."""
    console.print()
    console.print(Rule("[bold cyan]FULL-RUN COMPLETE[/bold cyan]"))

    bench = result.get("benchmark", {})
    opt   = result.get("optimization", {})

    # Headline stat
    if bench and "error" not in bench:
        b_ms = bench["before"]["avg_ms"]
        a_ms = bench["after"]["avg_ms"]
        pct  = bench["improvement_pct"]
        spd  = bench["speedup"]
        if pct > 0:
            console.print(
                f"\n  [bold green]{pct}% faster[/bold green]  "
                f"[dim]{b_ms}ms → {a_ms}ms  ({spd}x speedup)[/dim]"
            )
        elif pct < 0:
            console.print(f"\n  [bold red]{abs(pct)}% slower[/bold red] — review before applying")
        else:
            console.print("\n  [yellow]No measurable improvement[/yellow]")

    # What was produced
    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column(style="dim",   min_width=22)
    table.add_column(style="green")

    if opt and opt.get("optimized_query"):
        table.add_row("Optimized query",    "✓ produced")
    if opt and opt.get("index_scripts"):
        table.add_row("Index scripts",      f"✓ {len(opt['index_scripts'])} script(s)")
    if result.get("migration"):
        table.add_row("Migration file",     f"✓ {result['migration']['filename']}")
    if result.get("report_path"):
        table.add_row("Report",             "✓ saved to reports/")
    if result.get("deployment_package"):
        pkg = result["deployment_package"]
        table.add_row("Deployment package", f"✓ deployments/{pkg.get('folder_name', '')}")

    console.print()
    console.print(table)

    if result["errors"]:
        console.print("\n[yellow]Warnings during run:[/yellow]")
        for e in result["errors"]:
            console.print(f"  [yellow]•[/yellow] {e}")

    console.print(f"\n  [dim]Total time: {elapsed}s[/dim]")
    console.print()
    console.print("  [dim]Next: review optimized query above, apply index scripts in SSMS,[/dim]")
    console.print("  [dim]then run [cyan]python agent.py mark-applied <number>[/cyan][/dim]")


def _print_batch_summary(results: list, successful: int, failed: int, elapsed: float):
    """Print final summary table after batch full-run."""
    console.print()
    console.print(Rule("[bold cyan]BATCH FULL-RUN COMPLETE[/bold cyan]"))

    table = Table(
        show_header=True, header_style="bold cyan",
        border_style="dim",
    )
    table.add_column("File",          min_width=28)
    table.add_column("Before",        justify="right", style="red")
    table.add_column("After",         justify="right", style="green")
    table.add_column("Improvement",   justify="right", style="bold")
    table.add_column("Migration",     justify="center")
    table.add_column("Status",        justify="center")

    total_before = []
    total_after  = []

    for r in results:
        bench  = r.get("benchmark", {})
        mig    = r.get("migration", {})
        source = r.get("source_file", "?")

        if bench and "error" not in bench and bench.get("before"):
            b_ms = bench["before"]["avg_ms"]
            a_ms = bench["after"]["avg_ms"]
            pct  = bench["improvement_pct"]
            total_before.append(b_ms)
            total_after.append(a_ms)

            imp_str = (
                f"[green]{pct}%[/green]" if pct > 0
                else f"[red]{pct}%[/red]"
            )
            b_str = f"{b_ms}ms"
            a_str = f"{a_ms}ms"
        else:
            b_str = imp_str = a_str = "—"

        mig_str    = f"[cyan]{mig['filename'][:20]}[/cyan]" if mig else "[dim]none[/dim]"
        status_str = "[green]✓[/green]" if r["success"] else "[red]✗[/red]"

        table.add_row(source, b_str, a_str, imp_str, mig_str, status_str)

    console.print(table)

    # Overall stats
    if total_before and total_after:
        avg_before = round(sum(total_before) / len(total_before), 1)
        avg_after  = round(sum(total_after)  / len(total_after), 1)
        avg_pct    = round(((avg_before - avg_after) / avg_before) * 100, 1)
        console.print(
            f"\n  Overall: [bold green]{avg_pct}% average improvement[/bold green]  "
            f"[dim](avg {avg_before}ms → {avg_after}ms)[/dim]"
        )

    console.print(
        f"  [dim]{successful} succeeded · {failed} failed · {elapsed}s total[/dim]"
    )
