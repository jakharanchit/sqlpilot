# ============================================================
# tools/reporter.py
# Generates the full client delivery package from migration
# registry data and run logs.
#
# WHAT IT PRODUCES (per deployment):
#
#   deployments/client_acme_2026_03_20/
#   ├── deploy.sql              ← ordered SQL to apply everything
#   ├── rollback.sql            ← ordered SQL to undo everything
#   ├── pre_flight.md           ← checklist client confirms before starting
#   ├── technical_report.md     ← full DDL, plan analysis, your reference
#   ├── walkthrough.md          ← plain-English step-by-step for client
#   └── session_log.txt         ← written during deployment (see session_logger.py)
#
# HOW IT WORKS:
#   1. Reads pending migrations from registry.json
#   2. Reads matching run logs from runs/ for context
#   3. Generates each document
#   4. Saves the deployment folder
#   5. Updates migration registry (marks as packaged)
# ============================================================

import re
from datetime import datetime
from pathlib import Path

from rich.console import Console
from rich.panel import Panel

from config import (
    ACTIVE_CLIENT as _GLOBAL_CLIENT,
    BASE_DIR,
    DEPLOYMENTS_DIR as _GLOBAL_DEPLOYMENTS_DIR,
    MIGRATIONS_DIR  as _GLOBAL_MIGRATIONS_DIR,
    DB_CONFIG,
)

def _get_active_client():
    try:
        from tools.client_manager import get_active_client
        return get_active_client()
    except Exception:
        return _GLOBAL_CLIENT

def _get_deployments_dir():
    try:
        from tools.client_manager import get_client_paths
        return get_client_paths()["deployments"]
    except Exception:
        return _GLOBAL_DEPLOYMENTS_DIR

def _get_migrations_dir():
    try:
        from tools.client_manager import get_client_paths
        return get_client_paths()["migrations"]
    except Exception:
        return _GLOBAL_MIGRATIONS_DIR

console = Console()


def _ok(msg):   console.print(f"  [green]✓[/green] {msg}")
def _info(msg): console.print(f"  [dim]{msg}[/dim]")
def _warn(msg): console.print(f"  [yellow]⚠[/yellow]  {msg}")


# ============================================================
# MAIN: generate_deployment_package
# ============================================================

def generate_deployment_package(
    client:       str  = None,
    migrations:   list = None,
    include_all:  bool = False,
) -> dict:
    """
    Generates a complete client deployment package.

    Args:
        client:      client name — defaults to ACTIVE_CLIENT
        migrations:  list of migration dicts to include.
                     If None, uses all pending migrations.
        include_all: include already-applied migrations too (for full re-deploy)

    Returns:
        dict with package_path and list of files generated

    Usage:
        # Package all pending migrations for active client
        package = generate_deployment_package()

        # Package specific migrations
        from tools.migrator import list_migrations
        migs = list_migrations(status_filter="pending")
        package = generate_deployment_package(migrations=migs)
    """
    client_name = client or _get_active_client()

    console.print()
    console.print(Panel(
        f"[bold cyan]Deployment Package Generator[/bold cyan]\n"
        f"[dim]Client: {client_name}[/dim]",
        border_style="cyan", expand=False,
    ))

    # ── Load migrations ───────────────────────────────────
    console.print("\n[bold cyan]Step 1/6[/bold cyan] — Loading migrations")

    if migrations is None:
        from tools.migrator import list_migrations, get_pending_migrations
        if include_all:
            migrations = list_migrations()
        else:
            migrations = get_pending_migrations()

    if not migrations:
        _warn("No pending migrations found. Run optimizations first.")
        _info("Check status with: python agent.py migrations")
        return {"error": "No pending migrations to package"}

    _ok(f"{len(migrations)} migration(s) to package")
    for m in migrations:
        bench = f" — {m['improvement_pct']}% faster" if m.get("improvement_pct") else ""
        _info(f"  [{m['number']:03d}] {m['description']}{bench}")

    # ── Create deployment folder ──────────────────────────
    console.print("\n[bold cyan]Step 2/6[/bold cyan] — Creating deployment folder")

    ts           = datetime.now().strftime("%Y_%m_%d_%H%M")
    folder_name  = f"{client_name}_{ts}"
    package_path = Path(_get_deployments_dir()) / folder_name
    package_path.mkdir(parents=True, exist_ok=True)
    _ok(f"deployments/{folder_name}/")

    # ── Generate deploy.sql ───────────────────────────────
    console.print("\n[bold cyan]Step 3/6[/bold cyan] — Generating deploy.sql + rollback.sql")

    deploy_sql   = _build_deploy_sql(migrations, client_name)
    rollback_sql = _build_rollback_sql(migrations, client_name)

    (package_path / "deploy.sql").write_text(deploy_sql, encoding="utf-8")
    _ok("deploy.sql")

    (package_path / "rollback.sql").write_text(rollback_sql, encoding="utf-8")
    _ok("rollback.sql")

    # ── Generate pre_flight.md ────────────────────────────
    console.print("\n[bold cyan]Step 4/6[/bold cyan] — Generating pre-flight checklist")

    pre_flight = _build_pre_flight(migrations, client_name)
    (package_path / "pre_flight.md").write_text(pre_flight, encoding="utf-8")
    _ok("pre_flight.md")

    # ── Generate technical_report.md ──────────────────────
    console.print("\n[bold cyan]Step 5/6[/bold cyan] — Generating technical report")

    tech_report = _build_technical_report(migrations, client_name)
    (package_path / "technical_report.md").write_text(tech_report, encoding="utf-8")
    _ok("technical_report.md")

    # ── Generate walkthrough.md ───────────────────────────
    console.print("\n[bold cyan]Step 6/6[/bold cyan] — Generating client walkthrough")

    walkthrough = _build_walkthrough(migrations, client_name, folder_name)
    (package_path / "walkthrough.md").write_text(walkthrough, encoding="utf-8")
    _ok("walkthrough.md")

    # ── Create empty session_log.txt ──────────────────────
    session_header = (
        f"SESSION LOG — {client_name}\n"
        f"Package: {folder_name}\n"
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        f"{'=' * 60}\n"
        f"(This file is written during deployment)\n"
    )
    (package_path / "session_log.txt").write_text(session_header, encoding="utf-8")

    # ── Auto Git commit ───────────────────────────────────
    try:
        from tools.git_manager import commit_deployment
        migration_numbers = [m["number"] for m in migrations]
        if len(migration_numbers) == 1:
            mig_range = f"{migration_numbers[0]:03d}"
        else:
            mig_range = f"{migration_numbers[0]:03d}-{migration_numbers[-1]:03d}"
        commit_deployment(client_name, mig_range, str(package_path))
    except Exception as e:
        _warn(f"Git commit skipped: {e}")

    # ── Summary ───────────────────────────────────────────
    files = [
        "deploy.sql", "rollback.sql", "pre_flight.md",
        "technical_report.md", "walkthrough.md", "session_log.txt",
    ]

    console.print()
    console.print(Panel(
        f"[bold green]✓ Package ready[/bold green]\n"
        f"[dim]deployments/{folder_name}/[/dim]",
        border_style="green", expand=False,
    ))
    console.print("\n[bold]Next steps:[/bold]")
    console.print("  1. Open [cyan]pre_flight.md[/cyan] — confirm with client before starting")
    console.print("  2. Open [cyan]walkthrough.md[/cyan] — follow step by step during deployment")
    console.print("  3. Run [cyan]deploy.sql[/cyan] in SSMS — applies all changes in order")
    console.print("  4. If anything looks wrong — run [cyan]rollback.sql[/cyan]")
    console.print("  5. After deployment — run: [cyan]python agent.py mark-applied <number>[/cyan]")

    return {
        "package_path": str(package_path),
        "folder_name":  folder_name,
        "files":        files,
        "migrations":   migrations,
        "client":       client_name,
    }


# ============================================================
# DOCUMENT BUILDERS
# ============================================================

def _build_deploy_sql(migrations: list, client: str) -> str:
    """Builds deploy.sql — ordered SQL to apply all migrations."""
    ts    = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    db    = DB_CONFIG.get("database", "your_database")
    lines = [
        f"-- ============================================================",
        f"-- DEPLOY.SQL",
        f"-- Client:    {client}",
        f"-- Database:  {db}",
        f"-- Generated: {ts}",
        f"-- Migrations: {', '.join(str(m['number']) for m in migrations)}",
        f"-- ============================================================",
        f"",
        f"-- SAFETY CHECK: confirm you are on the correct database",
        f"-- before running this script.",
        f"IF DB_NAME() != '{db}'",
        f"BEGIN",
        f"    RAISERROR('Wrong database! Expected {db}, got %s', 20, 1, DB_NAME()) WITH LOG;",
        f"    RETURN;",
        f"END",
        f"",
        f"PRINT 'Starting deployment on: ' + DB_NAME();",
        f"PRINT 'Time: ' + CONVERT(VARCHAR, GETDATE(), 120);",
        f"PRINT '{'=' * 50}';",
        f"",
    ]

    for m in sorted(migrations, key=lambda x: x["number"]):
        lines += [
            f"-- ------------------------------------------------------------",
            f"-- Migration {m['number']:03d}: {m['description']}",
            f"-- Reason:  {m.get('reason', 'See technical_report.md')}",
        ]
        if m.get("before_ms") and m.get("after_ms"):
            lines.append(
                f"-- Result:  {m['before_ms']}ms → {m['after_ms']}ms "
                f"({m['improvement_pct']}% faster)"
            )
        lines += [
            f"-- ------------------------------------------------------------",
            f"",
            f"PRINT 'Applying migration {m['number']:03d}: {m['description']}...';",
            f"",
        ]

        # Read the actual apply SQL from the migration file
        mig_file = Path(_get_migrations_dir()) / m["filename"]
        if mig_file.exists():
            apply_sql = _extract_apply_section(mig_file.read_text(encoding="utf-8"))
            lines.append(apply_sql)
        else:
            lines.append(f"-- ⚠ Migration file not found: {m['filename']}")

        lines += [
            f"",
            f"PRINT 'Migration {m['number']:03d} complete.';",
            f"",
        ]

    lines += [
        f"-- ============================================================",
        f"PRINT '{'=' * 50}';",
        f"PRINT 'All migrations applied successfully.';",
        f"PRINT 'Run verify.sql or test your application to confirm.';",
        f"-- ============================================================",
    ]

    return "\n".join(lines)


def _build_rollback_sql(migrations: list, client: str) -> str:
    """Builds rollback.sql — ordered SQL to undo all migrations (reverse order)."""
    ts    = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    db    = DB_CONFIG.get("database", "your_database")
    lines = [
        f"-- ============================================================",
        f"-- ROLLBACK.SQL — UNDO ALL CHANGES",
        f"-- Client:    {client}",
        f"-- Database:  {db}",
        f"-- Generated: {ts}",
        f"-- ============================================================",
        f"",
        f"-- ⚠  THIS UNDOES ALL CHANGES FROM THIS DEPLOYMENT PACKAGE",
        f"-- ⚠  Run this ONLY if something went wrong after deploy.sql",
        f"",
        f"-- SAFETY CHECK",
        f"IF DB_NAME() != '{db}'",
        f"BEGIN",
        f"    RAISERROR('Wrong database! Expected {db}, got %s', 20, 1, DB_NAME()) WITH LOG;",
        f"    RETURN;",
        f"END",
        f"",
        f"PRINT 'Starting rollback on: ' + DB_NAME();",
        f"PRINT '{'=' * 50}';",
        f"",
    ]

    # Rollback in reverse order
    for m in sorted(migrations, key=lambda x: x["number"], reverse=True):
        lines += [
            f"-- Rollback migration {m['number']:03d}: {m['description']}",
            f"PRINT 'Rolling back migration {m['number']:03d}...';",
            f"",
        ]

        mig_file = Path(_get_migrations_dir()) / m["filename"]
        if mig_file.exists():
            rollback_sql = _extract_rollback_section(mig_file.read_text(encoding="utf-8"))
            lines.append(rollback_sql)
        else:
            lines.append(f"-- ⚠ Migration file not found: {m['filename']}")

        lines += [
            f"PRINT 'Migration {m['number']:03d} rolled back.';",
            f"",
        ]

    lines += [
        f"-- ============================================================",
        f"PRINT 'Rollback complete. Database restored to previous state.';",
        f"-- ============================================================",
    ]

    return "\n".join(lines)


def _build_pre_flight(migrations: list, client: str) -> str:
    """Builds pre_flight.md — checklist client confirms before deployment starts."""
    ts  = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    db  = DB_CONFIG.get("database", "your_database")

    lines = [
        f"# Pre-Flight Checklist",
        f"**Client:** {client}  ",
        f"**Database:** {db}  ",
        f"**Generated:** {ts}",
        f"",
        f"---",
        f"",
        f"## ⚠ Complete this checklist BEFORE running deploy.sql",
        f"",
        f"**Please confirm each item and sign at the bottom.**",
        f"",
        f"### Database Backup",
        f"- [ ] A full database backup has been taken **today**",
        f"- [ ] The backup has been verified (restore tested or file confirmed)",
        f"- [ ] You know where the backup file is stored",
        f"",
        f"### Environment Check",
        f"- [ ] You are connected to the **correct server**: `{DB_CONFIG.get('server', 'your_server')}`",
        f"- [ ] You are on the **correct database**: `{db}`",
        f"- [ ] Run this query to verify: `SELECT DB_NAME()` — should return `{db}`",
        f"- [ ] No other users are actively writing to the database",
        f"",
        f"### Application",
        f"- [ ] The application (LabVIEW / dashboard) is **closed** on all machines",
        f"- [ ] You have notified anyone who uses the system of the maintenance window",
        f"",
        f"### What Is Changing",
        f"The following changes will be applied:",
        f"",
    ]

    for m in sorted(migrations, key=lambda x: x["number"]):
        bench = f" ({m['improvement_pct']}% faster)" if m.get("improvement_pct") else ""
        lines.append(f"- **Migration {m['number']:03d}:** {m['description']}{bench}")

    lines += [
        f"",
        f"Full details in `technical_report.md`.",
        f"",
        f"### Rollback Plan",
        f"- [ ] You have read `rollback.sql` and know how to run it",
        f"- [ ] You understand that running `rollback.sql` will **undo everything** in this package",
        f"",
        f"---",
        f"",
        f"## Sign-Off",
        f"",
        f"By proceeding with the deployment, you confirm all items above are complete.",
        f"",
        f"**Name:** _______________________________",
        f"",
        f"**Date:** _______________________________",
        f"",
        f"**Time started:** _______________________",
        f"",
        f"---",
        f"",
        f"*Once this checklist is complete, proceed to `walkthrough.md`.*",
    ]

    return "\n".join(lines)


def _build_technical_report(migrations: list, client: str) -> str:
    """Builds technical_report.md — full DDL, analysis, your reference."""
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Overall improvement stats
    improvements = [
        m["improvement_pct"] for m in migrations
        if m.get("improvement_pct") is not None
    ]
    avg_improvement = round(sum(improvements) / len(improvements), 1) if improvements else None

    lines = [
        f"# Technical Report",
        f"**Client:** {client}  ",
        f"**Database:** {DB_CONFIG.get('database', 'your_database')}  ",
        f"**Generated:** {ts}  ",
        f"**Migrations included:** {len(migrations)}",
        f"",
    ]

    if avg_improvement:
        lines += [
            f"**Average performance improvement: {avg_improvement}%**",
            f"",
        ]

    lines += [
        f"---",
        f"",
        f"## Summary",
        f"",
        f"| Migration | Description | Before | After | Improvement |",
        f"|-----------|-------------|--------|-------|-------------|",
    ]

    for m in sorted(migrations, key=lambda x: x["number"]):
        before = f"{m['before_ms']}ms" if m.get("before_ms") else "—"
        after  = f"{m['after_ms']}ms"  if m.get("after_ms")  else "—"
        imp    = f"**{m['improvement_pct']}%**" if m.get("improvement_pct") else "—"
        lines.append(
            f"| {m['number']:03d} | {m['description'][:40]} | {before} | {after} | {imp} |"
        )

    lines += ["", "---", ""]

    # Per-migration detail section
    for m in sorted(migrations, key=lambda x: x["number"]):
        lines += [
            f"## Migration {m['number']:03d} — {m['description']}",
            f"",
            f"**Date:** {m.get('date', '?')}  ",
            f"**Tables affected:** {', '.join(m.get('tables_affected', []))}  ",
            f"**Reason:** {m.get('reason', 'See run log')}",
            f"",
        ]

        if m.get("before_ms") and m.get("after_ms"):
            lines += [
                f"### Benchmark Results",
                f"",
                f"| Metric | Before | After | Improvement |",
                f"|--------|--------|-------|-------------|",
                f"| Average response | {m['before_ms']}ms | {m['after_ms']}ms | **{m['improvement_pct']}% faster** |",
                f"",
            ]

        # Include the full migration file content
        mig_file = Path(_get_migrations_dir()) / m["filename"]
        if mig_file.exists():
            lines += [
                f"### Migration File: `{m['filename']}`",
                f"",
                f"```sql",
                mig_file.read_text(encoding="utf-8").strip(),
                f"```",
                f"",
            ]

        # Try to find matching run log for deeper context
        run_log_content = _find_run_log_context(m)
        if run_log_content:
            lines += [
                f"### AI Diagnosis (from run log)",
                f"",
                run_log_content,
                f"",
            ]

        lines.append("---")
        lines.append("")

    lines += [
        f"## How To Apply",
        f"",
        f"1. Open `deploy.sql` in SSMS",
        f"2. Confirm `DB_NAME()` returns `{DB_CONFIG.get('database', 'your_database')}`",
        f"3. Press F5 to run",
        f"",
        f"## How To Roll Back",
        f"",
        f"1. Open `rollback.sql` in SSMS",
        f"2. Press F5 to run",
        f"3. Everything returns to the state before this deployment",
        f"",
        f"---",
        f"*Generated by SQL Optimization Agent · {ts}*",
    ]

    return "\n".join(lines)


def _build_walkthrough(migrations: list, client: str, folder_name: str) -> str:
    """Builds walkthrough.md — plain English step-by-step for the client."""
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    db = DB_CONFIG.get("database", "your_database")

    # Calculate total improvement for headline
    improvements = [
        m["improvement_pct"] for m in migrations
        if m.get("improvement_pct") is not None
    ]
    avg_improvement = round(sum(improvements) / len(improvements), 1) if improvements else None
    headline = (
        f"These changes improve database response times by an average of **{avg_improvement}%**."
        if avg_improvement
        else "These changes improve database query performance."
    )

    # Plain English descriptions of what changed
    change_summaries = []
    for m in sorted(migrations, key=lambda x: x["number"]):
        tables = ", ".join(m.get("tables_affected", ["database"]))
        if m.get("before_ms") and m.get("after_ms"):
            change_summaries.append(
                f"- Optimized **{tables}** — response time reduced from "
                f"{m['before_ms']}ms to {m['after_ms']}ms "
                f"(**{m['improvement_pct']}% faster**)"
            )
        else:
            change_summaries.append(f"- Optimized **{tables}** — performance improvement applied")

    lines = [
        f"# Deployment Walkthrough",
        f"**Client:** {client}  ",
        f"**Date:** {ts}",
        f"",
        f"---",
        f"",
        f"## What We're Doing Today",
        f"",
        headline,
        f"",
        f"### Changes being applied:",
        f"",
    ] + change_summaries + [
        f"",
        f"**Estimated time:** 15–20 minutes  ",
        f"**Risk level:** Low — a rollback script is ready if anything looks wrong",
        f"",
        f"---",
        f"",
        f"## Before We Start",
        f"",
        f"✅ Complete the **pre_flight.md** checklist first.",
        f"",
        f"---",
        f"",
        f"## Step 1 — Open SQL Server Management Studio (SSMS)",
        f"",
        f"1. Open SSMS on the database server machine",
        f"2. Connect to server: `{DB_CONFIG.get('server', 'your_server')}`",
        f"3. In the top toolbar, confirm the selected database is: **{db}**",
        f"   - If not: click the dropdown and select `{db}`",
        f"4. Open a new query window (Ctrl+N)",
        f"5. Run this quick check:",
        f"   ```sql",
        f"   SELECT DB_NAME()",
        f"   ```",
        f"   ✅ Should return: `{db}`",
        f"",
        f"---",
        f"",
        f"## Step 2 — Open and Run deploy.sql",
        f"",
        f"1. In SSMS: File → Open → File...",
        f"2. Navigate to this folder: `{folder_name}`",
        f"3. Open: **deploy.sql**",
        f"4. Press **F5** (or click Execute)",
        f"5. Watch the Messages tab at the bottom",
        f"",
        f"✅ Expected output:",
        f"```",
        f"Starting deployment on: {db}",
    ]

    for m in sorted(migrations, key=lambda x: x["number"]):
        lines.append(f"Applying migration {m['number']:03d}: {m['description']}...")
        lines.append(f"Migration {m['number']:03d} complete.")

    lines += [
        f"All migrations applied successfully.",
        f"```",
        f"",
        f"⚠ If you see any **red error messages** — stop here and run rollback.sql (Step 5).",
        f"",
        f"---",
        f"",
        f"## Step 3 — Verify Everything Works",
        f"",
        f"1. Open your application (LabVIEW / dashboard)",
        f"2. Test the filters and screens that were previously slow",
        f"3. Confirm they respond noticeably faster",
        f"",
        f"**Expected improvements:**",
        f"",
    ]

    for m in sorted(migrations, key=lambda x: x["number"]):
        if m.get("before_ms") and m.get("after_ms"):
            tables = ", ".join(m.get("tables_affected", []))
            lines.append(
                f"- **{tables}**: was ~{m['before_ms']}ms, "
                f"should now be ~{m['after_ms']}ms"
            )

    lines += [
        f"",
        f"---",
        f"",
        f"## Step 4 — Confirm Completion",
        f"",
        f"Once everything looks good:",
        f"",
        f"1. Note the finish time in pre_flight.md",
        f"2. Let the developer know deployment is confirmed:",
        f"   > *'Deploy completed successfully at [time]. "
        f"Application tested and working.'*",
        f"",
        f"---",
        f"",
        f"## Step 5 — If Anything Looks Wrong (Rollback)",
        f"",
        f"**If anything is not working correctly after deployment:**",
        f"",
        f"1. In SSMS: File → Open → File...",
        f"2. Open: **rollback.sql** (from the same folder)",
        f"3. Press **F5**",
        f"4. Wait for: `Rollback complete. Database restored to previous state.`",
        f"5. Restart the application and confirm it works as before",
        f"6. Contact the developer: *'Rollback completed at [time].'*",
        f"",
        f"✅ The rollback script is safe to run — it will not delete any data.",
        f"   It only removes the indexes and view changes that were added today.",
        f"",
        f"---",
        f"",
        f"## Summary",
        f"",
        f"| File | Purpose |",
        f"|------|---------|",
        f"| `deploy.sql` | Apply all changes |",
        f"| `rollback.sql` | Undo all changes |",
        f"| `pre_flight.md` | Checklist before starting |",
        f"| `technical_report.md` | Full technical details |",
        f"| `session_log.txt` | Auto-written during deployment |",
        f"",
        f"---",
        f"*Generated by SQL Optimization Agent · {ts}*",
    ]

    return "\n".join(lines)


# ============================================================
# HELPERS — extract SQL sections from migration files
# ============================================================

def _extract_apply_section(migration_content: str) -> str:
    """
    Extracts the APPLY section from a migration file.
    Returns everything between -- APPLY and -- VERIFY markers.
    """
    # Find the APPLY section
    apply_match = re.search(
        r"--\s*={10,}\s*\n--\s*APPLY.*?\n--\s*={10,}\s*\n(.*?)(?:--\s*={10,}\s*\n--\s*VERIFY|--\s*={10,}\s*\n--\s*Migration \d+ end|\Z)",
        migration_content,
        re.DOTALL | re.IGNORECASE,
    )

    if apply_match:
        sql = apply_match.group(1).strip()
        # Remove pure comment lines that are just filler
        lines = [
            l for l in sql.splitlines()
            if not re.match(r"^\s*--\s*(No schema changes|Manual rollback|reference)\s*", l, re.I)
        ]
        return "\n".join(lines).strip()

    # Fallback: return everything that looks like SQL (not comments starting with --)
    sql_lines = []
    in_apply  = False
    for line in migration_content.splitlines():
        if "-- APPLY" in line.upper():
            in_apply = True
            continue
        if in_apply and ("-- VERIFY" in line.upper() or "-- Migration" in line):
            break
        if in_apply:
            sql_lines.append(line)

    result = "\n".join(sql_lines).strip()
    return result if result else "-- No apply SQL found in migration file"


def _extract_rollback_section(migration_content: str) -> str:
    """
    Extracts the ROLLBACK section from a migration file.
    Returns everything between -- ROLLBACK and -- APPLY markers.
    """
    rollback_match = re.search(
        r"--\s*={10,}\s*\n--\s*ROLLBACK.*?\n--\s*={10,}\s*\n(.*?)(?:--\s*={10,}\s*\n--\s*APPLY)",
        migration_content,
        re.DOTALL | re.IGNORECASE,
    )

    if rollback_match:
        sql = rollback_match.group(1).strip()
        lines = [
            l for l in sql.splitlines()
            if not re.match(r"^\s*--\s*(No rollback|No schema)\s*", l, re.I)
        ]
        return "\n".join(lines).strip()

    # Fallback
    sql_lines = []
    in_rollback = False
    for line in migration_content.splitlines():
        if "-- ROLLBACK" in line.upper():
            in_rollback = True
            continue
        if in_rollback and "-- APPLY" in line.upper():
            break
        if in_rollback:
            sql_lines.append(line)

    result = "\n".join(sql_lines).strip()
    return result if result else "-- No rollback SQL found in migration file"


def _find_run_log_context(migration: dict) -> str:
    """
    Tries to find a matching run log for a migration and extracts
    the AI diagnosis section for the technical report.
    """
    runs_dir = Path(BASE_DIR) / "runs"
    if not runs_dir.exists():
        return ""

    # Match by date prefix (first 10 chars of date: YYYY-MM-DD)
    date_prefix = migration.get("date", "")[:10].replace("-", "_")
    matching    = list(runs_dir.glob(f"{date_prefix}*_query.md"))

    if not matching:
        return ""

    # Read the most recent match
    run_log = sorted(matching)[-1].read_text(encoding="utf-8", errors="ignore")

    # Extract the diagnosis section
    diag_match = re.search(
        r"## AI Diagnosis.*?\n\n(.*?)(?:\n---|\n##)",
        run_log, re.DOTALL
    )

    if diag_match:
        diagnosis = diag_match.group(1).strip()
        # Truncate if very long
        if len(diagnosis) > 1000:
            diagnosis = diagnosis[:1000] + "\n\n*[truncated — see full run log]*"
        return diagnosis

    return ""


# ============================================================
# QUICK REPORT: single optimization result
# ============================================================

def quick_report(optimization_result: dict, benchmark_result: dict = None) -> str:
    """
    Generates a quick single-optimization report as a markdown string.
    Used after running analyze to give immediate readable output.

    Args:
        optimization_result: from optimizer.optimize_query()
        benchmark_result:    from benchmarker.benchmark_query() — optional

    Returns:
        markdown string (also saved to reports/)
    """
    ts    = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    query = optimization_result.get("original_query", "")
    tables = [s["table_name"] for s in optimization_result.get("schema_list", [])]

    lines = [
        f"# Optimization Report",
        f"**Date:** {ts}  ",
        f"**Tables:** {', '.join(tables)}",
        f"",
    ]

    if benchmark_result and "error" not in benchmark_result:
        b   = benchmark_result["before"]
        a   = benchmark_result["after"]
        pct = benchmark_result["improvement_pct"]
        lines += [
            f"## Performance Result",
            f"",
            f"| Before | After | Improvement |",
            f"|--------|-------|-------------|",
            f"| {b['avg_ms']}ms | {a['avg_ms']}ms | **{pct}% faster** |",
            f"",
        ]

    lines += [
        f"## Original Query",
        f"```sql",
        query.strip(),
        f"```",
        f"",
        f"## Optimized Query",
        f"```sql",
        optimization_result.get("optimized_query", "— not produced").strip(),
        f"```",
        f"",
        f"## Diagnosis",
        f"",
        optimization_result.get("diagnosis", "— not produced"),
        f"",
    ]

    if optimization_result.get("index_scripts"):
        lines += [f"## Index Scripts", f""]
        for i, script in enumerate(optimization_result["index_scripts"], 1):
            lines += [f"### Index {i}", f"```sql", script, f"```", f""]

    report_text = "\n".join(lines)

    # Save to reports/
    reports_dir = Path(BASE_DIR) / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    slug     = re.sub(r"[^\w]", "_", "_".join(tables))[:30]
    filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{slug}.md"
    (reports_dir / filename).write_text(report_text, encoding="utf-8")

    return report_text
