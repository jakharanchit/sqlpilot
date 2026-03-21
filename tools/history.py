# ============================================================
# tools/history.py
# SQLite-backed run history — records every optimization run
# and enables comparison, trend tracking, and regression detection.
#
# WHY HISTORY:
#   Without this you can't answer:
#   - "Has this query improved over time?"
#   - "Which query is still the slowest after all our work?"
#   - "Did a schema change break an optimization we already did?"
#   - "What's our best result ever on vw_dashboard?"
#
# DATABASE: history.db (SQLite — local only, gitignored)
#
# SCHEMA:
#   runs table — one row per optimization run
#   Each row captures: query fingerprint, tables, timing,
#   improvement, migration number, model versions, timestamp.
#
# QUERY FINGERPRINT:
#   A normalized hash of the query (lowercase, stripped whitespace).
#   Lets you match the same logical query across different runs
#   even if whitespace or case changed slightly.
# ============================================================

import hashlib
import re
import sqlite3
from datetime import datetime
from pathlib import Path

from rich.console import Console
from rich.rule import Rule
from rich.table import Table

from config import HISTORY_DB, MODELS, ACTIVE_CLIENT

console = Console()

DB_PATH = Path(HISTORY_DB)


# ============================================================
# DB SETUP
# ============================================================

def _get_conn() -> sqlite3.Connection:
    """Return a SQLite connection, creating the DB and tables if needed."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row   # access columns by name
    _ensure_schema(conn)
    return conn


def _ensure_schema(conn: sqlite3.Connection):
    """Create tables if they don't exist yet."""
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS runs (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp        TEXT    NOT NULL,
            client           TEXT    NOT NULL,
            run_type         TEXT    NOT NULL DEFAULT 'query',
            label            TEXT,
            query_preview    TEXT,
            query_hash       TEXT,
            tables_involved  TEXT,
            before_ms        REAL,
            after_ms         REAL,
            improvement_pct  REAL,
            speedup          REAL,
            row_count        INTEGER,
            index_scripts    INTEGER DEFAULT 0,
            migration_number INTEGER,
            migration_file   TEXT,
            log_path         TEXT,
            model_reasoner   TEXT,
            model_optimizer  TEXT,
            success          INTEGER DEFAULT 1,
            notes            TEXT
        );

        CREATE INDEX IF NOT EXISTS idx_query_hash  ON runs (query_hash);
        CREATE INDEX IF NOT EXISTS idx_timestamp   ON runs (timestamp);
        CREATE INDEX IF NOT EXISTS idx_client      ON runs (client);
        CREATE INDEX IF NOT EXISTS idx_tables      ON runs (tables_involved);
    """)
    conn.commit()


# ============================================================
# FINGERPRINT
# ============================================================

def _fingerprint(query: str) -> str:
    """
    Create a stable hash for a query, ignoring formatting differences.
    Two queries that are logically the same will have the same fingerprint
    even if whitespace, case, or comments differ.
    """
    # Normalize: lowercase, collapse whitespace, strip comments
    normalized = query.lower()
    normalized = re.sub(r"--[^\n]*",     "",  normalized)   # strip line comments
    normalized = re.sub(r"/\*.*?\*/",    "",  normalized, flags=re.DOTALL)  # block comments
    normalized = re.sub(r"\s+",          " ", normalized)   # collapse whitespace
    normalized = normalized.strip()
    return hashlib.md5(normalized.encode()).hexdigest()


# ============================================================
# RECORD: save a run to history
# ============================================================

def record_run(
    query:           str,
    run_type:        str   = "query",
    label:           str   = "",
    tables:          list  = None,
    before_ms:       float = None,
    after_ms:        float = None,
    improvement_pct: float = None,
    speedup:         float = None,
    row_count:       int   = None,
    index_scripts:   int   = 0,
    migration_number: int  = None,
    migration_file:  str   = None,
    log_path:        str   = None,
    success:         bool  = True,
    notes:           str   = "",
) -> int:
    """
    Record a completed run to history.db.

    Called automatically by pipeline.py after every full-run.
    Can also be called manually after individual analyze runs.

    Args:
        query:           the original SQL query
        run_type:        "query" | "view" | "batch" | "workload"
        label:           short name for this run
        tables:          list of table/view names involved
        before_ms:       avg ms before optimization
        after_ms:        avg ms after optimization
        improvement_pct: percentage improvement
        speedup:         speedup multiplier (e.g. 8.5 = 8.5x faster)
        row_count:       rows returned by query
        index_scripts:   number of CREATE INDEX scripts generated
        migration_number: migration number if one was created
        migration_file:  migration filename
        log_path:        path to the run log MD file
        success:         did the pipeline complete successfully
        notes:           any extra notes

    Returns:
        The new run ID (integer)

    Usage:
        run_id = record_run(
            query           = "SELECT * FROM vw_dashboard WHERE machine_id=1",
            tables          = ["measurements"],
            before_ms       = 847.3,
            after_ms        = 12.1,
            improvement_pct = 98.6,
        )
    """
    conn = _get_conn()

    tables_str   = ", ".join(tables) if tables else ""
    query_preview = query.strip().splitlines()[0][:120]
    query_hash    = _fingerprint(query)

    cursor = conn.execute("""
        INSERT INTO runs (
            timestamp, client, run_type, label,
            query_preview, query_hash, tables_involved,
            before_ms, after_ms, improvement_pct, speedup,
            row_count, index_scripts,
            migration_number, migration_file, log_path,
            model_reasoner, model_optimizer,
            success, notes
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        ACTIVE_CLIENT,
        run_type,
        label or "",
        query_preview,
        query_hash,
        tables_str,
        before_ms,
        after_ms,
        improvement_pct,
        speedup,
        row_count,
        index_scripts,
        migration_number,
        migration_file or "",
        log_path or "",
        MODELS.get("reasoner", ""),
        MODELS.get("optimizer", ""),
        1 if success else 0,
        notes or "",
    ))

    conn.commit()
    run_id = cursor.lastrowid
    conn.close()
    return run_id


def record_from_pipeline(pipeline_result: dict) -> int:
    """
    Convenience wrapper — records a run directly from
    the dict returned by pipeline.run_single().

    Usage:
        result = run_single("SELECT ...")
        record_from_pipeline(result)
    """
    bench = pipeline_result.get("benchmark", {}) or {}
    opt   = pipeline_result.get("optimization", {}) or {}
    mig   = pipeline_result.get("migration", {}) or {}

    tables = [
        s["table_name"]
        for s in opt.get("schema_list", [])
    ]

    return record_run(
        query            = pipeline_result.get("query", ""),
        run_type         = "query",
        label            = pipeline_result.get("label", ""),
        tables           = tables,
        before_ms        = bench.get("before", {}).get("avg_ms"),
        after_ms         = bench.get("after",  {}).get("avg_ms"),
        improvement_pct  = bench.get("improvement_pct"),
        speedup          = bench.get("speedup"),
        row_count        = bench.get("after",  {}).get("row_count"),
        index_scripts    = len(opt.get("index_scripts", [])),
        migration_number = mig.get("number"),
        migration_file   = mig.get("filename"),
        log_path         = opt.get("log_path", ""),
        success          = pipeline_result.get("success", False),
    )


# ============================================================
# QUERY: fetch history
# ============================================================

def get_history(
    query:      str  = None,
    table_name: str  = None,
    limit:      int  = 20,
    client:     str  = None,
) -> list:
    """
    Fetch run history, optionally filtered by query or table.

    Args:
        query:      filter by query text or hash (fuzzy match on preview)
        table_name: filter by table/view name
        limit:      max rows to return
        client:     filter by client name (default: all)

    Returns:
        list of dicts (most recent first)

    Usage:
        history = get_history(table_name="vw_dashboard")
        history = get_history(query="machine filter", limit=5)
    """
    conn   = _get_conn()
    params = []
    where  = []

    if query:
        where.append("(query_preview LIKE ? OR label LIKE ?)")
        params.extend([f"%{query}%", f"%{query}%"])

    if table_name:
        where.append("tables_involved LIKE ?")
        params.append(f"%{table_name}%")

    if client:
        where.append("client = ?")
        params.append(client)

    where_clause = f"WHERE {' AND '.join(where)}" if where else ""

    rows = conn.execute(f"""
        SELECT * FROM runs
        {where_clause}
        ORDER BY timestamp DESC
        LIMIT ?
    """, params + [limit]).fetchall()

    conn.close()
    return [dict(row) for row in rows]


def get_trend(query_hash: str = None, table_name: str = None) -> list:
    """
    Returns all runs for a specific query (by hash) or table,
    ordered oldest → newest for trend display.

    Usage:
        # Get trend for a specific query
        runs = get_trend(query_hash="abc123...")

        # Get all runs involving a table
        runs = get_trend(table_name="measurements")
    """
    conn   = _get_conn()
    params = []
    where  = []

    if query_hash:
        where.append("query_hash = ?")
        params.append(query_hash)

    if table_name:
        where.append("tables_involved LIKE ?")
        params.append(f"%{table_name}%")

    where_clause = f"WHERE {' AND '.join(where)}" if where else ""

    rows = conn.execute(f"""
        SELECT * FROM runs
        {where_clause}
        ORDER BY timestamp ASC
    """, params).fetchall()

    conn.close()
    return [dict(row) for row in rows]


def get_regressions(threshold_pct: float = 0.0) -> list:
    """
    Returns runs where the 'optimized' query was actually slower
    (improvement_pct is negative or zero).

    Args:
        threshold_pct: flag runs slower than this % (default 0 = any regression)

    Usage:
        regressions = get_regressions()
        regressions = get_regressions(threshold_pct=-5.0)  # only flag >5% slower
    """
    conn = _get_conn()
    rows = conn.execute("""
        SELECT * FROM runs
        WHERE improvement_pct IS NOT NULL
          AND improvement_pct <= ?
        ORDER BY improvement_pct ASC
    """, (threshold_pct,)).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_top_improvements(limit: int = 10) -> list:
    """Returns the runs with the highest improvement_pct ever recorded."""
    conn = _get_conn()
    rows = conn.execute("""
        SELECT * FROM runs
        WHERE improvement_pct IS NOT NULL
        ORDER BY improvement_pct DESC
        LIMIT ?
    """, (limit,)).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_stats() -> dict:
    """
    Returns overall statistics across all recorded runs.

    Returns dict with:
        total_runs, successful_runs, avg_improvement,
        best_improvement, total_migrations, queries_tracked
    """
    conn  = _get_conn()
    stats = conn.execute("""
        SELECT
            COUNT(*)                                    AS total_runs,
            SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) AS successful_runs,
            AVG(improvement_pct)                        AS avg_improvement,
            MAX(improvement_pct)                        AS best_improvement,
            MIN(improvement_pct)                        AS worst_improvement,
            COUNT(DISTINCT migration_number)             AS total_migrations,
            COUNT(DISTINCT query_hash)                  AS queries_tracked,
            COUNT(DISTINCT tables_involved)             AS tables_touched
        FROM runs
        WHERE improvement_pct IS NOT NULL
    """).fetchone()
    conn.close()
    return dict(stats) if stats else {}


# ============================================================
# COMPARE: two specific runs side by side
# ============================================================

def compare_runs(run_id_a: int, run_id_b: int) -> dict:
    """
    Compare two specific runs side by side.

    Args:
        run_id_a: ID of first run  (use history command to find IDs)
        run_id_b: ID of second run

    Returns:
        dict with both runs and a diff summary

    Usage:
        comparison = compare_runs(1, 15)
    """
    conn  = _get_conn()
    run_a = conn.execute("SELECT * FROM runs WHERE id = ?", (run_id_a,)).fetchone()
    run_b = conn.execute("SELECT * FROM runs WHERE id = ?", (run_id_b,)).fetchone()
    conn.close()

    if not run_a:
        return {"error": f"Run {run_id_a} not found"}
    if not run_b:
        return {"error": f"Run {run_id_b} not found"}

    run_a = dict(run_a)
    run_b = dict(run_b)

    # Build diff
    diff = {}
    for key in ("before_ms", "after_ms", "improvement_pct", "speedup"):
        a_val = run_a.get(key)
        b_val = run_b.get(key)
        if a_val is not None and b_val is not None:
            diff[key] = {
                "run_a": a_val,
                "run_b": b_val,
                "delta": round(b_val - a_val, 2),
                "direction": "better" if b_val > a_val else "worse" if b_val < a_val else "same",
            }

    return {"run_a": run_a, "run_b": run_b, "diff": diff}


# ============================================================
# TERMINAL OUTPUT
# ============================================================

def print_history(runs: list, title: str = "Run History"):
    """Print a formatted history table to the terminal."""
    if not runs:
        console.print("[yellow]No runs found matching your filter.[/yellow]")
        return

    table = Table(
        title=title,
        show_header=True,
        header_style="bold cyan",
        border_style="dim",
    )
    table.add_column("ID",      justify="right",  style="dim",    width=5)
    table.add_column("Date",    style="dim",       min_width=16)
    table.add_column("Label / Query",              min_width=30)
    table.add_column("Tables",  style="cyan",      min_width=18)
    table.add_column("Before",  justify="right",   style="red")
    table.add_column("After",   justify="right",   style="green")
    table.add_column("Impr.",   justify="right",   style="bold")
    table.add_column("Mig.",    justify="center",  style="dim")

    for r in runs:
        label   = r.get("label") or r.get("query_preview", "")[:35]
        before  = f"{r['before_ms']}ms"     if r.get("before_ms")       else "—"
        after   = f"{r['after_ms']}ms"      if r.get("after_ms")        else "—"
        mig     = str(r["migration_number"]) if r.get("migration_number") else "—"

        if r.get("improvement_pct") is not None:
            pct = r["improvement_pct"]
            imp = (
                f"[green]{pct}%[/green]" if pct > 0
                else f"[red]{pct}%[/red]"
            )
        else:
            imp = "—"

        table.add_row(
            str(r["id"]),
            r["timestamp"][:16],
            label,
            r.get("tables_involved", "")[:20],
            before, after, imp, mig,
        )

    console.print(table)


def print_trend(runs: list, label: str = ""):
    """Print a trend view — shows progression of same query over time."""
    if not runs:
        console.print("[yellow]No trend data found.[/yellow]")
        return

    console.print()
    console.print(Rule(f"[bold cyan]Trend: {label}[/bold cyan]"))

    table = Table(show_header=True, header_style="bold cyan", border_style="dim")
    table.add_column("Run",     justify="right", style="dim",   width=5)
    table.add_column("Date",    style="dim",      min_width=16)
    table.add_column("Before",  justify="right",  style="red")
    table.add_column("After",   justify="right",  style="green")
    table.add_column("Improvement",               style="bold")
    table.add_column("Migration", justify="center", style="dim")

    best_after = None

    for r in runs:
        before = f"{r['before_ms']}ms" if r.get("before_ms") else "—"
        after  = f"{r['after_ms']}ms"  if r.get("after_ms")  else "—"
        mig    = str(r["migration_number"]) if r.get("migration_number") else "—"

        if r.get("improvement_pct") is not None:
            pct = r["improvement_pct"]
            imp = f"[green]{pct}%[/green]" if pct > 0 else f"[red]{pct}%[/red]"
        else:
            imp = "—"

        if r.get("after_ms") and (best_after is None or r["after_ms"] < best_after):
            best_after = r["after_ms"]

        table.add_row(str(r["id"]), r["timestamp"][:16], before, after, imp, mig)

    console.print(table)

    # Baseline vs best comparison
    first = next((r for r in runs if r.get("before_ms")), None)
    if first and best_after:
        baseline = first["before_ms"]
        total_pct = round(((baseline - best_after) / baseline) * 100, 1)
        console.print(
            f"\n  Baseline: [red]{baseline}ms[/red]  →  "
            f"Best: [green]{best_after}ms[/green]  "
            f"([bold green]{total_pct}% total improvement[/bold green])"
        )


def print_compare(comparison: dict):
    """Print a side-by-side comparison of two runs."""
    if "error" in comparison:
        console.print(f"[red]✗ {comparison['error']}[/red]")
        return

    a   = comparison["run_a"]
    b   = comparison["run_b"]
    dif = comparison["diff"]

    console.print()
    console.print(Rule("[bold cyan]Run Comparison[/bold cyan]"))

    table = Table(show_header=True, header_style="bold cyan", border_style="dim")
    table.add_column("Metric",       style="dim",    min_width=18)
    table.add_column(f"Run {a['id']} ({a['timestamp'][:10]})", justify="right", style="red")
    table.add_column(f"Run {b['id']} ({b['timestamp'][:10]})", justify="right", style="green")
    table.add_column("Change",       justify="right", style="bold")

    metrics = [
        ("Before (avg)",  "before_ms",       "ms"),
        ("After (avg)",   "after_ms",        "ms"),
        ("Improvement",   "improvement_pct", "%"),
        ("Speedup",       "speedup",         "x"),
    ]

    for label, key, unit in metrics:
        a_val = a.get(key)
        b_val = b.get(key)
        a_str = f"{a_val}{unit}" if a_val is not None else "—"
        b_str = f"{b_val}{unit}" if b_val is not None else "—"

        if key in dif:
            d = dif[key]
            delta = d["delta"]
            if key in ("improvement_pct", "speedup"):
                change = (
                    f"[green]+{delta}{unit}[/green]" if delta > 0
                    else f"[red]{delta}{unit}[/red]"
                )
            else:
                # For ms values, negative delta is better (faster)
                change = (
                    f"[green]{delta}{unit}[/green]" if delta < 0
                    else f"[red]+{delta}{unit}[/red]"
                )
        else:
            change = "—"

        table.add_row(label, a_str, b_str, change)

    # Non-numeric fields
    table.add_row("Label",     a.get("label", "—"),     b.get("label", "—"),     "")
    table.add_row("Migration", str(a.get("migration_number") or "—"),
                               str(b.get("migration_number") or "—"), "")

    console.print(table)

    # Verdict
    if "improvement_pct" in dif:
        d = dif["improvement_pct"]["delta"]
        if d > 0:
            console.print(
                f"\n  [bold green]Run {b['id']} is {d}% better[/bold green] than run {a['id']}"
            )
        elif d < 0:
            console.print(
                f"\n  [bold red]Run {b['id']} is {abs(d)}% worse[/bold red] than run {a['id']}"
            )
        else:
            console.print(f"\n  [yellow]Both runs achieved the same improvement[/yellow]")


def print_stats(stats: dict):
    """Print overall statistics summary."""
    if not stats or not stats.get("total_runs"):
        console.print("[yellow]No history data yet. Run some optimizations first.[/yellow]")
        return

    console.print()
    console.print(Rule("[bold cyan]History Statistics[/bold cyan]"))

    table = Table(show_header=False, box=None, padding=(0, 3))
    table.add_column(style="dim",    min_width=22)
    table.add_column(style="bold")

    table.add_row("Total runs",         str(stats.get("total_runs", 0)))
    table.add_row("Successful runs",    str(stats.get("successful_runs", 0)))
    table.add_row("Queries tracked",    str(stats.get("queries_tracked", 0)))
    table.add_row("Tables touched",     str(stats.get("tables_touched", 0)))
    table.add_row("Total migrations",   str(stats.get("total_migrations", 0)))

    if stats.get("avg_improvement") is not None:
        table.add_row(
            "Avg improvement",
            f"[green]{round(stats['avg_improvement'], 1)}%[/green]"
        )
    if stats.get("best_improvement") is not None:
        table.add_row(
            "Best improvement",
            f"[bold green]{round(stats['best_improvement'], 1)}%[/bold green]"
        )
    if stats.get("worst_improvement") is not None:
        worst = stats["worst_improvement"]
        color = "red" if worst < 0 else "yellow"
        table.add_row(
            "Worst result",
            f"[{color}]{round(worst, 1)}%[/{color}]"
        )

    console.print(table)
