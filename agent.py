#!/usr/bin/env python3
# ============================================================
# agent.py — SQL Optimization Agent Toolkit
# Main entry point. Run everything from here.
# ============================================================
# Usage:
#   python agent.py --test-connection
#   python agent.py --analyze "SELECT * FROM vw_dashboard"
#   python agent.py --view vw_dashboard
# ============================================================

import typer
from rich.console import Console
from rich.panel import Panel
from rich import print as rprint

app     = typer.Typer(help="SQL Optimization Agent — local AI-powered database assistant")
console = Console()


def _banner():
    console.print(Panel.fit(
        "[bold cyan]SQL Optimization Agent[/bold cyan]\n"
        "[dim]Offline · Local · Powered by Ollama[/dim]",
        border_style="cyan"
    ))


# --------------------------------------------------------
# --test-connection
# --------------------------------------------------------
@app.command()
def test_connection():
    """Test that the database connection in config.py works."""
    _banner()
    from schema import test_connection as _test
    _test()


# --------------------------------------------------------
# --list
# --------------------------------------------------------
@app.command()
def list_objects():
    """List all tables and views in your database."""
    _banner()
    from schema import list_all_tables, list_all_views

    tables = list_all_tables()
    views  = list_all_views()

    console.print(f"\n[bold]Tables ({len(tables)})[/bold]")
    for t in tables:
        console.print(f"  [green]•[/green] {t}")

    console.print(f"\n[bold]Views ({len(views)})[/bold]")
    for v in views:
        console.print(f"  [cyan]•[/cyan] {v}")


# --------------------------------------------------------
# --schema TABLE_NAME
# --------------------------------------------------------
@app.command()
def schema(table_name: str = typer.Argument(..., help="Table name to inspect")):
    """Show schema, columns, and indexes for a table."""
    _banner()
    from schema import get_schema
    import json

    result = get_schema(table_name)

    console.print(f"\n[bold]Columns[/bold]")
    for col in result["columns"]:
        pk  = " [yellow][PK][/yellow]" if col["primary_key"] == "YES" else ""
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
        console.print("  [yellow]No indexes found — this table has no non-clustered indexes[/yellow]")

    console.print(f"\n[dim]Estimated rows: {result['estimated_row_count']:,}[/dim]"
                  if isinstance(result['estimated_row_count'], int)
                  else f"\n[dim]Row count: unknown[/dim]")


# --------------------------------------------------------
# --view VIEW_NAME
# --------------------------------------------------------
@app.command()
def view(view_name: str = typer.Argument(..., help="View name to inspect")):
    """Show the SQL definition of a view."""
    _banner()
    from schema import get_view_definition

    result = get_view_definition(view_name)

    if "error" in result:
        console.print(f"[red]{result['error']}[/red]")
        return

    console.print(f"\n[bold]Referenced tables:[/bold] {', '.join(result['referenced_tables'])}")
    console.print(f"\n[bold]View Definition:[/bold]\n")
    console.print(result["definition"])


# --------------------------------------------------------
# Placeholder commands (built in later phases)
# --------------------------------------------------------
@app.command()
def analyze(query: str = typer.Argument(..., help="SQL query to optimize")):
    """[Phase 2] Optimize a SQL query."""
    _banner()
    console.print("[yellow]⏳ optimizer not built yet — coming in Phase 2[/yellow]")
    console.print(f"\nQuery received: [dim]{query[:100]}...[/dim]" if len(query) > 100 else f"\nQuery: [dim]{query}[/dim]")


@app.command()
def file(path: str = typer.Argument(..., help="Path to .sql file")):
    """[Phase 2] Optimize a .sql file."""
    _banner()
    console.print(f"[yellow]⏳ file optimizer not built yet — coming in Phase 2[/yellow]")
    console.print(f"File: [dim]{path}[/dim]")


@app.command()
def plan(path: str = typer.Argument(..., help="Path to .sqlplan file")):
    """[Phase 3] Analyze an execution plan XML file."""
    _banner()
    console.print("[yellow]⏳ plan analyzer not built yet — coming in Phase 3[/yellow]")
    console.print(f"Plan file: [dim]{path}[/dim]")


@app.command()
def deploy(
    client: str = typer.Option(..., help="Client name to deploy to")
):
    """[Phase 6] Generate deployment package for a client."""
    _banner()
    console.print(f"[yellow]⏳ deployment packager not built yet — coming in Phase 6[/yellow]")
    console.print(f"Client: [dim]{client}[/dim]")


@app.command()
def new_client(name: str = typer.Argument(..., help="New client name")):
    """[Phase 9] Create a new client workspace from template."""
    _banner()
    console.print(f"[yellow]⏳ multi-client system not built yet — coming in Phase 9[/yellow]")
    console.print(f"Client name: [dim]{name}[/dim]")


# --------------------------------------------------------
# Entry point
# --------------------------------------------------------
if __name__ == "__main__":
    app()
