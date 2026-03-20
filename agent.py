#!/usr/bin/env python3
# ============================================================
# agent.py — SQL Optimization Agent Toolkit
# Main entry point. Run everything from here.
# ============================================================
# USAGE EXAMPLES:
#   python agent.py test-connection
#   python agent.py list-objects
#   python agent.py schema measurements
#   python agent.py analyze "SELECT * FROM vw_dashboard WHERE machine_id=1"
#   python agent.py optimize-file queries/labview.sql
#   python agent.py optimize-view vw_dashboard
#   python agent.py plan plans/slow_query.sqlplan
#   python agent.py workload queries/
# ============================================================

import typer
from rich.console import Console
from rich.panel import Panel

app     = typer.Typer(help="SQL Optimization Agent — local AI-powered database assistant")
console = Console()


def _banner():
    console.print(Panel.fit(
        "[bold cyan]SQL Optimization Agent[/bold cyan]\n"
        "[dim]Offline · Local · Powered by Ollama[/dim]",
        border_style="cyan"
    ))


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
    client: str = typer.Option(..., help="Client name to deploy to")
):
    """[Phase 6] Generate client deployment package."""
    _banner()
    console.print(f"[yellow]⏳ Deployment packager — coming in Phase 6[/yellow]")
    console.print(f"Client: [dim]{client}[/dim]")


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
