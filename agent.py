#!/usr/bin/env python3
# ============================================================
# agent.py — SQL Optimization Agent Toolkit
# Main entry point. Run everything from here.
# ============================================================
# USAGE EXAMPLES:
#   python agent.py full-run --query "SELECT * FROM vw_dashboard WHERE id=1"
#   python agent.py full-run --folder queries/
#   python agent.py analyze "SELECT * FROM vw_dashboard WHERE machine_id=1"
#   python agent.py optimize-file queries/labview.sql
#   python agent.py optimize-view vw_dashboard
#   python agent.py benchmark --before "..." --after "..."
#   python agent.py deploy
#   python agent.py migrations
#   python agent.py git-log
# ============================================================

import typer
from rich.console import Console
from rich.panel import Panel
from pathlib import Path

app     = typer.Typer(help="SQL Optimization Agent — local AI-powered database assistant")
console = Console()


def _banner():
    console.print(Panel.fit(
        "[bold cyan]SQL Optimization Agent[/bold cyan]\n"
        "[dim]Offline · Local · Powered by Ollama[/dim]",
        border_style="cyan"
    ))



# ============================================================
# FULL-RUN PIPELINE — single command does everything
# ============================================================

@app.command()
def full_run(
    query:       str  = typer.Option(None,  "--query",     "-q", help="Single SQL query to run through full pipeline"),
    folder:      str  = typer.Option(None,  "--folder",    "-f", help="Folder of .sql files for batch processing"),
    runs:        int  = typer.Option(None,  "--runs",      "-r", help="Benchmark runs per query (default from config.py)"),
    no_deploy:   bool = typer.Option(False, "--no-deploy",       help="Skip deployment package generation"),
    label:       str  = typer.Option("",    "--label",     "-l", help="Short name for this run (used in filenames)"),
):
    """
    Full pipeline: optimize → benchmark → migrate → report → deploy package.

    Single query:
        python agent.py full-run --query "SELECT * FROM vw_dashboard WHERE machine_id=1"

    Batch folder:
        python agent.py full-run --folder queries/

    Skip deployment package (just optimize + benchmark + migrate):
        python agent.py full-run --query "SELECT ..." --no-deploy
    """
    _banner()

    if not query and not folder:
        console.print("[red]✗ Provide either --query or --folder[/red]")
        console.print("  Example: [cyan]python agent.py full-run --query \"SELECT * FROM your_table\"[/cyan]")
        console.print("  Example: [cyan]python agent.py full-run --folder queries/[/cyan]")
        raise typer.Exit(1)

    if query and folder:
        console.print("[red]✗ Provide either --query or --folder, not both[/red]")
        raise typer.Exit(1)

    from tools.pipeline import run_single, run_batch

    if query:
        run_single(
            query          = query,
            label          = label,
            benchmark_runs = runs,
            skip_deploy    = no_deploy,
        )
    else:
        run_batch(
            folder         = folder,
            benchmark_runs = runs,
            skip_deploy    = no_deploy,
        )


# ============================================================
# PHASE 1 COMMANDS — DB connection and inspection
# ============================================================

@app.command()
def test_connection():
    """Test that the database connection in config.py works."""
    _banner()
    from tools.schema import test_connection as _test
    _test()


@app.command()
def list_objects():
    """List all tables and views in the database."""
    _banner()
    from tools.schema import list_all_tables, list_all_views

    tables = list_all_tables()
    views  = list_all_views()

    console.print(f"\n[bold]Tables ({len(tables)})[/bold]")
    for t in tables:
        console.print(f"  [green]•[/green] {t}")

    console.print(f"\n[bold]Views ({len(views)})[/bold]")
    for v in views:
        console.print(f"  [cyan]•[/cyan] {v}")


@app.command()
def schema(table_name: str = typer.Argument(..., help="Table name to inspect")):
    """Show columns and indexes for a table."""
    _banner()
    from tools.schema import get_schema

    result = get_schema(table_name)

    console.print(f"\n[bold]Columns[/bold]")
    for col in result["columns"]:
        pk   = " [yellow][PK][/yellow]" if col["primary_key"] == "YES" else ""
        null = " [dim]NULL[/dim]" if col["nullable"] == "YES" else ""
        console.print(f"  {col['name']}  [dim]{col['type']}[/dim]{pk}{null}")

    console.print(f"\n[bold]Indexes ({len(result['indexes'])})[/bold]")
    if result["indexes"]:
        for idx in result["indexes"]:
            console.print(f"  [cyan]•[/cyan] {idx['name']}  [dim]({idx['type']})[/dim]")
            console.print(f"    Keys: {idx['key_columns']}")
            if idx["included_columns"]:
                console.print(f"    Includes: {idx['included_columns']}")
    else:
        console.print("  [yellow]No non-clustered indexes found[/yellow]")

    row_count = result["estimated_row_count"]
    console.print(
        f"\n[dim]Estimated rows: {row_count:,}[/dim]"
        if isinstance(row_count, int)
        else f"\n[dim]Row count: unknown[/dim]"
    )


@app.command()
def show_view(view_name: str = typer.Argument(..., help="View name to inspect")):
    """Show the SQL definition of a view."""
    _banner()
    from tools.schema import get_view_definition

    result = get_view_definition(view_name)

    if "error" in result:
        console.print(f"[red]{result['error']}[/red]")
        return

    console.print(f"\n[bold]Referenced tables:[/bold] {', '.join(result['referenced_tables'])}")
    console.print(f"\n[bold]View Definition:[/bold]\n")
    console.print(result["definition"])


# ============================================================
# PHASE 2 COMMANDS — AI optimization
# ============================================================

def _auto_fetch_schemas(query: str):
    """Helper: auto-detect tables in query and pull their schemas."""
    from tools.schema import get_schema, list_all_tables, list_all_views

    all_tables = list_all_tables()
    all_views  = list_all_views()
    all_objects = all_tables + all_views
    query_upper = query.upper()

    found = [obj for obj in all_objects if obj.upper() in query_upper]

    if not found:
        console.print("[yellow]⚠ Could not auto-detect tables — pulling all schemas[/yellow]")
        found = all_tables

    console.print(f"[cyan]→ Pulling schema for:[/cyan] {', '.join(found)}")

    schemas = []
    for obj in found:
        if obj in all_tables:
            schemas.append(get_schema(obj))
        else:
            # For views, get the view def and schemas of tables it references
            from tools.schema import get_view_definition
            vd = get_view_definition(obj)
            for ref_table in vd.get("referenced_tables", []):
                if ref_table in all_tables:
                    schemas.append(get_schema(ref_table))

    return schemas


@app.command()
def analyze(
    query: str = typer.Argument(..., help="SQL query to optimize"),
):
    """Optimize a SQL query — auto-detects tables, fetches execution plan, runs AI pipeline."""
    _banner()
    from tools.optimizer import optimize_query

    schema_list = _auto_fetch_schemas(query)
    optimize_query(query, schema_list)


@app.command()
def optimize_file(
    path: str = typer.Argument(..., help="Path to .sql file to optimize"),
):
    """Optimize a .sql file — reads file, auto-detects tables, runs full AI pipeline."""
    _banner()
    from pathlib import Path
    from tools.optimizer import optimize_query

    sql_path = Path(path)
    if not sql_path.exists():
        console.print(f"[red]✗ File not found: {path}[/red]")
        raise typer.Exit(1)

    query = sql_path.read_text(encoding="utf-8").strip()
    console.print(f"[cyan]→ Loaded:[/cyan] {sql_path.name} ({len(query)} chars)\n")

    schema_list = _auto_fetch_schemas(query)
    optimize_query(query, schema_list)


@app.command()
def optimize_view(
    view_name: str = typer.Argument(..., help="View name to optimize"),
):
    """Refactor a view for better read performance."""
    _banner()
    from tools.schema import get_view_definition, get_schema, list_all_tables
    from tools.optimizer import optimize_view as _optimize_view

    view_def    = get_view_definition(view_name)
    if "error" in view_def:
        console.print(f"[red]✗ {view_def['error']}[/red]")
        raise typer.Exit(1)

    all_tables  = list_all_tables()
    schema_list = [
        get_schema(t) for t in view_def["referenced_tables"]
        if t in all_tables
    ]

    _optimize_view(view_def, schema_list)


@app.command()
def plan(
    path: str = typer.Argument(..., help="Path to .sqlplan file from SSMS"),
    query: str = typer.Option("", "--query", "-q", help="The original query (improves analysis)"),
):
    """Analyze a SQL Server execution plan (.sqlplan file from SSMS)."""
    _banner()
    from tools.planner import analyze_execution_plan
    analyze_execution_plan(path, query=query)


@app.command()
def workload(
    folder: str = typer.Argument(..., help="Folder containing .sql files to analyze as a workload"),
):
    """Design optimal indexes for a folder of .sql files treated as a workload."""
    _banner()
    from pathlib import Path
    from tools.optimizer import generate_index_scripts

    folder_path = Path(folder)
    sql_files   = list(folder_path.glob("*.sql"))

    if not sql_files:
        console.print(f"[red]✗ No .sql files found in: {folder}[/red]")
        raise typer.Exit(1)

    console.print(f"[cyan]→ Found {len(sql_files)} .sql files[/cyan]")
    queries = [f.read_text(encoding="utf-8").strip() for f in sql_files]

    combined = "\n".join(queries)
    schema_list = _auto_fetch_schemas(combined)

    generate_index_scripts(queries, schema_list)



# ============================================================
# PHASE 3 COMMANDS — benchmarking
# ============================================================

@app.command()
def benchmark(
    before: str  = typer.Option(...,   "--before", "-b", help="Original (slow) query"),
    after:  str  = typer.Option(...,   "--after",  "-a", help="Optimized query"),
    label:  str  = typer.Option("Query", "--label", "-l", help="Name for this benchmark"),
    runs:   int  = typer.Option(None,  "--runs",   "-r", help="Number of runs (default from config.py)"),
    save:   bool = typer.Option(False, "--save",   "-s", help="Save result to reports/"),
):
    """
    Compare before vs after query timing. Runs each N times and shows stats.

    Example:
        python agent.py benchmark \\
          --before "SELECT * FROM vw_dashboard WHERE machine_id=1" \\
          --after  "SELECT id, val FROM measurements WITH(NOLOCK) WHERE machine_id=1" \\
          --label  "dashboard filter" --save
    """
    _banner()
    from tools.benchmarker import benchmark_query, save_benchmark
    result = benchmark_query(
        original_query  = before,
        optimized_query = after,
        label           = label,
        runs            = runs,
    )
    if save and "error" not in result:
        save_benchmark(result)


@app.command()
def baseline(
    query: str = typer.Argument(...,      help="Query to time before optimizing"),
    label: str = typer.Option("Query",   "--label", "-l", help="Name for this baseline"),
    runs:  int = typer.Option(None,      "--runs",  "-r", help="Number of runs"),
):
    """
    Time a single query to establish a baseline before optimizing.

    Example:
        python agent.py baseline "SELECT * FROM vw_dashboard" --label "dashboard"
    """
    _banner()
    from tools.benchmarker import benchmark_single
    benchmark_single(query, label=label, runs=runs)


@app.command()
def benchmark_files(
    before_file: str  = typer.Argument(...,      help="Path to original .sql file"),
    after_file:  str  = typer.Argument(...,      help="Path to optimized .sql file"),
    label:       str  = typer.Option("Query",   "--label", "-l", help="Name for benchmark"),
    runs:        int  = typer.Option(None,      "--runs",  "-r", help="Number of runs"),
    save:        bool = typer.Option(False,     "--save",  "-s", help="Save to reports/"),
):
    """
    Compare two .sql files — original vs optimized.

    Example:
        python agent.py benchmark-files queries/original.sql queries/optimized.sql --save
    """
    _banner()
    from pathlib import Path
    from tools.benchmarker import benchmark_query, save_benchmark

    for p in [before_file, after_file]:
        if not Path(p).exists():
            console.print(f"[red]✗ File not found: {p}[/red]")
            raise typer.Exit(1)

    before_sql = Path(before_file).read_text(encoding="utf-8").strip()
    after_sql  = Path(after_file).read_text(encoding="utf-8").strip()

    console.print(f"[cyan]→ Before:[/cyan] {Path(before_file).name}")
    console.print(f"[cyan]→ After:[/cyan]  {Path(after_file).name}\n")

    result = benchmark_query(before_sql, after_sql, label=label, runs=runs)
    if save and "error" not in result:
        save_benchmark(result)






# ============================================================
# PHASE 2.7 — TUI
# ============================================================

@app.command()
def ui():
    """
    Launch the Terminal UI — OpenCode-style four-panel interface.

    Panels:
      Top-left     Schema tree (tables + views, click to inspect)
      Top-right    Live output (pipeline steps stream here)
      Bottom-left  Recent runs (last 8 from history.db)
      Bottom-right Progress bar + query input

    Keyboard shortcuts:
      a   Analyze / Full-run a query
      f   Batch full-run on queries/ folder
      r   Refresh schema tree
      d   Generate deployment package
      h   View run history
      w   Run schema watcher
      s   Take schema snapshot
      q   Quit

    Requires: pip install textual
    """
    try:
        from tui.app import run_tui
        run_tui()
    except ImportError:
        console.print("[red]✗ Textual not installed[/red]")
        console.print("  Install with: [cyan]pip install textual[/cyan]")
        console.print("  Then run:     [cyan]python agent.py ui[/cyan]")


# ============================================================
# PHASE 2.6 COMMANDS — schema watcher
# ============================================================

@app.command()
def watch(
    force: bool = typer.Option(False, "--force", "-f",
                               help="Re-run even if already ran today"),
):
    """
    Run the schema watcher — diffs today's schema against yesterday.
    Alerts you to changes that could break existing optimizations.

    Schedule this to run automatically every morning:
        python agent.py watch-schedule
    """
    _banner()
    from tools.watcher import run_watch
    run_watch(force=force)


@app.command()
def watch_report():
    """Show the most recent schema watch report."""
    _banner()
    from tools.watcher import print_last_watch_report
    print_last_watch_report()


@app.command()
def watch_schedule():
    """
    Generate Windows Task Scheduler files to run the watcher
    automatically every morning at 07:00.

    After running this command, follow the instructions in
    scheduler/README.md to register the scheduled task.
    """
    _banner()
    from tools.watcher import generate_scheduler_script
    from rich.panel import Panel as RPanel

    setup_dir = generate_scheduler_script()

    console.print()
    console.print(RPanel(
        f"[bold green]✓ Scheduler files generated[/bold green]\n"
        f"[dim]{setup_dir}[/dim]",
        border_style="green", expand=False,
    ))
    console.print("\n[bold]To register the daily task:[/bold]")
    console.print("  1. Open PowerShell [bold]as Administrator[/bold]")
    console.print("  2. Run:")
    console.print(f"     [cyan]cd {setup_dir}[/cyan]")
    console.print("     [cyan]Set-ExecutionPolicy RemoteSigned -Scope CurrentUser[/cyan]")
    console.print("     [cyan].\\register_task.ps1[/cyan]")
    console.print("\n  Watcher will run every morning at [bold]07:00[/bold]")
    console.print("  Check results with: [cyan]python agent.py watch-report[/cyan]")


@app.command()
def snapshot():
    """Take a manual schema snapshot without running the diff."""
    _banner()
    from tools.watcher import take_snapshot, save_snapshot

    console.print("[cyan]→ Taking schema snapshot...[/cyan]")
    try:
        snap  = take_snapshot()
        paths = save_snapshot(snap)
        console.print(
            f"\n[green]✓ Snapshot saved[/green]  "
            f"[dim]{Path(paths['dated']).name}[/dim]"
        )
        console.print(
            f"  Tables: {len(snap['tables'])}  "
            f"Views: {len(snap['views'])}"
        )
    except Exception as e:
        console.print(f"[red]✗ Snapshot failed: {e}[/red]")


# ============================================================
# PHASE 2.5 COMMANDS — history, trends, comparison
# ============================================================

@app.command()
def history(
    query:      str  = typer.Option(None,  "--query",  "-q", help="Filter by query text or label"),
    table:      str  = typer.Option(None,  "--table",  "-t", help="Filter by table or view name"),
    limit:      int  = typer.Option(20,    "--limit",  "-n", help="Max results"),
    top:        bool = typer.Option(False, "--top",         help="Show top improvements only"),
    regressions:bool = typer.Option(False, "--regressions", help="Show runs that got worse"),
    stats:      bool = typer.Option(False, "--stats",       help="Show overall statistics"),
):
    """
    View run history, trends, and statistics.

    Examples:
        python agent.py history
        python agent.py history --table vw_dashboard
        python agent.py history --query "machine filter"
        python agent.py history --top
        python agent.py history --regressions
        python agent.py history --stats
    """
    _banner()
    from tools.history import (
        get_history, get_top_improvements, get_regressions,
        get_stats, print_history, print_stats
    )

    if stats:
        s = get_stats()
        print_stats(s)
        return

    if top:
        runs = get_top_improvements(limit=limit)
        print_history(runs, title=f"Top {limit} Improvements")
        return

    if regressions:
        runs = get_regressions()
        if not runs:
            console.print("[green]✓ No regressions found — all optimizations improved performance[/green]")
        else:
            print_history(runs, title="Regressions (optimized query was slower)")
        return

    runs = get_history(query=query, table_name=table, limit=limit)
    title = "Run History"
    if query: title += f" — query: {query}"
    if table: title += f" — table: {table}"
    print_history(runs, title=title)

    if not runs:
        console.print("[dim]Run some optimizations first, or try: python agent.py full-run --query '...'[/dim]")


@app.command()
def trend(
    table: str = typer.Option(None, "--table", "-t", help="Table or view name to show trend for"),
    query: str = typer.Option(None, "--query", "-q", help="Query text to match"),
):
    """
    Show improvement trend for a specific table or query over time.

    Examples:
        python agent.py trend --table vw_dashboard
        python agent.py trend --query "machine filter"
    """
    _banner()
    from tools.history import get_trend, get_history, print_trend, _fingerprint

    if not table and not query:
        console.print("[red]✗ Provide --table or --query[/red]")
        console.print("  Example: [cyan]python agent.py trend --table vw_dashboard[/cyan]")
        raise typer.Exit(1)

    if query:
        # Find matching runs then group by query hash
        runs = get_history(query=query, limit=50)
        if runs:
            # Get the hash from the first match and show trend for that hash
            from tools.history import get_trend as _get_trend
            runs = _get_trend(query_hash=runs[0]["query_hash"])
            print_trend(runs, label=query)
        else:
            console.print(f"[yellow]No runs found matching: {query}[/yellow]")
    else:
        from tools.history import get_trend as _get_trend
        runs = _get_trend(table_name=table)
        print_trend(runs, label=table)


@app.command()
def compare(
    run_a: int = typer.Argument(..., help="ID of first run (from history command)"),
    run_b: int = typer.Argument(..., help="ID of second run"),
):
    """
    Compare two specific runs side by side.

    First find run IDs with:
        python agent.py history --table vw_dashboard

    Then compare:
        python agent.py compare 3 12
    """
    _banner()
    from tools.history import compare_runs, print_compare
    comparison = compare_runs(run_a, run_b)
    print_compare(comparison)


# ============================================================
# PHASE 2.1 COMMANDS — migrations and Git
# ============================================================

@app.command()
def migrations(
    status: str = typer.Option(None, "--status", "-s",
                               help="Filter by: pending, applied, rolled_back"),
):
    """List all migration files and their status."""
    _banner()
    from tools.migrator import list_migrations
    from rich.table import Table as RichTable

    items = list_migrations(status_filter=status)

    if not items:
        msg = f"No {status} migrations found." if status else "No migrations found yet."
        console.print(f"[yellow]{msg}[/yellow]")
        console.print("[dim]Migrations are generated automatically after each optimization.[/dim]")
        return

    table = RichTable(show_header=True, header_style="bold cyan")
    table.add_column("#",           justify="right",  style="dim",   width=5)
    table.add_column("Description", min_width=35)
    table.add_column("Date",        style="dim",       min_width=16)
    table.add_column("Tables",      style="cyan",      min_width=20)
    table.add_column("Improvement", justify="right")
    table.add_column("Status",      justify="center")

    for m in items:
        improvement = (
            f"[green]{m['improvement_pct']}%[/green]"
            if m.get("improvement_pct") else "[dim]—[/dim]"
        )
        status_col = {
            "pending":     "[yellow]pending[/yellow]",
            "applied":     "[green]applied[/green]",
            "rolled_back": "[red]rolled back[/red]",
        }.get(m["status"], m["status"])

        table.add_row(
            str(m["number"]),
            m["description"],
            m["date"][:16],
            ", ".join(m.get("tables_affected", []))[:25],
            improvement,
            status_col,
        )

    console.print(table)
    pending = sum(1 for m in items if m["status"] == "pending")
    if pending:
        console.print(
            f"\n[yellow]{pending} pending migration(s)[/yellow] — "
            f"[dim]apply these before generating a deployment package[/dim]"
        )


@app.command()
def mark_applied(
    number: int = typer.Argument(..., help="Migration number to mark as applied"),
    client: str = typer.Option(None, "--client", "-c", help="Client name (default: from config.py)"),
):
    """Mark a migration as applied to a client system."""
    _banner()
    from tools.migrator import mark_applied as _mark
    _mark(number, client)


@app.command()
def mark_rolled_back(
    number: int = typer.Argument(..., help="Migration number to mark as rolled back"),
):
    """Mark a migration as rolled back."""
    _banner()
    from tools.migrator import mark_rolled_back as _rollback
    _rollback(number)


@app.command()
def git_log(
    limit: int = typer.Option(10, "--limit", "-n", help="Number of commits to show"),
):
    """Show recent Git commits made by the agent."""
    _banner()
    from tools.git_manager import get_recent_commits, get_status
    from rich.table import Table as RichTable

    status = get_status()
    if "error" not in status:
        console.print(
            f"[dim]Branch: [cyan]{status['branch']}[/cyan]  "
            f"{'[yellow]Uncommitted changes[/yellow]' if status['is_dirty'] else '[green]Clean[/green]'}[/dim]\n"
        )

    commits = get_recent_commits(limit)
    if not commits:
        console.print("[yellow]No commits found. Run: git init[/yellow]")
        return

    table = RichTable(show_header=True, header_style="bold cyan")
    table.add_column("Hash",    style="dim",   width=8)
    table.add_column("Type",    style="cyan",  width=12)
    table.add_column("Message", min_width=45)
    table.add_column("Date",    style="dim",   min_width=16)

    type_colors = {
        "optimize":  "green",
        "migrate":   "cyan",
        "benchmark": "yellow",
        "deploy":    "magenta",
        "watch":     "red",
        "baseline":  "blue",
    }
    for c in commits:
        color = type_colors.get(c["type"], "white")
        table.add_row(
            c["hash"],
            f"[{color}]{c['type']}[/{color}]",
            c["message"][len(f"[{c['type']}] "):].splitlines()[0][:60],
            c["date"],
        )
    console.print(table)


@app.command()
def git_init():
    """Initialize Git in the project if not already done."""
    _banner()
    from tools.git_manager import init_git_if_needed
    init_git_if_needed()


# ============================================================
# RUN LOGS — list and view saved run logs
# ============================================================

@app.command()
def runs(
    run_type: str = typer.Option(None, "--type", "-t", help="Filter: optimize, benchmark, plan, view"),
    limit:    int = typer.Option(10,   "--limit", "-n", help="Max results to show"),
):
    """List recent run logs saved in runs/ folder."""
    _banner()
    from tools.logger import list_runs
    from rich.table import Table as RichTable

    results = list_runs(run_type=run_type, limit=limit)

    if not results:
        console.print("[yellow]No run logs found. Run an optimization first.[/yellow]")
        return

    table = RichTable(show_header=True, header_style="bold cyan")
    table.add_column("Date",     style="dim",   min_width=16)
    table.add_column("Filename", min_width=45)
    table.add_column("Size",     justify="right", style="dim")

    for r in results:
        table.add_row(r["date"], r["filename"], f"{r['size_kb']}KB")

    console.print(table)
    console.print(f"\n[dim]Logs are in: runs/  — open any .md file to read the full run details[/dim]")


# ============================================================
# PLACEHOLDER COMMANDS — built in later phases
# ============================================================

@app.command()
def deploy(
    client:      str  = typer.Option(None,  "--client",  "-c",  help="Client name (default: from config.py)"),
    include_all: bool = typer.Option(False, "--all",     "-a",  help="Include already-applied migrations too"),
):
    """Generate a full client deployment package — deploy.sql, rollback.sql, walkthrough, report."""
    _banner()
    from tools.reporter import generate_deployment_package
    generate_deployment_package(client=client, include_all=include_all)


@app.command()
def report(
    query:   str = typer.Option(None, "--query",  "-q", help="Query to include in report"),
    open_it: bool = typer.Option(False, "--open", "-o", help="Open report in default viewer after saving"),
):
    """Generate a quick report from the last optimization run."""
    _banner()
    from tools.logger import list_runs
    from pathlib import Path

    # Find most recent optimization run log
    recent = list_runs(run_type="query", limit=1)
    if not recent:
        recent = list_runs(limit=1)

    if not recent:
        console.print("[yellow]No run logs found. Run an optimization first.[/yellow]")
        return

    log_path = recent[0]["path"]
    console.print(f"[cyan]→ Using run log:[/cyan] {recent[0]['filename']}")
    console.print(f"[dim]  {recent[0]['date']} · {recent[0]['size_kb']}KB[/dim]\n")

    # Read and display the run log as the report
    content = Path(log_path).read_text(encoding="utf-8")
    console.print(content)

    console.print(f"\n[dim]Full log: {log_path}[/dim]")


@app.command()
def new_client(name: str = typer.Argument(..., help="New client name")):
    """[Phase 9] Create a new client workspace from template."""
    _banner()
    console.print(f"[yellow]⏳ Multi-client system — coming in Phase 9[/yellow]")
    console.print(f"Client name: [dim]{name}[/dim]")


# ============================================================
# Entry point
# ============================================================
if __name__ == "__main__":
    app()
