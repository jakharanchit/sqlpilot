# ============================================================
# tools/lv_monitor.py
# LabVIEW Query Monitor — reads SQL Server DMVs to capture
# every query LabVIEW sends, with timing and I/O cost.
#
# HOW IT WORKS:
#   SQL Server automatically records every query in
#   sys.dm_exec_query_stats. We filter by program_name
#   = 'National Instruments LabVIEW' to isolate LabVIEW
#   traffic from SSMS and other tools.
#
# ZERO CHANGES REQUIRED TO:
#   - LabVIEW application or VIs
#   - SQL Server configuration
#   - Database schema
#   - Network setup
#
# KEY DMVs USED:
#   sys.dm_exec_sessions      — live connections (who is connected)
#   sys.dm_exec_query_stats   — cached query stats (timing, I/O)
#   sys.dm_exec_sql_text()    — retrieves full query text from handle
#   sys.dm_exec_requests      — queries running right now
#
# LIMITATION:
#   DMV data resets when SQL Server restarts.
#   Use lv-snapshot + lv-snapshot --diff for delta tracking.
#
# LABVIEW APP NAME (confirmed):
#   program_name = 'National Instruments LabVIEW'
# ============================================================

import json
import time
from datetime import datetime
from pathlib import Path

import pyodbc
from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.rule import Rule
from rich.table import Table

from config import DB_CONFIG, BASE_DIR
from tools.app_logger import get_logger
from tools.error_handler import DBConnectionError, DBPermissionError

console = Console()
log     = get_logger("lv_monitor")

# The application name LabVIEW uses — confirmed from your SSMS check
LV_APP_NAME = "National Instruments LabVIEW"

# Path for snapshot files
SNAPSHOTS_PATH = Path(BASE_DIR) / "runs"


# ============================================================
# CONNECTION
# ============================================================

def _get_connection():
    """Connect to SQL Server — requires VIEW SERVER STATE permission."""
    cfg = DB_CONFIG
    if cfg.get("trusted_connection", "no").lower() == "yes":
        conn_str = (
            f"DRIVER={{{cfg['driver']}}};"
            f"SERVER={cfg['server']};"
            f"DATABASE=master;"          # DMVs are in master context
            f"Trusted_Connection=yes;"
        )
    else:
        conn_str = (
            f"DRIVER={{{cfg['driver']}}};"
            f"SERVER={cfg['server']};"
            f"DATABASE=master;"
            f"UID={cfg['username']};"
            f"PWD={cfg['password']};"
        )
    try:
        return pyodbc.connect(conn_str)
    except pyodbc.Error as e:
        raise DBConnectionError(str(e), server=cfg.get("server", ""))


# ============================================================
# DMV QUERIES
# ============================================================

# ── Query 1: Is LabVIEW currently connected? ──────────────
_SQL_LV_SESSION = """
SELECT
    s.session_id,
    s.login_name,
    s.host_name,
    s.program_name,
    s.status,
    s.cpu_time,
    s.total_elapsed_time / 1000        AS elapsed_ms,
    s.reads                            AS logical_reads,
    s.login_time,
    DB_NAME(s.database_id)             AS database_name
FROM sys.dm_exec_sessions s
WHERE s.program_name LIKE ?
  AND s.is_user_process = 1
ORDER BY s.session_id
"""

# ── Query 2: All LabVIEW queries with performance stats ───
# Joins query stats to sessions to isolate LabVIEW traffic.
# Uses CROSS APPLY to resolve sql_handle → query text.
_SQL_LV_QUERY_STATS = """
SELECT TOP (?)
    qs.execution_count                                          AS exec_count,
    CAST(qs.total_elapsed_time / 1000.0
         / NULLIF(qs.execution_count, 0) AS DECIMAL(10,2))    AS avg_ms,
    CAST(qs.min_elapsed_time  / 1000.0   AS DECIMAL(10,2))    AS min_ms,
    CAST(qs.max_elapsed_time  / 1000.0   AS DECIMAL(10,2))    AS max_ms,
    CAST(qs.total_logical_reads * 1.0
         / NULLIF(qs.execution_count, 0) AS DECIMAL(10,1))    AS avg_reads,
    CAST(qs.total_worker_time  / 1000.0
         / NULLIF(qs.execution_count, 0) AS DECIMAL(10,2))    AS avg_cpu_ms,
    qs.last_execution_time,
    qs.creation_time                                           AS plan_created,
    SUBSTRING(qt.text, 1, 500)                                 AS query_preview,
    qt.text                                                    AS full_query,
    qs.plan_handle
FROM sys.dm_exec_query_stats  qs
CROSS APPLY sys.dm_exec_sql_text(qs.sql_handle) qt
WHERE qt.text NOT LIKE '%dm_exec%'       -- exclude monitoring queries themselves
  AND qt.text NOT LIKE '%sys.%'          -- exclude system queries
  AND qs.execution_count > 0
  AND EXISTS (
      SELECT 1
      FROM sys.dm_exec_sessions s
      WHERE s.program_name LIKE ?
        AND s.is_user_process = 1
  )
  AND UPPER(qt.text) NOT LIKE '%WAITFOR%'
ORDER BY avg_ms DESC
"""

# ── Query 3: Queries running RIGHT NOW from LabVIEW ───────
_SQL_LV_ACTIVE = """
SELECT
    r.session_id,
    r.status,
    r.wait_type,
    r.wait_time                        AS wait_ms,
    r.total_elapsed_time               AS elapsed_ms,
    r.cpu_time                         AS cpu_ms,
    r.logical_reads,
    SUBSTRING(qt.text, 1, 300)         AS query_preview
FROM sys.dm_exec_requests r
JOIN sys.dm_exec_sessions s
    ON r.session_id = s.session_id
CROSS APPLY sys.dm_exec_sql_text(r.sql_handle) qt
WHERE s.program_name LIKE ?
  AND s.is_user_process = 1
"""


# ============================================================
# CORE FUNCTIONS
# ============================================================

def get_lv_sessions() -> list:
    """
    Returns all active LabVIEW sessions currently connected.
    Call this to verify LabVIEW is connected before monitoring.

    Returns:
        list of session dicts, empty if LabVIEW is not connected

    Usage:
        sessions = get_lv_sessions()
        if not sessions:
            print("LabVIEW is not connected")
    """
    try:
        conn   = _get_connection()
        cursor = conn.cursor()
        cursor.execute(_SQL_LV_SESSION, f"%{LV_APP_NAME}%")
        rows   = cursor.fetchall()
        conn.close()

        return [
            {
                "session_id":    row[0],
                "login_name":    row[1],
                "host_name":     row[2],
                "program_name":  row[3],
                "status":        row[4],
                "elapsed_ms":    row[6],
                "logical_reads": row[7],
                "login_time":    str(row[8])[:19] if row[8] else "",
                "database_name": row[9],
            }
            for row in rows
        ]
    except DBConnectionError:
        raise
    except pyodbc.Error as e:
        # VIEW SERVER STATE permission missing
        if "permission" in str(e).lower() or "8097" in str(e):
            raise DBPermissionError(
                operation = "VIEW SERVER STATE",
                detail    = str(e),
            )
        raise DBConnectionError(str(e))


def get_lv_queries(limit: int = 20) -> list:
    """
    Returns LabVIEW query performance stats from the DMV cache.
    Results are sorted by avg_ms descending — slowest first.

    Args:
        limit: max number of queries to return (default 20)

    Returns:
        list of query stat dicts with:
            exec_count   — how many times LabVIEW ran this query
            avg_ms       — average execution time in milliseconds
            min_ms       — fastest execution
            max_ms       — slowest execution
            avg_reads    — average logical reads (I/O cost)
            avg_cpu_ms   — average CPU time
            query_preview— first 500 chars of query text
            full_query   — complete query text
            last_execution_time

    Usage:
        queries = get_lv_queries(limit=10)
        for q in queries:
            print(f"{q['avg_ms']}ms — {q['query_preview'][:60]}")
    """
    try:
        conn   = _get_connection()
        cursor = conn.cursor()
        cursor.execute(_SQL_LV_QUERY_STATS, limit, f"%{LV_APP_NAME}%")
        rows   = cursor.fetchall()
        conn.close()

        return [
            {
                "exec_count":     row[0],
                "avg_ms":         float(row[1] or 0),
                "min_ms":         float(row[2] or 0),
                "max_ms":         float(row[3] or 0),
                "avg_reads":      float(row[4] or 0),
                "avg_cpu_ms":     float(row[5] or 0),
                "last_run":       str(row[6])[:19] if row[6] else "",
                "plan_created":   str(row[7])[:19] if row[7] else "",
                "query_preview":  (row[8] or "").strip(),
                "full_query":     (row[9] or "").strip(),
            }
            for row in rows
        ]

    except DBConnectionError:
        raise
    except DBPermissionError:
        raise
    except pyodbc.Error as e:
        if "permission" in str(e).lower():
            raise DBPermissionError("VIEW SERVER STATE", str(e))
        raise DBConnectionError(str(e))


def get_lv_active() -> list:
    """
    Returns queries LabVIEW is running RIGHT NOW.
    Empty list if LabVIEW is idle.

    Usage:
        active = get_lv_active()
        if active:
            print(f"LabVIEW is currently executing: {active[0]['query_preview']}")
    """
    try:
        conn   = _get_connection()
        cursor = conn.cursor()
        cursor.execute(_SQL_LV_ACTIVE, f"%{LV_APP_NAME}%")
        rows   = cursor.fetchall()
        conn.close()

        return [
            {
                "session_id":    row[0],
                "status":        row[1],
                "wait_type":     row[2] or "",
                "wait_ms":       row[3] or 0,
                "elapsed_ms":    row[4] or 0,
                "cpu_ms":        row[5] or 0,
                "logical_reads": row[6] or 0,
                "query_preview": (row[7] or "").strip(),
            }
            for row in rows
        ]
    except Exception:
        return []


# ============================================================
# SNAPSHOT — point-in-time capture for delta tracking
# ============================================================

def take_snapshot(label: str = "") -> dict:
    """
    Captures a point-in-time snapshot of all LabVIEW query stats.
    Use two snapshots (before/after a LabVIEW session) to see
    exactly which queries ran during that window.

    Args:
        label: optional label e.g. "before_dashboard_test"

    Returns:
        snapshot dict — also saved to runs/lv_snapshot_*.json

    Usage:
        snap1 = take_snapshot("before")
        # ... use LabVIEW dashboard ...
        snap2 = take_snapshot("after")
        delta = diff_snapshots(snap1, snap2)
    """
    queries   = get_lv_queries(limit=100)
    sessions  = get_lv_sessions()
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    snapshot = {
        "timestamp":  timestamp,
        "label":      label,
        "sessions":   sessions,
        "queries":    queries,
        "query_count":len(queries),
        "lv_connected": len(sessions) > 0,
    }

    # Save to disk
    SNAPSHOTS_PATH.mkdir(parents=True, exist_ok=True)
    ts_slug  = datetime.now().strftime("%Y%m%d_%H%M%S")
    lbl_slug = label.replace(" ", "_") if label else "snap"
    snap_file = SNAPSHOTS_PATH / f"lv_snapshot_{ts_slug}_{lbl_slug}.json"

    snap_file.write_text(
        json.dumps(snapshot, indent=2, default=str),
        encoding="utf-8",
    )

    log.info(f"LV SNAPSHOT: {len(queries)} queries captured → {snap_file.name}")
    return snapshot


def diff_snapshots(snap_before: dict, snap_after: dict) -> list:
    """
    Compares two LV snapshots and returns queries that are NEW
    or CHANGED (more executions, slower) in the after snapshot.

    This tells you exactly which queries ran during a LabVIEW
    session between the two snapshot times.

    Args:
        snap_before: snapshot taken before LabVIEW session
        snap_after:  snapshot taken after LabVIEW session

    Returns:
        list of dicts with change_type: "new" | "more_executions" | "slower"

    Usage:
        before = take_snapshot("session start")
        # use LabVIEW...
        after  = take_snapshot("session end")
        changes = diff_snapshots(before, after)
    """
    # Index before queries by preview
    before_map = {
        q["query_preview"][:100]: q
        for q in snap_before.get("queries", [])
    }

    changes = []
    for q in snap_after.get("queries", []):
        key    = q["query_preview"][:100]
        before = before_map.get(key)

        if before is None:
            # Brand new query — appeared during this session
            changes.append({
                **q,
                "change_type":  "new",
                "exec_delta":   q["exec_count"],
                "ms_delta":     0,
            })
        elif q["exec_count"] > before["exec_count"]:
            exec_delta = q["exec_count"] - before["exec_count"]
            ms_delta   = round(q["avg_ms"] - before["avg_ms"], 2)
            changes.append({
                **q,
                "change_type":  "more_executions" if ms_delta <= 5 else "slower",
                "exec_delta":   exec_delta,
                "ms_delta":     ms_delta,
                "before_avg_ms":before["avg_ms"],
            })

    # Sort: new first, then by avg_ms descending
    changes.sort(key=lambda x: (
        0 if x["change_type"] == "new" else 1,
        -x["avg_ms"]
    ))
    return changes


def export_to_sql_files(queries: list, output_dir: str = None) -> list:
    """
    Exports LabVIEW queries to .sql files in queries/ folder,
    ready for python agent.py full-run --folder.

    Cleans up queries — removes SET statements, DECLARE noise,
    and other connection overhead LabVIEW adds.

    Args:
        queries:    list from get_lv_queries()
        output_dir: output folder (default: queries/ in project root)

    Returns:
        list of file paths created

    Usage:
        queries = get_lv_queries()
        files   = export_to_sql_files(queries)
        # Then run: python agent.py full-run --folder queries/
    """
    import re

    out_dir = Path(output_dir or (Path(BASE_DIR) / "queries"))
    out_dir.mkdir(parents=True, exist_ok=True)

    files_created = []

    for i, q in enumerate(queries, 1):
        full_query = q.get("full_query", "").strip()
        if not full_query:
            continue

        # Clean up LabVIEW connection overhead
        cleaned = _clean_lv_query(full_query)
        if not cleaned:
            continue

        # Build a safe filename from the query preview
        preview  = q.get("query_preview", f"query_{i}")[:40]
        slug     = re.sub(r"[^\w\s]", "", preview.lower())
        slug     = re.sub(r"\s+", "_", slug).strip("_")[:30]
        filename = f"{i:02d}_{slug}.sql"
        filepath = out_dir / filename

        # Add metadata header
        content = (
            f"-- LabVIEW Query Export\n"
            f"-- Executions: {q['exec_count']}\n"
            f"-- Avg time:   {q['avg_ms']}ms\n"
            f"-- Avg reads:  {q['avg_reads']}\n"
            f"-- Last run:   {q['last_run']}\n"
            f"-- Exported:   {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"\n"
            f"{cleaned}\n"
        )

        filepath.write_text(content, encoding="utf-8")
        files_created.append(str(filepath))
        log.info(f"LV EXPORT: {filename} ({q['avg_ms']}ms avg, {q['exec_count']} runs)")

    return files_created


def _clean_lv_query(sql: str) -> str:
    """
    Strips LabVIEW connection overhead from a captured query.
    LabVIEW sometimes prepends SET statements and DECLARE blocks
    that are connection setup, not the actual query.
    """
    import re

    lines        = sql.strip().splitlines()
    clean_lines  = []
    skip_prefixes = (
        "SET NOCOUNT",
        "SET ANSI",
        "SET QUOTED",
        "SET CONCAT",
        "SET ARITHABORT",
        "SET TRANSACTION",
        "SET LOCK_TIMEOUT",
        "DECLARE @",
        "EXEC sp_executesql",
    )

    for line in lines:
        stripped = line.strip().upper()
        if any(stripped.startswith(p) for p in skip_prefixes):
            continue
        clean_lines.append(line)

    result = "\n".join(clean_lines).strip()
    # If nothing left after cleaning, return original
    return result if result else sql.strip()


# ============================================================
# LIVE MONITOR — polling display
# ============================================================

def run_live_monitor(
    interval_s:  int = 30,
    limit:       int = 10,
    threshold_ms:float = 0,
) -> None:
    """
    Live monitor that polls SQL Server every interval_s seconds
    and displays a refreshing table of LabVIEW query performance.

    Press Ctrl+C to exit.

    Args:
        interval_s:   polling interval in seconds (default 30)
        limit:        max queries to display (default 10)
        threshold_ms: only show queries slower than this (0 = show all)

    Usage:
        run_live_monitor()
        run_live_monitor(interval_s=10, threshold_ms=100)
    """
    console.print(Panel(
        f"[bold cyan]LabVIEW Query Monitor[/bold cyan]\n"
        f"[dim]Polling every {interval_s}s · "
        f"Filter: {'>' + str(threshold_ms) + 'ms' if threshold_ms else 'all queries'} · "
        f"Ctrl+C to stop[/dim]",
        border_style="cyan", expand=False,
    ))

    # Check LabVIEW is connected
    sessions = get_lv_sessions()
    if not sessions:
        console.print(
            "\n[yellow]⚠ LabVIEW is not currently connected to SQL Server[/yellow]"
        )
        console.print(
            "[dim]  Open your LabVIEW dashboard and connect it to the database first[/dim]\n"
        )
    else:
        for s in sessions:
            console.print(
                f"[green]✓ LabVIEW connected[/green]  "
                f"[dim]session {s['session_id']} · {s['host_name']} · "
                f"{s['database_name']} · since {s['login_time']}[/dim]"
            )

    try:
        poll_count = 0
        while True:
            poll_count += 1
            timestamp  = datetime.now().strftime("%H:%M:%S")

            queries = get_lv_queries(limit=limit)

            if threshold_ms:
                queries = [q for q in queries if q["avg_ms"] >= threshold_ms]

            # Check for actively running queries
            active = get_lv_active()

            _print_monitor_table(queries, active, timestamp, poll_count)

            # Suggest optimizations for slow queries
            if queries:
                slowest = queries[0]
                if slowest["avg_ms"] > 500:
                    console.print(
                        f"\n  [yellow]⚠ Slowest query: {slowest['avg_ms']}ms avg "
                        f"({slowest['exec_count']} executions)[/yellow]"
                    )
                    console.print(
                        f"  [dim]  Run: python agent.py full-run --query "
                        f'"{slowest["query_preview"][:80]}" --safe[/dim]'
                    )

            console.print(
                f"\n[dim]  Next refresh in {interval_s}s · "
                f"[cyan]Ctrl+C[/cyan] to stop · "
                f"[cyan]python agent.py lv-export[/cyan] to save queries[/dim]"
            )

            time.sleep(interval_s)

    except KeyboardInterrupt:
        console.print("\n\n[dim]Monitor stopped.[/dim]")
        log.info("LV MONITOR: stopped by user")


def _print_monitor_table(
    queries:    list,
    active:     list,
    timestamp:  str,
    poll_count: int,
):
    """Print the live monitor table."""
    console.print()
    console.print(Rule(
        f"[bold cyan]LabVIEW Query Monitor[/bold cyan]  "
        f"[dim]{timestamp}  poll #{poll_count}[/dim]"
    ))

    if not queries:
        console.print(
            "\n  [dim]No LabVIEW queries in SQL Server cache yet.\n"
            "  Use the LabVIEW dashboard to trigger some queries.[/dim]\n"
        )
        return

    # Active query indicator
    if active:
        for a in active:
            console.print(
                f"  [bold yellow]● RUNNING NOW[/bold yellow]  "
                f"[dim]{a['query_preview'][:70]}  "
                f"({a['elapsed_ms']}ms elapsed)[/dim]"
            )
        console.print()

    # Main stats table
    table = Table(
        show_header=True,
        header_style="bold cyan",
        border_style="dim",
        expand=False,
    )
    table.add_column("#",          justify="right", style="dim",   width=3)
    table.add_column("Avg ms",     justify="right", width=8)
    table.add_column("Min",        justify="right", style="dim",   width=6)
    table.add_column("Max",        justify="right", style="dim",   width=7)
    table.add_column("Runs",       justify="right", style="dim",   width=6)
    table.add_column("Reads/run",  justify="right", style="dim",   width=10)
    table.add_column("Last run",   style="dim",     width=19)
    table.add_column("Query",      min_width=40)

    for i, q in enumerate(queries, 1):
        avg_ms = q["avg_ms"]

        # Colour-code by speed
        if avg_ms >= 1000:
            ms_str = f"[bold red]{avg_ms}[/bold red]"
        elif avg_ms >= 200:
            ms_str = f"[yellow]{avg_ms}[/yellow]"
        else:
            ms_str = f"[green]{avg_ms}[/green]"

        # Truncate query preview — strip whitespace and newlines
        preview = " ".join(q["query_preview"].split())[:65]

        table.add_row(
            str(i),
            ms_str,
            f"{q['min_ms']}",
            f"{q['max_ms']}",
            str(q["exec_count"]),
            f"{q['avg_reads']:.0f}",
            q["last_run"][:16],
            f"[dim]{preview}[/dim]",
        )

    console.print(table)


# ============================================================
# ONE-SHOT SNAPSHOT REPORT
# ============================================================

def print_snapshot_report(queries: list, sessions: list):
    """Print a formatted one-shot snapshot report."""
    console.print()
    console.print(Panel(
        "[bold cyan]LabVIEW Query Snapshot[/bold cyan]\n"
        f"[dim]{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}[/dim]",
        border_style="cyan", expand=False,
    ))

    if sessions:
        for s in sessions:
            console.print(
                f"\n  [green]● LabVIEW connected[/green]  "
                f"[dim]session {s['session_id']} on {s['host_name']} "
                f"→ {s['database_name']} (since {s['login_time']})[/dim]"
            )
    else:
        console.print("\n  [yellow]⚠ LabVIEW not currently connected[/yellow]")
        console.print(
            "  [dim]Historical query data may still be shown "
            "from before the last SQL Server restart[/dim]"
        )

    if not queries:
        console.print(
            "\n  [dim]No LabVIEW queries found in SQL Server cache.\n"
            "  If LabVIEW has been running, try using the dashboard "
            "to trigger some queries first.[/dim]"
        )
        return

    console.print(
        f"\n  [dim]Found {len(queries)} query/queries in cache, "
        f"sorted by avg response time[/dim]"
    )

    _print_monitor_table(queries, [], datetime.now().strftime("%H:%M:%S"), 1)

    # Summary stats
    total_executions = sum(q["exec_count"] for q in queries)
    slowest          = queries[0]["avg_ms"]
    fastest          = queries[-1]["avg_ms"]

    console.print(f"\n  [bold]Summary[/bold]")
    console.print(f"  Total queries tracked:    {len(queries)}")
    console.print(f"  Total executions:         {total_executions:,}")
    console.print(f"  Slowest avg:              [red]{slowest}ms[/red]")
    console.print(f"  Fastest avg:              [green]{fastest}ms[/green]")

    slow_count = sum(1 for q in queries if q["avg_ms"] > 500)
    if slow_count:
        console.print(
            f"\n  [yellow]⚠ {slow_count} query/queries averaging >500ms[/yellow]"
        )
        console.print(
            "  [dim]Run: python agent.py lv-export to save these for optimization[/dim]"
        )
    else:
        console.print("\n  [green]✓ All queries under 500ms[/green]")
