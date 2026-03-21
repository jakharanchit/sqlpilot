# ============================================================
# tools/migrator.py
# Auto-generates numbered migration SQL files after every
# optimization run.
#
# WHY MIGRATIONS:
#   Without this you finish optimizing locally, then have to
#   manually remember and redo every change on the client system.
#   One missed index = client system behaves differently from dev.
#
# HOW IT WORKS:
#   1. Reads the migrations/ folder to find the last number
#   2. Creates the next file: migrations/004_description.sql
#   3. Fills in: date, reason, benchmark proof, SQL to apply,
#      and the rollback SQL to undo it safely
#   4. Records the migration in the registry (migrations/registry.json)
#
# MIGRATION STATES:
#   pending   — generated, not yet applied to any client
#   applied   — confirmed applied to a client system
#   rolled_back — was applied then undone
#
# FILE NAMING:
#   migrations/004_optimize_vw_dashboard.sql
#   migrations/005_add_ix_measurements_machine_date.sql
# ============================================================

import json
import re
from datetime import datetime
from pathlib import Path

from rich.console import Console

from config import MIGRATIONS_DIR, ACTIVE_CLIENT

console = Console()

MIGRATIONS_PATH = Path(MIGRATIONS_DIR)
REGISTRY_PATH   = MIGRATIONS_PATH / "registry.json"


# ============================================================
# REGISTRY — tracks every migration and its status
# ============================================================

def _load_registry() -> dict:
    """Load the migration registry. Creates it if it doesn't exist."""
    MIGRATIONS_PATH.mkdir(parents=True, exist_ok=True)

    if not REGISTRY_PATH.exists():
        registry = {
            "last_number": 0,
            "migrations":  {},
        }
        _save_registry(registry)
        return registry

    with open(REGISTRY_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def _save_registry(registry: dict):
    REGISTRY_PATH.write_text(
        json.dumps(registry, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )


def _next_number() -> int:
    """Get the next migration number, scanning actual files as source of truth."""
    MIGRATIONS_PATH.mkdir(parents=True, exist_ok=True)

    # Scan existing files for highest number
    existing = []
    for f in MIGRATIONS_PATH.glob("*.sql"):
        match = re.match(r"^(\d+)_", f.name)
        if match:
            existing.append(int(match.group(1)))

    return (max(existing) + 1) if existing else 1


def _slug(text: str, max_len: int = 40) -> str:
    """Convert text to a safe filename slug."""
    text = re.sub(r"[^\w\s-]", "", text.lower())
    text = re.sub(r"[\s_-]+", "_", text).strip("_")
    return text[:max_len]


# ============================================================
# MAIN: create_migration
# ============================================================

def create_migration(
    description:     str,
    apply_sql:       list,
    rollback_sql:    list,
    reason:          str   = "",
    before_ms:       float = None,
    after_ms:        float = None,
    improvement_pct: float = None,
    tables_affected: list  = None,
    source_query:    str   = "",
) -> dict:
    """
    Creates a numbered migration SQL file in migrations/.

    Args:
        description:     short name e.g. "optimize vw_dashboard"
        apply_sql:       list of SQL statements to apply (in order)
        rollback_sql:    list of SQL statements to undo (in reverse order)
        reason:          why this change is being made
        before_ms:       benchmark time before (ms)
        after_ms:        benchmark time after (ms)
        improvement_pct: % improvement
        tables_affected: list of table/view names changed
        source_query:    the original query that triggered this migration

    Returns:
        dict with migration metadata

    Usage:
        migration = create_migration(
            description     = "add covering index for machine filter",
            apply_sql       = ["CREATE INDEX IX_measurements_machine ON ..."],
            rollback_sql    = ["DROP INDEX IF EXISTS IX_measurements_machine ON measurements"],
            reason          = "Table Scan on measurements — 847ms avg",
            before_ms       = 847.3,
            after_ms        = 12.1,
            improvement_pct = 98.6,
            tables_affected = ["measurements"],
        )
    """
    number      = _next_number()
    slug        = _slug(description)
    filename    = f"{number:03d}_{slug}.sql"
    filepath    = MIGRATIONS_PATH / filename
    timestamp   = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    date_str    = datetime.now().strftime("%Y-%m-%d")

    # ── Build benchmark block ──────────────────────────────
    if before_ms is not None and after_ms is not None:
        bench_block = (
            f"-- Benchmark: {before_ms}ms → {after_ms}ms "
            f"({improvement_pct}% faster)\n"
        )
    else:
        bench_block = "-- Benchmark: not measured\n"

    # ── Build reason block ────────────────────────────────
    reason_text = reason or "Manual optimization"

    # ── Build tables block ────────────────────────────────
    tables_text = ", ".join(tables_affected) if tables_affected else "unknown"

    # ── Build apply SQL block ─────────────────────────────
    apply_block = "\n\n".join(apply_sql) if apply_sql else "-- No apply SQL provided"

    # ── Build rollback SQL block ──────────────────────────
    rollback_block = (
        "\n\n".join(rollback_sql)
        if rollback_sql
        else "-- No rollback SQL provided — review before applying"
    )

    # ── Build source query block ──────────────────────────
    source_block = ""
    if source_query:
        source_block = (
            f"\n-- Source query that triggered this migration:\n"
            + "\n".join(f"--   {line}" for line in source_query.strip().splitlines())
            + "\n"
        )

    # ── Write the file ────────────────────────────────────
    content = f"""-- ============================================================
-- Migration: {number:03d}
-- Description: {description}
-- Date: {timestamp}
-- Client: {ACTIVE_CLIENT}
-- Tables affected: {tables_text}
-- Reason: {reason_text}
-- {bench_block.strip()}
-- ============================================================
{source_block}
-- ============================================================
-- ROLLBACK — run this section to undo this migration
-- ============================================================

{rollback_block}


-- ============================================================
-- APPLY — run this section to apply this migration
-- ============================================================

{apply_block}


-- ============================================================
-- VERIFY — run after applying to confirm it worked
-- ============================================================

-- Check the object exists
-- (adjust object name and type as appropriate)
SELECT
    name,
    type_desc,
    create_date
FROM sys.objects
WHERE name IN ({", ".join(f"'{t}'" for t in (tables_affected or ["?"]))})
ORDER BY create_date DESC;

-- Check execution plan no longer shows Table Scan
-- (paste your original query here and check the plan tab in SSMS)

-- ============================================================
-- Migration {number:03d} end
-- Generated by SQL Optimization Agent · {date_str}
-- ============================================================
"""

    filepath.write_text(content, encoding="utf-8")

    # ── Update registry ───────────────────────────────────
    registry = _load_registry()
    registry["last_number"] = number
    registry["migrations"][str(number)] = {
        "number":          number,
        "filename":        filename,
        "description":     description,
        "date":            timestamp,
        "client":          ACTIVE_CLIENT,
        "tables_affected": tables_affected or [],
        "reason":          reason_text,
        "before_ms":       before_ms,
        "after_ms":        after_ms,
        "improvement_pct": improvement_pct,
        "status":          "pending",
        "applied_to":      [],
    }
    _save_registry(registry)

    console.print(
        f"  [green]✓[/green] Migration created: "
        f"[cyan]migrations/{filename}[/cyan]"
    )
    if before_ms and after_ms:
        console.print(
            f"  [dim]  {before_ms}ms → {after_ms}ms "
            f"({improvement_pct}% improvement recorded)[/dim]"
        )

    return {
        "number":   number,
        "filename": filename,
        "path":     str(filepath),
        "status":   "pending",
    }


# ============================================================
# EXTRACT: pull SQL from optimizer result
# ============================================================

def migration_from_optimization(
    optimization_result: dict,
    benchmark_result:    dict = None,
) -> dict:
    """
    Convenience wrapper — creates a migration directly from
    the output of optimizer.optimize_query() and optionally
    benchmarker.benchmark_query().

    Args:
        optimization_result: dict returned by optimize_query()
        benchmark_result:    dict returned by benchmark_query() — optional

    Returns:
        migration metadata dict

    Usage:
        opt    = optimize_query(query, schema_list)
        bench  = benchmark_query(original, opt["optimized_query"])
        migration = migration_from_optimization(opt, bench)
    """
    query           = optimization_result.get("original_query", "")
    optimized       = optimization_result.get("optimized_query", "")
    index_scripts   = optimization_result.get("index_scripts", [])
    diagnosis       = optimization_result.get("diagnosis", "")
    schema_list     = optimization_result.get("schema_list", [])

    # Build description from query preview
    query_preview = query.strip().splitlines()[0][:50].strip()
    description   = f"optimize: {query_preview}"

    # Collect apply SQL — optimized query is informational,
    # indexes are the actual DDL changes to apply
    apply_sql = []
    if index_scripts:
        apply_sql.extend(index_scripts)
    if optimized and optimized != query:
        apply_sql.append(
            f"-- Optimized query (reference — not a schema change):\n"
            f"-- Apply this in your application code, not in SQL Server\n"
            + "\n".join(f"-- {line}" for line in optimized.splitlines())
        )

    # Build rollback SQL from index scripts
    rollback_sql = []
    for script in index_scripts:
        # Extract index name and table from CREATE INDEX statement
        match = re.search(
            r"CREATE\s+(?:UNIQUE\s+)?(?:NONCLUSTERED\s+)?INDEX\s+(\w+)\s+ON\s+(\w+)",
            script, re.I
        )
        if match:
            idx_name   = match.group(1)
            table_name = match.group(2)
            rollback_sql.append(
                f"DROP INDEX IF EXISTS {idx_name} ON {table_name};"
            )
        else:
            rollback_sql.append(f"-- Manual rollback needed for:\n-- {script[:100]}")

    # Tables affected
    tables_affected = [s["table_name"] for s in schema_list]

    # Benchmark data
    before_ms       = None
    after_ms        = None
    improvement_pct = None

    if benchmark_result and "error" not in benchmark_result:
        before_ms       = benchmark_result.get("before", {}).get("avg_ms")
        after_ms        = benchmark_result.get("after",  {}).get("avg_ms")
        improvement_pct = benchmark_result.get("improvement_pct")

    # Reason from diagnosis (first 200 chars)
    reason = ""
    if diagnosis:
        first_line = diagnosis.strip().splitlines()[0][:200]
        reason     = first_line

    return create_migration(
        description     = description,
        apply_sql       = apply_sql if apply_sql else ["-- No schema changes — query optimization only"],
        rollback_sql    = rollback_sql if rollback_sql else ["-- No schema changes to roll back"],
        reason          = reason,
        before_ms       = before_ms,
        after_ms        = after_ms,
        improvement_pct = improvement_pct,
        tables_affected = tables_affected,
        source_query    = query,
    )


# ============================================================
# STATUS: list and mark migrations
# ============================================================

def list_migrations(status_filter: str = None) -> list:
    """
    Returns a list of all migrations from the registry.

    Args:
        status_filter: "pending" | "applied" | "rolled_back" | None (all)

    Returns:
        list of migration dicts sorted by number
    """
    registry    = _load_registry()
    migrations  = list(registry["migrations"].values())
    migrations.sort(key=lambda x: x["number"])

    if status_filter:
        migrations = [m for m in migrations if m["status"] == status_filter]

    return migrations


def mark_applied(migration_number: int, client: str = None):
    """
    Mark a migration as applied to a client system.

    Args:
        migration_number: the migration number (e.g. 4)
        client: client name — defaults to ACTIVE_CLIENT

    Usage:
        mark_applied(4, "client_acme")
    """
    registry = _load_registry()
    key      = str(migration_number)

    if key not in registry["migrations"]:
        console.print(f"[red]✗ Migration {migration_number:03d} not found in registry[/red]")
        return False

    client_name = client or ACTIVE_CLIENT
    m           = registry["migrations"][key]

    m["status"] = "applied"
    if client_name not in m["applied_to"]:
        m["applied_to"].append(client_name)
    m["applied_date"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    _save_registry(registry)
    console.print(f"  [green]✓[/green] Migration {migration_number:03d} marked as applied to {client_name}")
    return True


def mark_rolled_back(migration_number: int):
    """Mark a migration as rolled back."""
    registry = _load_registry()
    key      = str(migration_number)

    if key not in registry["migrations"]:
        console.print(f"[red]✗ Migration {migration_number:03d} not found[/red]")
        return False

    registry["migrations"][key]["status"]       = "rolled_back"
    registry["migrations"][key]["rollback_date"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    _save_registry(registry)
    console.print(f"  [yellow]↩[/yellow] Migration {migration_number:03d} marked as rolled back")
    return True


def get_pending_migrations() -> list:
    """Returns all migrations not yet applied to the active client."""
    all_migrations = list_migrations()
    return [
        m for m in all_migrations
        if m["status"] == "pending"
        or ACTIVE_CLIENT not in m.get("applied_to", [])
    ]
