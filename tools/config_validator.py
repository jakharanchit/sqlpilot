# ============================================================
# tools/config_validator.py
# Startup validation — checks everything before any pipeline runs.
#
# V2 PROBLEM:
#   Config problems caused crashes mid-run with cryptic errors.
#   e.g. Wrong server name → crash at Step 2 after 30s of setup.
#   Wrong Ollama URL → crash at Step 5 after AI models were loaded.
#
# V3 SOLUTION:
#   Run all checks upfront, report all problems at once, suggest
#   exact fixes before wasting any time. Like a pre-flight checklist.
#
# WHAT IT CHECKS:
#   1. config.py required fields are set and not placeholders
#   2. SQL Server is reachable and the database exists
#   3. SQL Server login has required permissions
#   4. Ollama is running and required models are pulled
#   5. Required directories exist and are writable
#   6. migrations/registry.json is valid (if it exists)
#   7. history.db schema is current (if it exists)
#   8. Last schema snapshot age (warn if > 7 days old)
#
# USAGE:
#   # Full check — called by 'python agent.py check'
#   from tools.config_validator import run_checks
#   passed = run_checks()
#
#   # Quick check — called at start of every pipeline
#   from tools.config_validator import quick_check
#   quick_check()   # raises ConfigError if critical issues found
# ============================================================

import json
import os
import sqlite3
from datetime import date, datetime
from pathlib import Path

import requests
from rich.console import Console
from rich.table import Table

from config import (
    ACTIVE_CLIENT,
    BASE_DIR,
    DB_CONFIG,
    DEPLOYMENTS_DIR,
    HISTORY_DB,
    MIGRATIONS_DIR,
    MODELS,
    OLLAMA_BASE_URL,
    REPORTS_DIR,
    SNAPSHOTS_DIR,
)
from tools.error_handler import ConfigError, DBConnectionError

console = Console()


# ============================================================
# CHECK RESULT
# ============================================================

class CheckResult:
    """Holds the result of a single validation check."""

    def __init__(self, name: str, category: str):
        self.name     = name
        self.category = category
        self.passed   = False
        self.message  = ""
        self.fix      = ""
        self.critical = False   # if True, pipeline should not run
        self.warning  = False   # if True, can continue but should know

    def ok(self, message: str = "") -> "CheckResult":
        self.passed  = True
        self.message = message
        return self

    def fail(self, message: str, fix: str = "", critical: bool = True) -> "CheckResult":
        self.passed   = False
        self.message  = message
        self.fix      = fix
        self.critical = critical
        return self

    def warn(self, message: str, fix: str = "") -> "CheckResult":
        self.passed  = True
        self.message = message
        self.fix     = fix
        self.warning = True
        return self


# ============================================================
# INDIVIDUAL CHECKS
# ============================================================

def _check_config_fields() -> list:
    """Check that config.py fields are set and not placeholders."""
    results = []

    # Database name
    r = CheckResult("Database name set", "Config")
    db = DB_CONFIG.get("database", "")
    if not db or db == "your_database_name":
        r.fail(
            "DB_CONFIG['database'] is still the placeholder value",
            fix="Open config.py and set 'database' to your actual database name",
        )
    else:
        r.ok(f"Database: {db}")
    results.append(r)

    # Server name
    r = CheckResult("Server name set", "Config")
    server = DB_CONFIG.get("server", "")
    if not server:
        r.fail(
            "DB_CONFIG['server'] is empty",
            fix="Set server to 'localhost' or 'localhost\\\\SQLEXPRESS'",
        )
    else:
        r.ok(f"Server: {server}")
    results.append(r)

    # ODBC driver
    r = CheckResult("ODBC driver set", "Config")
    driver = DB_CONFIG.get("driver", "")
    if not driver:
        r.fail(
            "DB_CONFIG['driver'] is empty",
            fix="Set driver to 'ODBC Driver 17 for SQL Server'",
        )
    else:
        r.ok(f"Driver: {driver}")
    results.append(r)

    # Active client
    r = CheckResult("Active client set", "Config")
    if not ACTIVE_CLIENT or ACTIVE_CLIENT == "client_name":
        r.fail(
            "ACTIVE_CLIENT is not set",
            fix="Set ACTIVE_CLIENT in config.py to your client folder name",
        )
    else:
        r.ok(f"Active client: {ACTIVE_CLIENT}")
    results.append(r)

    # Ollama URL
    r = CheckResult("Ollama URL set", "Config")
    if not OLLAMA_BASE_URL:
        r.fail(
            "OLLAMA_BASE_URL is empty",
            fix="Set OLLAMA_BASE_URL = 'http://localhost:11434'",
        )
    else:
        r.ok(f"Ollama URL: {OLLAMA_BASE_URL}")
    results.append(r)

    return results


def _check_database() -> list:
    """Check SQL Server connectivity and permissions."""
    results = []
    import pyodbc

    # Connection
    r = CheckResult("SQL Server reachable", "Database")
    try:
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
                f"UID={cfg.get('username','')};"
                f"PWD={cfg.get('password','')};"
            )

        conn   = pyodbc.connect(conn_str, timeout=5)
        cursor = conn.cursor()
        cursor.execute("SELECT @@VERSION, DB_NAME()")
        row     = cursor.fetchone()
        version = row[0].split("\n")[0].strip()[:60] if row else "unknown"
        db_name = row[1] if row else "unknown"
        r.ok(f"{db_name} — {version}")
    except pyodbc.Error as e:
        r.fail(
            f"Cannot connect: {e}",
            fix=(
                "1. Check SQL Server is running (Services)\n"
                "     2. Verify server name: try 'localhost\\\\SQLEXPRESS'\n"
                "     3. Check Windows Firewall port 1433"
            ),
        )
        results.append(r)
        return results  # No point running further DB checks

    results.append(r)

    # Table count
    r = CheckResult("Database has tables", "Database")
    try:
        cursor.execute(
            "SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES "
            "WHERE TABLE_TYPE = 'BASE TABLE'"
        )
        count = cursor.fetchone()[0]
        if count == 0:
            r.warn(
                "Database has no tables yet",
                fix="Restore your .bak file or create tables before optimizing",
            )
        else:
            r.ok(f"{count} table(s) found")
    except Exception as e:
        r.fail(str(e))
    results.append(r)

    # VIEW DATABASE STATE permission (needed for execution plans)
    r = CheckResult("VIEW DATABASE STATE permission", "Database")
    try:
        cursor.execute(
            "SELECT HAS_PERMS_BY_NAME(NULL, 'DATABASE', 'VIEW DATABASE STATE')"
        )
        has_perm = cursor.fetchone()[0]
        if has_perm:
            r.ok("Granted")
        else:
            r.fail(
                "Missing VIEW DATABASE STATE permission",
                fix="Grant with: GRANT VIEW DATABASE STATE TO [your_login]",
                critical=False,  # Can still optimize, just no execution plans
            )
            r.warning = True
    except Exception as e:
        r.warn(f"Could not check permission: {e}")
    results.append(r)

    conn.close()
    return results


def _check_ollama() -> list:
    """Check Ollama is running and models are available."""
    results = []

    # Ollama running
    r = CheckResult("Ollama running", "Ollama")
    try:
        response = requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=5)
        response.raise_for_status()
        models_list = [m["name"] for m in response.json().get("models", [])]
        r.ok(f"{len(models_list)} model(s) available")
    except requests.exceptions.ConnectionError:
        r.fail(
            "Ollama is not running",
            fix="Start Ollama: open a terminal and run 'ollama serve'",
        )
        results.append(r)
        return results  # No point checking models if Ollama is down
    except Exception as e:
        r.fail(str(e), fix="Start Ollama with: ollama serve")
        results.append(r)
        return results

    results.append(r)

    # Required models
    for model_key, model_name in MODELS.items():
        r = CheckResult(f"Model: {model_name}", "Ollama")
        if model_name in models_list:
            r.ok("Ready")
        else:
            r.fail(
                f"Model '{model_name}' not pulled",
                fix=f"Pull with: ollama pull {model_name}",
            )
        results.append(r)

    return results


def _check_directories() -> list:
    """Check required directories exist and are writable."""
    results = []

    dirs = {
        "migrations/": MIGRATIONS_DIR,
        "reports/":    REPORTS_DIR,
        "deployments/":DEPLOYMENTS_DIR,
        "snapshots/":  SNAPSHOTS_DIR,
        "runs/":       str(Path(BASE_DIR) / "runs"),
        "logs/":       str(Path(BASE_DIR) / "logs"),
    }

    for label, dir_path in dirs.items():
        r = CheckResult(f"{label} writable", "Directories")
        p = Path(dir_path)
        try:
            p.mkdir(parents=True, exist_ok=True)
            # Test write
            test_file = p / ".write_test"
            test_file.write_text("test", encoding="utf-8")
            test_file.unlink()
            r.ok(f"OK — {p}")
        except PermissionError:
            r.fail(
                f"{p} is not writable",
                fix=f"Check folder permissions for: {p}",
            )
        except Exception as e:
            r.fail(str(e))
        results.append(r)

    return results


def _check_migrations() -> list:
    """Check migration registry is valid JSON."""
    results = []

    r = CheckResult("Migration registry", "Migrations")
    registry_path = Path(MIGRATIONS_DIR) / "registry.json"

    if not registry_path.exists():
        r.ok("No registry yet — will be created on first migration")
        results.append(r)
        return results

    try:
        data = json.loads(registry_path.read_text(encoding="utf-8"))
        count = len(data.get("migrations", {}))
        pending = sum(
            1 for m in data.get("migrations", {}).values()
            if m.get("status") == "pending"
        )
        r.ok(f"{count} migration(s) — {pending} pending")
    except json.JSONDecodeError as e:
        r.fail(
            f"registry.json is corrupted: {e}",
            fix=(
                "1. Open migrations/registry.json in a text editor\n"
                "     2. Fix the JSON syntax error, or delete the file to reset"
            ),
        )
    except Exception as e:
        r.warn(f"Could not read registry: {e}")

    results.append(r)
    return results


def _check_history_db() -> list:
    """Check history.db is accessible and schema is current."""
    results = []

    r = CheckResult("History database", "History")
    history_path = Path(HISTORY_DB)

    if not history_path.exists():
        r.ok("Will be created on first full-run")
        results.append(r)
        return results

    try:
        conn = sqlite3.connect(str(history_path))
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM runs")
        count = cursor.fetchone()[0]
        conn.close()
        r.ok(f"{count} run(s) recorded")
    except sqlite3.OperationalError as e:
        if "no such table" in str(e):
            r.ok("DB exists — tables will be created on first use")
        else:
            r.fail(
                f"history.db error: {e}",
                fix=(
                    "Delete history.db to reset (history will restart from zero):\n"
                    f"     del {HISTORY_DB}"
                ),
            )
    except Exception as e:
        r.warn(f"Could not open history.db: {e}")

    results.append(r)
    return results


def _check_schema_snapshot() -> list:
    """Check last schema snapshot age."""
    results = []

    r = CheckResult("Schema snapshot", "Watcher")
    snapshots_dir = Path(SNAPSHOTS_DIR)
    latest        = snapshots_dir / "schema_latest.json"

    if not latest.exists():
        r.warn(
            "No schema snapshot taken yet",
            fix="Run: python agent.py snapshot  (takes ~5 seconds)",
        )
        results.append(r)
        return results

    try:
        data = json.loads(latest.read_text(encoding="utf-8"))
        captured = data.get("captured_at", "")[:10]
        if captured:
            snapshot_date = date.fromisoformat(captured)
            age_days      = (date.today() - snapshot_date).days
            if age_days > 7:
                r.warn(
                    f"Snapshot is {age_days} days old (last: {captured})",
                    fix="Run: python agent.py snapshot  to refresh",
                )
            else:
                r.ok(f"Last snapshot: {captured} ({age_days} day(s) ago)")
        else:
            r.ok("Snapshot exists")
    except Exception as e:
        r.warn(f"Could not read snapshot: {e}")

    results.append(r)
    return results


# ============================================================
# MAIN: run_checks
# ============================================================

def run_checks(verbose: bool = True) -> bool:
    """
    Run all validation checks and print a formatted report.

    Args:
        verbose: print full results table (default True)
                 set False for quick machine-readable check

    Returns:
        True if all critical checks passed, False otherwise

    Usage:
        from tools.config_validator import run_checks
        passed = run_checks()
        if not passed:
            sys.exit(1)
    """
    all_results = []

    checks = [
        ("Config",     _check_config_fields),
        ("Database",   _check_database),
        ("Ollama",     _check_ollama),
        ("Directories",_check_directories),
        ("Migrations", _check_migrations),
        ("History",    _check_history_db),
        ("Watcher",    _check_schema_snapshot),
    ]

    if verbose:
        console.print("\n[bold cyan]Checking configuration...[/bold cyan]\n")

    for category, check_fn in checks:
        try:
            results = check_fn()
            all_results.extend(results)
        except Exception as e:
            # Check itself crashed — treat as failure
            r = CheckResult(category, category)
            r.fail(f"Check function crashed: {e}")
            all_results.append(r)

    if verbose:
        _print_results_table(all_results)

    # Determine overall pass/fail
    critical_failures = [r for r in all_results if not r.passed and r.critical]
    warnings          = [r for r in all_results if r.warning]

    if verbose:
        if not critical_failures:
            console.print(
                f"\n[bold green]✓ All checks passed[/bold green]"
                + (f" — [yellow]{len(warnings)} warning(s)[/yellow]" if warnings else "")
                + "  [dim]Ready to run.[/dim]"
            )
        else:
            console.print(
                f"\n[bold red]✗ {len(critical_failures)} critical check(s) failed[/bold red] — "
                f"resolve these before running pipelines."
            )

    return len(critical_failures) == 0


def quick_check() -> None:
    """
    Lightweight check run at the start of every pipeline.
    Only checks critical items (DB connection + Ollama).
    Raises ConfigError immediately if anything critical is wrong.
    Runs silently on success.

    Usage:
        from tools.config_validator import quick_check
        quick_check()   # raises ConfigError if not ready
    """
    from tools.app_logger import get_logger
    log = get_logger("config_validator")

    # 1. DB connection
    try:
        import pyodbc
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
                f"UID={cfg.get('username','')};"
                f"PWD={cfg.get('password','')};"
            )
        conn = pyodbc.connect(conn_str, timeout=5)
        conn.close()
        log.debug("Quick check: DB connection OK")
    except Exception as e:
        log.error(f"Quick check: DB connection FAILED — {e}")
        raise DBConnectionError(str(e), server=DB_CONFIG.get("server", ""))

    # 2. Ollama reachable
    try:
        r = requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=3)
        r.raise_for_status()
        log.debug("Quick check: Ollama OK")
    except Exception as e:
        from tools.error_handler import OllamaUnavailableError
        log.warning(f"Quick check: Ollama unavailable — {e}")
        raise OllamaUnavailableError(OLLAMA_BASE_URL)

    # 3. Placeholder config check
    if DB_CONFIG.get("database") == "your_database_name":
        raise ConfigError(
            "DB_CONFIG['database']",
            detail="Still set to placeholder 'your_database_name'",
        )


# ============================================================
# TERMINAL OUTPUT
# ============================================================

def _print_results_table(results: list):
    """Print a formatted results table."""
    table = Table(
        show_header=True,
        header_style="bold cyan",
        border_style="dim",
    )
    table.add_column("Check",    min_width=30)
    table.add_column("Category", style="dim",   min_width=12)
    table.add_column("Status",   justify="center", width=8)
    table.add_column("Detail",   min_width=40)

    for r in results:
        if r.passed and not r.warning:
            status = "[green]✓ pass[/green]"
            detail_color = "dim"
        elif r.warning:
            status = "[yellow]⚠ warn[/yellow]"
            detail_color = "yellow"
        else:
            status = "[red]✗ fail[/red]"
            detail_color = "red"

        detail = r.message[:60]
        if r.fix and not r.passed:
            fix_preview = r.fix.splitlines()[0][:40]
            detail += f"\n[dim]Fix: {fix_preview}[/dim]"

        table.add_row(
            r.name,
            r.category,
            status,
            f"[{detail_color}]{detail}[/{detail_color}]",
        )

    console.print(table)
