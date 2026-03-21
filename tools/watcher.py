# ============================================================
# tools/watcher.py
# Nightly schema watcher — takes a snapshot of the database
# schema, diffs it against the previous snapshot, and alerts
# you to any changes that could affect past optimizations.
#
# WHY THIS EXISTS:
#   You spend time optimizing a query for a specific schema.
#   Someone changes a column type, drops an index, adds a column.
#   Your optimization silently breaks — implicit conversions
#   appear, indexes stop being used, queries slow back down.
#   This catches it before your client notices.
#
# HOW IT WORKS:
#   1. Take a full snapshot of all tables, columns, and indexes
#   2. Compare to the previous snapshot (stored as JSON)
#   3. Classify changes by severity (HIGH / MEDIUM / LOW / INFO)
#   4. Cross-reference with history.db — which past runs are affected?
#   5. Save a watch log to runs/watch_YYYY_MM_DD.md
#   6. Auto-commit snapshot to Git
#   7. Print morning alert summary
#
# SEVERITY LEVELS:
#   HIGH   — column type changed, column dropped, index dropped
#            → directly breaks existing optimizations
#   MEDIUM — column added, table dropped, view changed
#            → may affect existing queries
#   LOW    — new table added, index renamed
#            → worth knowing, unlikely to break anything
#   INFO   — row count change, statistics updated
#            → informational only
#
# SNAPSHOT STORAGE:
#   snapshots/schema_YYYY_MM_DD.json     (daily snapshot)
#   snapshots/schema_latest.json         (always the most recent)
#   snapshots/schema_previous.json       (the one before latest)
# ============================================================

import json
import re
from datetime import datetime, date
from pathlib import Path

import pyodbc
from rich.console import Console
from rich.panel import Panel
from rich.rule import Rule
from rich.table import Table

from config import BASE_DIR, DB_CONFIG, ACTIVE_CLIENT

console = Console()

SNAPSHOTS_DIR = Path(BASE_DIR) / "snapshots"


def _ok(msg):   console.print(f"  [green]✓[/green] {msg}")
def _warn(msg): console.print(f"  [yellow]⚠[/yellow]  {msg}")
def _info(msg): console.print(f"  [dim]{msg}[/dim]")
def _fail(msg): console.print(f"  [red]✗[/red] {msg}")


# ============================================================
# DB CONNECTION
# ============================================================

def _get_connection():
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


# ============================================================
# SNAPSHOT: capture full schema state
# ============================================================

def take_snapshot() -> dict:
    """
    Captures the full schema state of the database.

    Returns a dict representing the complete schema — all tables,
    columns (with types), and indexes. This is the baseline for
    comparison on the next run.

    Structure:
        {
          "captured_at": "2026-03-21 07:00:00",
          "database":    "AcmeDev",
          "tables": {
            "measurements": {
              "columns": {
                "id":         {"type": "int",     "nullable": "NO",  "pk": true},
                "machine_id": {"type": "int",     "nullable": "NO",  "pk": false},
                "value":      {"type": "float",   "nullable": "YES", "pk": false},
              },
              "indexes": {
                "IX_measurements_machine": {
                  "type": "NONCLUSTERED", "unique": false,
                  "keys": "machine_id, timestamp", "includes": "value"
                }
              },
              "row_count": 250000
            }
          },
          "views": {
            "vw_dashboard": {"definition_hash": "abc123..."}
          }
        }
    """
    console.print("  [cyan]→ Connecting to SQL Server...[/cyan]")
    conn   = _get_connection()
    cursor = conn.cursor()

    snapshot = {
        "captured_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "database":    DB_CONFIG.get("database", "unknown"),
        "client":      ACTIVE_CLIENT,
        "tables":      {},
        "views":       {},
    }

    # ── Tables ────────────────────────────────────────────
    cursor.execute("""
        SELECT TABLE_NAME
        FROM INFORMATION_SCHEMA.TABLES
        WHERE TABLE_TYPE = 'BASE TABLE'
        ORDER BY TABLE_NAME
    """)
    tables = [row[0] for row in cursor.fetchall()]
    _info(f"Scanning {len(tables)} tables...")

    for table in tables:
        # Columns
        cursor.execute("""
            SELECT
                c.COLUMN_NAME,
                c.DATA_TYPE,
                COALESCE(c.CHARACTER_MAXIMUM_LENGTH, c.NUMERIC_PRECISION, 0) AS size,
                c.IS_NULLABLE,
                CASE WHEN pk.COLUMN_NAME IS NOT NULL THEN 1 ELSE 0 END AS is_pk
            FROM INFORMATION_SCHEMA.COLUMNS c
            LEFT JOIN (
                SELECT ku.COLUMN_NAME
                FROM INFORMATION_SCHEMA.TABLE_CONSTRAINTS tc
                JOIN INFORMATION_SCHEMA.KEY_COLUMN_USAGE ku
                    ON tc.CONSTRAINT_NAME = ku.CONSTRAINT_NAME
                WHERE tc.CONSTRAINT_TYPE = 'PRIMARY KEY'
                  AND tc.TABLE_NAME = ?
            ) pk ON c.COLUMN_NAME = pk.COLUMN_NAME
            WHERE c.TABLE_NAME = ?
            ORDER BY c.ORDINAL_POSITION
        """, table, table)

        columns = {}
        for row in cursor.fetchall():
            columns[row[0]] = {
                "type":     row[1],
                "size":     row[2],
                "nullable": row[3],
                "pk":       bool(row[4]),
            }

        # Indexes
        cursor.execute("""
            SELECT
                i.name,
                i.type_desc,
                i.is_unique,
                STRING_AGG(
                    CASE WHEN ic.is_included_column = 0 THEN c.name END,
                    ', '
                ) WITHIN GROUP (ORDER BY ic.key_ordinal) AS key_cols,
                STRING_AGG(
                    CASE WHEN ic.is_included_column = 1 THEN c.name END,
                    ', '
                ) AS include_cols
            FROM sys.indexes i
            JOIN sys.index_columns ic
                ON i.object_id = ic.object_id AND i.index_id = ic.index_id
            JOIN sys.columns c
                ON ic.object_id = c.object_id AND ic.column_id = c.column_id
            JOIN sys.tables t ON i.object_id = t.object_id
            WHERE t.name = ? AND i.type > 0
            GROUP BY i.name, i.type_desc, i.is_unique
        """, table)

        indexes = {}
        for row in cursor.fetchall():
            indexes[row[0]] = {
                "type":     row[1],
                "unique":   bool(row[2]),
                "keys":     row[3] or "",
                "includes": row[4] or "",
            }

        # Row count estimate
        cursor.execute("""
            SELECT SUM(p.rows)
            FROM sys.tables t
            JOIN sys.partitions p ON t.object_id = p.object_id
            WHERE t.name = ? AND p.index_id IN (0,1)
        """, table)
        row_count = cursor.fetchone()
        row_count = int(row_count[0]) if row_count and row_count[0] else 0

        snapshot["tables"][table] = {
            "columns":   columns,
            "indexes":   indexes,
            "row_count": row_count,
        }

    # ── Views ─────────────────────────────────────────────
    cursor.execute("""
        SELECT o.name, sm.definition
        FROM sys.sql_modules sm
        JOIN sys.objects o ON sm.object_id = o.object_id
        WHERE o.type = 'V'
        ORDER BY o.name
    """)

    import hashlib
    for row in cursor.fetchall():
        view_name = row[0]
        defn      = row[1] or ""
        snapshot["views"][view_name] = {
            "definition_hash": hashlib.md5(defn.encode()).hexdigest(),
            "definition":      defn,
        }

    conn.close()
    _ok(
        f"Snapshot captured — "
        f"{len(snapshot['tables'])} tables · "
        f"{len(snapshot['views'])} views"
    )
    return snapshot


def save_snapshot(snapshot: dict) -> dict:
    """
    Saves snapshot to snapshots/ folder.
    Rotates: latest → previous before saving new one.

    Returns paths dict.
    """
    SNAPSHOTS_DIR.mkdir(parents=True, exist_ok=True)

    today       = date.today().strftime("%Y_%m_%d")
    dated_path  = SNAPSHOTS_DIR / f"schema_{today}.json"
    latest_path = SNAPSHOTS_DIR / "schema_latest.json"
    prev_path   = SNAPSHOTS_DIR / "schema_previous.json"

    # Rotate: latest → previous
    if latest_path.exists():
        latest_path.rename(prev_path)

    # Save new snapshot
    data = json.dumps(snapshot, indent=2, ensure_ascii=False)
    dated_path.write_text(data, encoding="utf-8")
    latest_path.write_text(data, encoding="utf-8")

    return {
        "dated":    str(dated_path),
        "latest":   str(latest_path),
        "previous": str(prev_path),
    }


def load_snapshot(path: str = None) -> dict:
    """
    Load a snapshot from disk.
    Defaults to schema_previous.json (last run).
    """
    p = Path(path) if path else SNAPSHOTS_DIR / "schema_previous.json"
    if not p.exists():
        return {}
    return json.loads(p.read_text(encoding="utf-8"))


# ============================================================
# DIFF: compare two snapshots
# ============================================================

# Change severity classification
SEVERITY = {
    # Column changes
    "column_type_changed":   "HIGH",
    "column_dropped":        "HIGH",
    "column_nullable_changed":"MEDIUM",
    "column_size_changed":   "LOW",
    "column_added":          "LOW",
    # Index changes
    "index_dropped":         "HIGH",
    "index_keys_changed":    "HIGH",
    "index_includes_changed":"MEDIUM",
    "index_added":           "INFO",
    # Table/view changes
    "table_dropped":         "HIGH",
    "table_added":           "INFO",
    "view_changed":          "MEDIUM",
    "view_dropped":          "HIGH",
    "view_added":            "INFO",
}

SEVERITY_ORDER = {"HIGH": 0, "MEDIUM": 1, "LOW": 2, "INFO": 3}


def diff_snapshots(old: dict, new: dict) -> list:
    """
    Compares two schema snapshots and returns a list of changes.

    Each change is a dict:
        {
          "severity":    "HIGH" | "MEDIUM" | "LOW" | "INFO",
          "change_type": "column_type_changed" | ...,
          "object":      "measurements.machine_id",
          "detail":      "int → float",
          "table":       "measurements",
          "affects_optimizations": True | False  (set later)
        }

    Returns list sorted by severity.
    """
    if not old or not new:
        return []

    changes = []

    old_tables = old.get("tables", {})
    new_tables = new.get("tables", {})
    old_views  = old.get("views",  {})
    new_views  = new.get("views",  {})

    # ── Dropped tables ────────────────────────────────────
    for table in old_tables:
        if table not in new_tables:
            changes.append(_change(
                "table_dropped", table,
                f"Table '{table}' no longer exists",
                table=table,
            ))

    # ── New tables ────────────────────────────────────────
    for table in new_tables:
        if table not in old_tables:
            changes.append(_change(
                "table_added", table,
                f"New table '{table}' added",
                table=table,
            ))
            continue  # no point diffing columns of a new table

        old_t = old_tables[table]
        new_t = new_tables[table]

        # ── Column diffs ──────────────────────────────────
        old_cols = old_t.get("columns", {})
        new_cols = new_t.get("columns", {})

        for col, old_def in old_cols.items():
            if col not in new_cols:
                changes.append(_change(
                    "column_dropped", f"{table}.{col}",
                    f"Column '{col}' dropped from '{table}'",
                    table=table,
                ))
                continue

            new_def = new_cols[col]

            if old_def["type"] != new_def["type"]:
                changes.append(_change(
                    "column_type_changed", f"{table}.{col}",
                    f"{old_def['type']} → {new_def['type']}",
                    table=table,
                    extra={
                        "old_type": old_def["type"],
                        "new_type": new_def["type"],
                        "column":   col,
                    }
                ))

            if old_def["nullable"] != new_def["nullable"]:
                changes.append(_change(
                    "column_nullable_changed", f"{table}.{col}",
                    f"nullable: {old_def['nullable']} → {new_def['nullable']}",
                    table=table,
                ))

            if old_def.get("size") != new_def.get("size") and old_def["type"] == new_def["type"]:
                changes.append(_change(
                    "column_size_changed", f"{table}.{col}",
                    f"size: {old_def.get('size')} → {new_def.get('size')}",
                    table=table,
                ))

        for col in new_cols:
            if col not in old_cols:
                changes.append(_change(
                    "column_added", f"{table}.{col}",
                    f"New column '{col}' ({new_cols[col]['type']}) added to '{table}'",
                    table=table,
                ))

        # ── Index diffs ───────────────────────────────────
        old_idx = old_t.get("indexes", {})
        new_idx = new_t.get("indexes", {})

        for idx_name, old_def in old_idx.items():
            if idx_name not in new_idx:
                changes.append(_change(
                    "index_dropped", f"{table}.{idx_name}",
                    f"Index '{idx_name}' dropped from '{table}'",
                    table=table,
                    extra={"index_keys": old_def.get("keys", "")}
                ))
                continue

            new_def = new_idx[idx_name]
            if old_def["keys"] != new_def["keys"]:
                changes.append(_change(
                    "index_keys_changed", f"{table}.{idx_name}",
                    f"Keys changed: [{old_def['keys']}] → [{new_def['keys']}]",
                    table=table,
                ))

            if old_def.get("includes", "") != new_def.get("includes", ""):
                changes.append(_change(
                    "index_includes_changed", f"{table}.{idx_name}",
                    f"INCLUDE columns changed: [{old_def.get('includes','')}] "
                    f"→ [{new_def.get('includes','')}]",
                    table=table,
                ))

        for idx_name in new_idx:
            if idx_name not in old_idx:
                changes.append(_change(
                    "index_added", f"{table}.{idx_name}",
                    f"New index '{idx_name}' added to '{table}'",
                    table=table,
                ))

    # ── View diffs ────────────────────────────────────────
    for view in old_views:
        if view not in new_views:
            changes.append(_change(
                "view_dropped", view,
                f"View '{view}' no longer exists",
                table=view,
            ))
        elif old_views[view]["definition_hash"] != new_views[view]["definition_hash"]:
            changes.append(_change(
                "view_changed", view,
                f"View '{view}' definition was modified",
                table=view,
            ))

    for view in new_views:
        if view not in old_views:
            changes.append(_change(
                "view_added", view,
                f"New view '{view}' added",
                table=view,
            ))

    # Sort by severity
    changes.sort(key=lambda c: SEVERITY_ORDER.get(c["severity"], 99))
    return changes


def _change(
    change_type: str,
    obj:         str,
    detail:      str,
    table:       str = "",
    extra:       dict = None,
) -> dict:
    return {
        "severity":              SEVERITY.get(change_type, "INFO"),
        "change_type":           change_type,
        "object":                obj,
        "detail":                detail,
        "table":                 table,
        "extra":                 extra or {},
        "affects_optimizations": False,  # set by impact analysis
        "affected_run_ids":      [],
    }


# ============================================================
# IMPACT ANALYSIS: cross-reference with history
# ============================================================

def analyze_impact(changes: list) -> list:
    """
    For each HIGH/MEDIUM change, check history.db to see which
    past optimization runs involved the affected table.

    Annotates each change with affects_optimizations and
    affected_run_ids for the watch report.
    """
    try:
        from tools.history import get_history
    except Exception:
        return changes  # history not available — return unchanged

    for change in changes:
        if change["severity"] not in ("HIGH", "MEDIUM"):
            continue

        table = change.get("table", "")
        if not table:
            continue

        try:
            affected_runs = get_history(table_name=table, limit=50)
            if affected_runs:
                change["affects_optimizations"] = True
                change["affected_run_ids"]      = [r["id"] for r in affected_runs]
                change["affected_run_labels"]   = [
                    r.get("label") or r.get("query_preview", "")[:40]
                    for r in affected_runs[:3]
                ]
        except Exception:
            pass

    return changes


# ============================================================
# MAIN: run_watch
# ============================================================

def run_watch(force: bool = False) -> dict:
    """
    Full watch pipeline:
      1. Take today's snapshot
      2. Compare to previous snapshot
      3. Analyze impact on past optimizations
      4. Save watch log
      5. Git commit snapshot
      6. Print summary

    Args:
        force: re-run even if already ran today

    Returns:
        dict with changes list and summary stats

    Usage:
        result = run_watch()
        result = run_watch(force=True)   # force re-run
    """
    console.print()
    console.print(Panel(
        "[bold cyan]Schema Watcher[/bold cyan]\n"
        "[dim]Daily schema diff · Impact analysis · Auto-logged[/dim]",
        border_style="cyan", expand=False,
    ))

    # Check if already ran today
    today_snapshot = SNAPSHOTS_DIR / f"schema_{date.today().strftime('%Y_%m_%d')}.json"
    if today_snapshot.exists() and not force:
        _info(f"Already ran today ({today_snapshot.name})")
        _info("Use --force to re-run")
        return {"already_ran": True}

    # ── Step 1: Load previous snapshot ───────────────────
    console.print("\n[bold cyan]Step 1/5[/bold cyan] — Loading previous snapshot")
    old_snapshot = load_snapshot()
    if old_snapshot:
        prev_date = old_snapshot.get("captured_at", "unknown")[:10]
        _ok(f"Previous snapshot: {prev_date} "
            f"({len(old_snapshot.get('tables',{}))} tables)")
    else:
        _warn("No previous snapshot found — this will be the first baseline")
        _info("No diff will be produced today. Run again tomorrow for changes.")

    # ── Step 2: Take new snapshot ─────────────────────────
    console.print("\n[bold cyan]Step 2/5[/bold cyan] — Taking today's snapshot")
    try:
        new_snapshot = take_snapshot()
    except Exception as e:
        _fail(f"Snapshot failed: {e}")
        return {"error": str(e)}

    paths = save_snapshot(new_snapshot)
    _ok(f"Saved: {Path(paths['dated']).name}")

    # ── Step 3: Diff ──────────────────────────────────────
    console.print("\n[bold cyan]Step 3/5[/bold cyan] — Comparing snapshots")

    if not old_snapshot:
        changes = []
        _info("First run — no diff to produce")
    else:
        changes = diff_snapshots(old_snapshot, new_snapshot)
        if changes:
            high   = sum(1 for c in changes if c["severity"] == "HIGH")
            medium = sum(1 for c in changes if c["severity"] == "MEDIUM")
            low    = sum(1 for c in changes if c["severity"] == "LOW")
            info   = sum(1 for c in changes if c["severity"] == "INFO")
            console.print(
                f"  Found [red]{high} HIGH[/red] · "
                f"[yellow]{medium} MEDIUM[/yellow] · "
                f"[dim]{low} LOW · {info} INFO[/dim]"
            )
        else:
            _ok("No schema changes detected")

    # ── Step 4: Impact analysis ───────────────────────────
    console.print("\n[bold cyan]Step 4/5[/bold cyan] — Analyzing impact on past optimizations")

    if changes:
        changes = analyze_impact(changes)
        affected = sum(1 for c in changes if c.get("affects_optimizations"))
        if affected:
            console.print(
                f"  [red]{affected} change(s) affect previously optimized queries[/red]"
            )
        else:
            _ok("No impact on previous optimizations")
    else:
        _info("No changes to analyze")

    # ── Step 5: Save log + Git commit ─────────────────────
    console.print("\n[bold cyan]Step 5/5[/bold cyan] — Saving watch log")

    log_path = _save_watch_log(changes, new_snapshot, old_snapshot)
    _ok(f"Log saved: {log_path}")

    try:
        from tools.git_manager import commit_schema_watch
        if changes:
            high_changes = [c for c in changes if c["severity"] == "HIGH"]
            summary = (
                f"{len(high_changes)} HIGH changes detected"
                if high_changes
                else f"{len(changes)} changes detected (no HIGH severity)"
            )
        else:
            summary = "no changes detected"
        commit_schema_watch(f"{DB_CONFIG.get('database','db')} — {summary}")
    except Exception as e:
        _warn(f"Git commit skipped: {e}")

    # ── Print alert ───────────────────────────────────────
    _print_watch_alert(changes, new_snapshot)

    return {
        "changes":       changes,
        "total":         len(changes),
        "high":          sum(1 for c in changes if c["severity"] == "HIGH"),
        "medium":        sum(1 for c in changes if c["severity"] == "MEDIUM"),
        "log_path":      log_path,
        "snapshot_date": new_snapshot["captured_at"][:10],
    }


# ============================================================
# WATCH LOG
# ============================================================

def _save_watch_log(changes: list, new_snap: dict, old_snap: dict) -> str:
    """Save a detailed watch report to runs/watch_YYYY_MM_DD.md"""
    runs_dir = Path(BASE_DIR) / "runs"
    runs_dir.mkdir(parents=True, exist_ok=True)

    today    = date.today().strftime("%Y_%m_%d")
    filepath = runs_dir / f"watch_{today}.md"
    ts       = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    db       = DB_CONFIG.get("database", "unknown")

    lines = [
        f"# Schema Watch Report — {date.today().strftime('%Y-%m-%d')}",
        f"**Database:** {db}  ",
        f"**Client:** {ACTIVE_CLIENT}  ",
        f"**Generated:** {ts}",
        f"",
    ]

    if not changes:
        lines += [
            f"## ✅ No Changes Detected",
            f"",
            f"Schema is identical to previous snapshot.",
            f"All {len(new_snap.get('tables', {}))} tables and "
            f"{len(new_snap.get('views', {}))} views unchanged.",
        ]
    else:
        high   = [c for c in changes if c["severity"] == "HIGH"]
        medium = [c for c in changes if c["severity"] == "MEDIUM"]
        low    = [c for c in changes if c["severity"] in ("LOW", "INFO")]

        lines += [
            f"## Summary",
            f"",
            f"| Severity | Count |",
            f"|----------|-------|",
            f"| 🔴 HIGH   | {len(high)} |",
            f"| 🟡 MEDIUM | {len(medium)} |",
            f"| 🟢 LOW/INFO | {len(low)} |",
            f"| **Total** | **{len(changes)}** |",
            f"",
        ]

        if high:
            lines += ["## 🔴 HIGH Severity Changes", ""]
            for c in high:
                lines.append(f"### `{c['object']}`")
                lines.append(f"**Type:** {c['change_type'].replace('_', ' ').title()}  ")
                lines.append(f"**Detail:** {c['detail']}")
                if c.get("affects_optimizations"):
                    lines.append(
                        f"**⚠ Affects optimizations:** Yes — "
                        f"{len(c['affected_run_ids'])} previous run(s) involved this table"
                    )
                    if c.get("affected_run_labels"):
                        lines.append("**Affected runs:**")
                        for lbl in c["affected_run_labels"]:
                            lines.append(f"- {lbl}")
                    lines.append(
                        f"\n**Recommended action:**  \n"
                        f"Run `python agent.py analyze` on affected queries to check for implicit conversions."
                    )
                lines.append("")

        if medium:
            lines += ["## 🟡 MEDIUM Severity Changes", ""]
            for c in medium:
                lines.append(f"- **[{c['change_type'].replace('_',' ').upper()}]** "
                              f"`{c['object']}` — {c['detail']}")
            lines.append("")

        if low:
            lines += ["## 🟢 LOW / INFO Changes", ""]
            for c in low:
                lines.append(f"- **[{c['severity']}]** `{c['object']}` — {c['detail']}")
            lines.append("")

        lines += [
            "## Recommended Actions",
            "",
            "For each HIGH severity change:",
            "",
            "1. Check if any existing indexes on the affected table still work:",
            "   ```bash",
            "   python agent.py schema <table_name>",
            "   ```",
            "2. Re-run optimization on affected queries:",
            "   ```bash",
            "   python agent.py full-run --query \"<affected query>\"",
            "   ```",
            "3. If a column type change caused implicit conversions,",
            "   the optimizer will detect and fix them automatically.",
            "",
        ]

    # Snapshot comparison footer
    if old_snap:
        lines += [
            "---",
            "",
            f"**Previous snapshot:** {old_snap.get('captured_at','?')[:10]} "
            f"({len(old_snap.get('tables',{}))} tables)",
            f"**Current snapshot:**  {new_snap.get('captured_at','?')[:10]} "
            f"({len(new_snap.get('tables',{}))} tables)",
            "",
            "*Generated by SQL Optimization Agent Schema Watcher*",
        ]

    filepath.write_text("\n".join(lines), encoding="utf-8")
    return str(filepath)


# ============================================================
# TERMINAL OUTPUT
# ============================================================

def _print_watch_alert(changes: list, snapshot: dict):
    """Print the morning alert summary."""
    console.print()
    console.print(Rule("[bold cyan]SCHEMA WATCH REPORT[/bold cyan]"))

    if not changes:
        console.print(
            "\n  [bold green]✓ No schema changes[/bold green] — "
            f"all {len(snapshot.get('tables', {}))} tables unchanged"
        )
        return

    high   = [c for c in changes if c["severity"] == "HIGH"]
    medium = [c for c in changes if c["severity"] == "MEDIUM"]
    low    = [c for c in changes if c["severity"] in ("LOW", "INFO")]

    if high:
        console.print(f"\n  [bold red]⚠ {len(high)} HIGH severity change(s)[/bold red]")
        for c in high:
            impacted = (
                f" [red]→ affects {len(c['affected_run_ids'])} past run(s)[/red]"
                if c.get("affects_optimizations") else ""
            )
            console.print(f"  [red]  •[/red] [{c['change_type'].replace('_',' ').upper()}] "
                          f"`{c['object']}` — {c['detail']}{impacted}")

    if medium:
        console.print(f"\n  [yellow]{len(medium)} MEDIUM severity change(s):[/yellow]")
        for c in medium:
            console.print(f"  [yellow]  •[/yellow] `{c['object']}` — {c['detail']}")

    if low:
        console.print(f"\n  [dim]{len(low)} LOW/INFO change(s) — see watch log for details[/dim]")

    affected_total = sum(1 for c in changes if c.get("affects_optimizations"))
    if affected_total:
        console.print(
            f"\n  [bold red]Action required:[/bold red] "
            f"{affected_total} change(s) affect previously optimized queries."
        )
        console.print(
            "  Run: [cyan]python agent.py watch-report[/cyan] for full details"
        )
        console.print(
            "  Then: [cyan]python agent.py full-run --query '...'[/cyan] "
            "to re-optimize affected queries"
        )
    else:
        console.print(
            "\n  [dim]No impact on previous optimizations detected[/dim]"
        )


def print_last_watch_report():
    """Print the most recent watch log to terminal."""
    runs_dir = Path(BASE_DIR) / "runs"
    logs     = sorted(runs_dir.glob("watch_*.md"), reverse=True)

    if not logs:
        console.print("[yellow]No watch logs found. Run: python agent.py watch[/yellow]")
        return

    latest = logs[0]
    console.print(f"[dim]Watch log: {latest.name}[/dim]\n")
    console.print(latest.read_text(encoding="utf-8"))


# ============================================================
# WINDOWS TASK SCHEDULER SETUP
# ============================================================

def generate_scheduler_script() -> str:
    """
    Generates a Windows batch script and Task Scheduler XML
    to run the watcher automatically every morning at 07:00.

    Returns the path to the generated setup files.
    """
    setup_dir = Path(BASE_DIR) / "scheduler"
    setup_dir.mkdir(parents=True, exist_ok=True)

    python_path  = "python"   # user may need to set full path
    agent_path   = str(Path(BASE_DIR) / "agent.py").replace("\\", "\\\\")
    log_path     = str(Path(BASE_DIR) / "runs" / "scheduler.log").replace("\\", "\\\\")

    # ── Batch file ────────────────────────────────────────
    bat_content = f"""@echo off
REM SQL Optimization Agent — Nightly Schema Watcher
REM Runs every morning at 07:00 via Windows Task Scheduler
REM Generated by SQL Optimization Agent

cd /d "{Path(BASE_DIR)}"
echo Running schema watcher at %DATE% %TIME% >> "{log_path}"
{python_path} "{agent_path}" watch >> "{log_path}" 2>&1
echo Watcher complete at %TIME% >> "{log_path}"
echo ---------------------------------------- >> "{log_path}"
"""
    bat_path = setup_dir / "run_watcher.bat"
    bat_path.write_text(bat_content, encoding="utf-8")

    # ── PowerShell registration script ───────────────────
    ps_content = f"""# SQL Optimization Agent — Register Nightly Watcher
# Run this once as Administrator to set up the scheduled task
# Generated by SQL Optimization Agent

$taskName    = "SQLAgentSchemaWatcher"
$taskDesc    = "SQL Optimization Agent — nightly schema diff"
$batPath     = "{str(bat_path).replace(chr(92), chr(92)+chr(92))}"
$triggerTime = "07:00"

# Remove existing task if present
Unregister-ScheduledTask -TaskName $taskName -Confirm:$false -ErrorAction SilentlyContinue

# Create trigger — daily at 07:00
$trigger = New-ScheduledTaskTrigger -Daily -At $triggerTime

# Create action — run the batch file
$action = New-ScheduledTaskAction -Execute "cmd.exe" -Argument "/c `"$batPath`""

# Create settings
$settings = New-ScheduledTaskSettingsSet `
    -ExecutionTimeLimit (New-TimeSpan -Hours 1) `
    -StartWhenAvailable `
    -RunOnlyIfNetworkAvailable:$false

# Register the task (runs as current user)
Register-ScheduledTask `
    -TaskName $taskName `
    -Description $taskDesc `
    -Trigger $trigger `
    -Action $action `
    -Settings $settings `
    -RunLevel Highest `
    -Force

Write-Host "Task '$taskName' registered successfully." -ForegroundColor Green
Write-Host "Watcher will run daily at $triggerTime" -ForegroundColor Cyan
Write-Host "Logs saved to: {log_path}" -ForegroundColor Dim
"""
    ps_path = setup_dir / "register_task.ps1"
    ps_path.write_text(ps_content, encoding="utf-8")

    # ── README ────────────────────────────────────────────
    readme = f"""# Schema Watcher — Scheduler Setup

## Files
- `run_watcher.bat`    — the script Task Scheduler runs
- `register_task.ps1` — registers the task (run once as Admin)

## Setup (one time)
1. Open PowerShell as Administrator
2. Run:
   ```
   Set-ExecutionPolicy RemoteSigned -Scope CurrentUser
   .\\register_task.ps1
   ```
3. Done — watcher runs every morning at 07:00

## Manual run
To run the watcher right now:
    python agent.py watch

## Check logs
    python agent.py watch-report

## Uninstall
    Unregister-ScheduledTask -TaskName "SQLAgentSchemaWatcher" -Confirm:$false
"""
    (setup_dir / "README.md").write_text(readme, encoding="utf-8")

    return str(setup_dir)
