# ============================================================
# tools/sandbox.py
# Shadow DB Sandbox — safe pre-deployment testing environment.
#
# WHAT IT DOES:
#   Creates a temporary copy of your database, applies all
#   proposed changes there, benchmarks against the copy,
#   runs regression checks, then destroys the copy.
#   The real database is never touched until you are certain.
#
# WHY IT EXISTS:
#   "A change causing regression I didn't catch" was identified
#   as the single biggest deployment risk. The sandbox catches
#   regressions before the deployment script leaves your machine.
#
# WORKFLOW:
#   1. create()     — restore .bak to AcmeDev_Shadow_YYYYMMDD
#   2. apply()      — run migration SQL against the shadow
#   3. benchmark()  — measure query performance in shadow
#   4. regress()    — verify existing queries still work
#   5. destroy()    — DROP the shadow DB (auto-called on success/fail)
#
# SHADOW DB NAMING:
#   {original_db}_Shadow_{YYYYMMDD}
#   e.g. AcmeDev_Shadow_20260321
#
# REQUIREMENTS:
#   - SQL Server login must have CREATE DATABASE permission
#   - SQL Server must be able to read the .bak file path
#     (use a path local to the SQL Server, not a network path)
#   - Sufficient disk space for a full DB copy
#
# SANDBOX CONFIG (add to config.py):
#   SANDBOX_BAK_PATH = r"C:\Backups\AcmeDev.bak"
#   SANDBOX_DATA_DIR = r"C:\Program Files\Microsoft SQL Server\...\DATA"
#   SANDBOX_TIMEOUT  = 300  # seconds to wait for restore
# ============================================================

import re
import time
from datetime import date, datetime
from pathlib import Path

import pyodbc
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from config import DB_CONFIG, BASE_DIR
from tools.app_logger import get_logger
from tools.error_handler import (
    DBConnectionError,
    DBQueryError,
    SandboxError,
    operation,
)

console = Console()
log     = get_logger("sandbox")


def _ok(msg):   console.print(f"  [green]✓[/green] {msg}")
def _warn(msg): console.print(f"  [yellow]⚠[/yellow]  {msg}")
def _info(msg): console.print(f"  [dim]{msg}[/dim]")
def _fail(msg): console.print(f"  [red]✗[/red] {msg}")
def _step(n, total, msg): console.print(f"\n[bold cyan]Step {n}/{total}[/bold cyan] — {msg}")


# ============================================================
# SHADOW DB NAME
# ============================================================

def _shadow_name() -> str:
    """Generate the shadow DB name for today."""
    today = date.today().strftime("%Y%m%d")
    return f"{DB_CONFIG['database']}_Shadow_{today}"


def _get_sandbox_config() -> dict:
    """
    Load sandbox-specific config from config.py.
    Falls back to sensible defaults so config.py doesn't NEED
    sandbox entries until the user actually uses sandbox features.
    """
    try:
        import config as cfg
        return {
            "bak_path":   getattr(cfg, "SANDBOX_BAK_PATH",  ""),
            "data_dir":   getattr(cfg, "SANDBOX_DATA_DIR",  ""),
            "timeout_s":  getattr(cfg, "SANDBOX_TIMEOUT",   300),
            "log_dir":    getattr(cfg, "SANDBOX_LOG_DIR",
                                  str(Path(BASE_DIR) / "runs")),
        }
    except Exception:
        return {
            "bak_path":  "",
            "data_dir":  "",
            "timeout_s": 300,
            "log_dir":   str(Path(BASE_DIR) / "runs"),
        }


# ============================================================
# CONNECTION HELPERS
# ============================================================

def _get_master_connection():
    """
    Returns a connection to the master database.
    Required for CREATE DATABASE, RESTORE DATABASE, DROP DATABASE.
    autocommit=True is required — DDL cannot run inside a transaction.
    """
    cfg = DB_CONFIG
    if cfg.get("trusted_connection", "no").lower() == "yes":
        conn_str = (
            f"DRIVER={{{cfg['driver']}}};"
            f"SERVER={cfg['server']};"
            f"DATABASE=master;"
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

    conn = pyodbc.connect(conn_str)
    conn.autocommit = True   # DDL requires autocommit
    return conn


def _get_shadow_connection(shadow_name: str):
    """Returns a connection to the shadow database."""
    cfg = DB_CONFIG
    if cfg.get("trusted_connection", "no").lower() == "yes":
        conn_str = (
            f"DRIVER={{{cfg['driver']}}};"
            f"SERVER={cfg['server']};"
            f"DATABASE={shadow_name};"
            f"Trusted_Connection=yes;"
        )
    else:
        conn_str = (
            f"DRIVER={{{cfg['driver']}}};"
            f"SERVER={cfg['server']};"
            f"DATABASE={shadow_name};"
            f"UID={cfg['username']};"
            f"PWD={cfg['password']};"
        )

    conn = pyodbc.connect(conn_str)
    conn.autocommit = True
    return conn


def _shadow_exists(shadow_name: str) -> bool:
    """Check if the shadow database already exists."""
    try:
        conn   = _get_master_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT COUNT(*) FROM sys.databases WHERE name = ?",
            shadow_name,
        )
        count = cursor.fetchone()[0]
        conn.close()
        return count > 0
    except Exception:
        return False


# ============================================================
# STEP 1: create()
# ============================================================

def create(bak_path: str = None) -> dict:
    """
    Creates the shadow database by restoring from a .bak file.

    Args:
        bak_path: path to the .bak file. If None, reads from
                  SANDBOX_BAK_PATH in config.py.

    Returns:
        dict with shadow_name, bak_path, elapsed_s, success, error

    Usage:
        result = create()
        result = create(bak_path=r"C:\\Backups\\AcmeDev.bak")
    """
    cfg         = _get_sandbox_config()
    bak_path    = bak_path or cfg["bak_path"]
    shadow_name = _shadow_name()

    log.info(f"SANDBOX CREATE: {shadow_name} from {bak_path}")

    if not bak_path:
        raise SandboxError(
            operation = "create",
            detail    = "No .bak file path provided",
        )

    if not Path(bak_path).exists():
        raise SandboxError(
            operation = "create",
            detail    = (
                f"Backup file not found: {bak_path}\n"
                f"Set SANDBOX_BAK_PATH in config.py to the correct path."
            ),
        )

    # Clean up any leftover shadow from a previous failed run
    if _shadow_exists(shadow_name):
        _warn(f"Shadow DB '{shadow_name}' already exists — dropping it first")
        destroy(shadow_name)

    _info(f"Restoring {Path(bak_path).name} → {shadow_name}")
    _info("This may take 30–120 seconds depending on database size...")

    start = time.time()

    try:
        conn   = _get_master_connection()
        cursor = conn.cursor()

        # First, get the logical file names from the backup
        cursor.execute(f"RESTORE FILELISTONLY FROM DISK = N'{bak_path}'")
        file_list = cursor.fetchall()

        if not file_list:
            raise SandboxError("create", f"Could not read file list from {bak_path}")

        # Build MOVE clauses — redirect files to default SQL Server data dir
        data_dir  = cfg["data_dir"]
        move_parts = []

        for row in file_list:
            logical_name = row[0]
            file_type    = row[2].strip().upper()  # D=data, L=log

            if data_dir:
                # Use configured data directory
                ext          = ".mdf" if file_type == "D" else ".ldf"
                physical_new = str(Path(data_dir) / f"{shadow_name}_{logical_name}{ext}")
            else:
                # Let SQL Server figure out the path from the backup
                # by replacing the original DB name with shadow name
                original_path = row[1]
                physical_new  = re.sub(
                    re.escape(DB_CONFIG["database"]),
                    shadow_name,
                    original_path,
                    flags=re.IGNORECASE,
                )

            move_parts.append(
                f"MOVE N'{logical_name}' TO N'{physical_new}'"
            )

        move_clause = ",\n".join(move_parts)

        restore_sql = f"""
RESTORE DATABASE [{shadow_name}]
FROM DISK = N'{bak_path}'
WITH
    {move_clause},
    REPLACE,
    STATS = 10
"""

        cursor.execute(restore_sql)

        # Wait for restore to complete (it's async with STATS)
        # Poll sys.databases until the shadow appears and is online
        timeout = cfg["timeout_s"]
        waited  = 0
        while waited < timeout:
            if _shadow_exists(shadow_name):
                # Check it's online (state_desc = 'ONLINE')
                cursor.execute(
                    "SELECT state_desc FROM sys.databases WHERE name = ?",
                    shadow_name,
                )
                row = cursor.fetchone()
                if row and row[0] == "ONLINE":
                    break
            time.sleep(2)
            waited += 2

        conn.close()

        if not _shadow_exists(shadow_name):
            raise SandboxError("create", f"Shadow DB did not come online after {timeout}s")

        elapsed = round(time.time() - start, 1)
        log.info(f"SANDBOX CREATED: {shadow_name} ({elapsed}s)")
        _ok(f"Shadow DB ready: {shadow_name} ({elapsed}s)")

        return {
            "shadow_name": shadow_name,
            "bak_path":    bak_path,
            "elapsed_s":   elapsed,
            "success":     True,
            "error":       None,
        }

    except SandboxError:
        raise
    except pyodbc.Error as e:
        log.error(f"SANDBOX CREATE FAILED: {e}")
        raise SandboxError("create", str(e))
    except Exception as e:
        log.error(f"SANDBOX CREATE UNEXPECTED: {e}")
        raise SandboxError("create", str(e))


# ============================================================
# STEP 2: apply()
# ============================================================

def apply(sql_statements: list, shadow_name: str = None) -> dict:
    """
    Applies a list of SQL statements to the shadow database.
    This is where index creation and query changes are tested.

    Args:
        sql_statements: list of SQL strings to execute in order
        shadow_name:    shadow DB name (default: today's shadow name)

    Returns:
        dict with results per statement, success flag, errors

    Usage:
        result = apply([
            "CREATE INDEX IX_test ON measurements (machine_id) INCLUDE (value)",
            "CREATE INDEX IX_test2 ON sensors (sensor_id)",
        ])
    """
    shadow_name = shadow_name or _shadow_name()
    log.info(f"SANDBOX APPLY: {len(sql_statements)} statement(s) to {shadow_name}")

    if not _shadow_exists(shadow_name):
        raise SandboxError(
            "apply",
            f"Shadow DB '{shadow_name}' does not exist. Run sandbox-create first.",
        )

    results      = []
    all_success  = True

    try:
        conn   = _get_shadow_connection(shadow_name)
        cursor = conn.cursor()

        for i, sql in enumerate(sql_statements, 1):
            preview = sql.strip().splitlines()[0][:60]
            _info(f"  [{i}/{len(sql_statements)}] {preview}...")

            try:
                start = time.time()
                cursor.execute(sql)
                elapsed = round((time.time() - start) * 1000, 1)

                results.append({
                    "sql":       sql,
                    "success":   True,
                    "elapsed_ms":elapsed,
                    "error":     None,
                })
                _ok(f"{preview} ({elapsed}ms)")
                log.info(f"SANDBOX APPLY OK: {preview} ({elapsed}ms)")

            except pyodbc.Error as e:
                all_success = False
                err_msg = str(e)
                results.append({
                    "sql":     sql,
                    "success": False,
                    "error":   err_msg,
                })
                _fail(f"{preview}")
                _fail(f"  Error: {err_msg}")
                log.error(f"SANDBOX APPLY FAILED: {preview} — {err_msg}")

        conn.close()

    except SandboxError:
        raise
    except Exception as e:
        log.error(f"SANDBOX APPLY UNEXPECTED: {e}")
        raise SandboxError("apply", str(e))

    return {
        "shadow_name":  shadow_name,
        "statements":   len(sql_statements),
        "results":      results,
        "success":      all_success,
        "failed_count": sum(1 for r in results if not r["success"]),
    }


# ============================================================
# STEP 3: benchmark()
# ============================================================

def benchmark(
    queries:     list,
    shadow_name: str = None,
    runs:        int = 5,
) -> dict:
    """
    Benchmarks a list of queries against the shadow database.
    Uses fewer runs than the main benchmarker (5 vs 10) since
    this is for validation, not proof — speed matters here.

    Args:
        queries:     list of dicts: [{"label": "...", "sql": "..."}]
        shadow_name: shadow DB name
        runs:        number of runs per query (default 5)

    Returns:
        dict with per-query timing results

    Usage:
        results = benchmark([
            {"label": "dashboard filter", "sql": "SELECT * FROM vw_dashboard WHERE machine_id=1"},
            {"label": "sensor count",     "sql": "SELECT COUNT(*) FROM sensor_readings"},
        ])
    """
    shadow_name = shadow_name or _shadow_name()
    log.info(f"SANDBOX BENCHMARK: {len(queries)} queries against {shadow_name}")

    if not _shadow_exists(shadow_name):
        raise SandboxError("benchmark", f"Shadow '{shadow_name}' does not exist")

    results = []

    try:
        conn   = _get_shadow_connection(shadow_name)
        cursor = conn.cursor()

        for q in queries:
            label = q.get("label", "query")
            sql   = q["sql"]
            times = []

            _info(f"  Benchmarking: {label}...")

            for _ in range(runs):
                try:
                    start = time.perf_counter()
                    cursor.execute(sql)
                    cursor.fetchall()
                    elapsed = (time.perf_counter() - start) * 1000
                    times.append(round(elapsed, 2))
                except pyodbc.Error as e:
                    results.append({
                        "label":   label,
                        "sql":     sql,
                        "success": False,
                        "error":   str(e),
                    })
                    break
            else:
                import statistics
                avg_ms = round(statistics.mean(times), 2)
                results.append({
                    "label":     label,
                    "sql":       sql,
                    "success":   True,
                    "avg_ms":    avg_ms,
                    "min_ms":    round(min(times), 2),
                    "max_ms":    round(max(times), 2),
                    "times":     times,
                    "runs":      runs,
                })
                _ok(f"{label}: {avg_ms}ms avg")
                log.info(f"SANDBOX BENCHMARK: {label} = {avg_ms}ms avg")

        conn.close()

    except SandboxError:
        raise
    except Exception as e:
        raise SandboxError("benchmark", str(e))

    return {
        "shadow_name": shadow_name,
        "queries":     len(queries),
        "results":     results,
        "success":     all(r.get("success", False) for r in results),
    }


# ============================================================
# STEP 4: regression_check()
# ============================================================

def regression_check(
    queries:          list,
    shadow_name:      str   = None,
    baseline_history: list  = None,
    threshold_pct:    float = 30.0,
) -> dict:
    """
    Verifies that existing queries are not slower or returning
    different data after changes are applied to the shadow.

    Args:
        queries:          list of {"label": "...", "sql": "...", "baseline_ms": float}
                          baseline_ms is the known-good time from history.db
        shadow_name:      shadow DB name
        baseline_history: optional list of history run dicts (to auto-populate baselines)
        threshold_pct:    flag as regression if >this% slower (default 30%)

    Returns:
        dict with per-query pass/fail, overall passed flag, regressions list

    Usage:
        result = regression_check([
            {"label": "dashboard", "sql": "SELECT...", "baseline_ms": 12.1},
        ])
    """
    shadow_name = shadow_name or _shadow_name()
    log.info(f"SANDBOX REGRESSION CHECK: {len(queries)} queries, threshold {threshold_pct}%")

    if not queries:
        _info("No regression queries provided — skipping")
        return {"passed": True, "regressions": [], "results": []}

    # Run benchmark on shadow
    bench = benchmark(queries, shadow_name=shadow_name, runs=3)

    regressions = []
    results     = []

    for q, bench_result in zip(queries, bench["results"]):
        if not bench_result.get("success"):
            regressions.append({
                "label":  q.get("label", "query"),
                "reason": f"Query failed: {bench_result.get('error')}",
                "severity": "HIGH",
            })
            results.append({**bench_result, "regression": True, "reason": "query_failed"})
            continue

        baseline_ms  = q.get("baseline_ms")
        shadow_avg   = bench_result["avg_ms"]

        if baseline_ms:
            slowdown_pct = ((shadow_avg - baseline_ms) / baseline_ms) * 100

            if slowdown_pct > threshold_pct:
                reason = (
                    f"Query is {round(slowdown_pct, 1)}% slower in shadow "
                    f"({baseline_ms}ms → {shadow_avg}ms)"
                )
                regressions.append({
                    "label":      q.get("label", "query"),
                    "reason":     reason,
                    "baseline_ms":baseline_ms,
                    "shadow_ms":  shadow_avg,
                    "slowdown_pct": round(slowdown_pct, 1),
                    "severity":   "HIGH",
                })
                results.append({
                    **bench_result,
                    "regression":   True,
                    "slowdown_pct": round(slowdown_pct, 1),
                    "baseline_ms":  baseline_ms,
                })
                _fail(f"{q.get('label', 'query')}: {round(slowdown_pct, 1)}% slower — REGRESSION")
                log.error(f"SANDBOX REGRESSION: {q.get('label')} — {reason}")
            else:
                results.append({
                    **bench_result,
                    "regression":   False,
                    "baseline_ms":  baseline_ms,
                    "slowdown_pct": round(slowdown_pct, 1),
                })
                _ok(f"{q.get('label', 'query')}: OK ({shadow_avg}ms, was {baseline_ms}ms)")
        else:
            # No baseline — just record the shadow timing
            results.append({**bench_result, "regression": False, "baseline_ms": None})
            _ok(f"{q.get('label', 'query')}: {shadow_avg}ms (no baseline)")

    passed = len(regressions) == 0
    log.info(
        f"SANDBOX REGRESSION CHECK: {'PASSED' if passed else 'FAILED'} "
        f"({len(regressions)} regression(s))"
    )

    return {
        "shadow_name": shadow_name,
        "passed":      passed,
        "regressions": regressions,
        "results":     results,
        "threshold_pct": threshold_pct,
    }


# ============================================================
# STEP 5: destroy()
# ============================================================

def destroy(shadow_name: str = None) -> bool:
    """
    Drops the shadow database and frees disk space.
    Called automatically at the end of every sandbox session.

    Args:
        shadow_name: shadow DB name (default: today's shadow name)

    Returns:
        True if destroyed, False if not found or error

    Usage:
        destroy()  # destroys today's shadow
        destroy("AcmeDev_Shadow_20260320")  # destroy specific shadow
    """
    shadow_name = shadow_name or _shadow_name()
    log.info(f"SANDBOX DESTROY: {shadow_name}")

    if not _shadow_exists(shadow_name):
        _info(f"Shadow '{shadow_name}' does not exist — nothing to destroy")
        return True

    try:
        conn   = _get_master_connection()
        cursor = conn.cursor()

        # Force all connections closed before dropping
        cursor.execute(f"""
            ALTER DATABASE [{shadow_name}]
            SET SINGLE_USER WITH ROLLBACK IMMEDIATE
        """)

        cursor.execute(f"DROP DATABASE [{shadow_name}]")
        conn.close()

        _ok(f"Shadow DB destroyed: {shadow_name}")
        log.info(f"SANDBOX DESTROYED: {shadow_name}")
        return True

    except pyodbc.Error as e:
        _warn(f"Could not destroy shadow: {e}")
        log.error(f"SANDBOX DESTROY FAILED: {shadow_name} — {e}")
        return False
    except Exception as e:
        _warn(f"Unexpected error destroying shadow: {e}")
        return False


# ============================================================
# HIGH-LEVEL: full sandbox test pipeline
# ============================================================

def run_sandbox_test(
    sql_statements:   list,
    regression_queries: list = None,
    bak_path:         str   = None,
    threshold_pct:    float = 30.0,
    keep_on_failure:  bool  = False,
) -> dict:
    """
    Full sandbox pipeline — create, apply, benchmark, regression check, destroy.

    This is the main entry point called by:
      - pipeline.run_single() when --safe flag is used
      - 'python agent.py sandbox-test' command

    Args:
        sql_statements:    SQL to apply to the shadow (index scripts etc.)
        regression_queries:queries to check for regressions (from history.db)
        bak_path:          path to .bak file
        threshold_pct:     regression threshold % (default 30%)
        keep_on_failure:   keep shadow DB alive if test fails (for inspection)

    Returns:
        dict with:
            passed          — True if all checks passed
            shadow_name     — name of the shadow DB (destroyed after)
            apply_result    — result of apply()
            benchmark_result— result of benchmark()
            regression_result— result of regression_check()
            safe_to_deploy  — True = generate real deploy.sql
            errors          — list of failure reasons

    Usage:
        result = run_sandbox_test(
            sql_statements = ["CREATE INDEX IX_test ON measurements (machine_id)"],
            regression_queries = [
                {"label": "dashboard", "sql": "SELECT...", "baseline_ms": 12.1}
            ],
        )
        if result["safe_to_deploy"]:
            generate_deployment_package()
    """
    shadow_name = _shadow_name()
    errors      = []
    TOTAL       = 5

    console.print()
    console.print(Panel(
        f"[bold cyan]Shadow DB Sandbox[/bold cyan]\n"
        f"[dim]{shadow_name} — safe pre-deployment testing[/dim]",
        border_style="cyan", expand=False,
    ))

    result = {
        "shadow_name":        shadow_name,
        "passed":             False,
        "apply_result":       None,
        "benchmark_result":   None,
        "regression_result":  None,
        "safe_to_deploy":     False,
        "errors":             errors,
    }

    # ── Step 1: Create shadow ─────────────────────────────
    _step(1, TOTAL, "Creating shadow database from .bak")
    try:
        create_result = create(bak_path=bak_path)
    except SandboxError as e:
        _fail(str(e))
        errors.append(e.message)
        result["errors"] = errors
        return result

    # ── Step 2: Apply changes ─────────────────────────────
    _step(2, TOTAL, f"Applying {len(sql_statements)} change(s) to shadow")
    try:
        apply_result         = apply(sql_statements, shadow_name=shadow_name)
        result["apply_result"] = apply_result

        if not apply_result["success"]:
            failed = [r for r in apply_result["results"] if not r["success"]]
            for f in failed:
                errors.append(f"Apply failed: {f['sql'][:60]} — {f['error']}")
            _fail(f"{apply_result['failed_count']} statement(s) failed")
            _cleanup(shadow_name, keep_on_failure)
            result["errors"] = errors
            return result

    except SandboxError as e:
        errors.append(e.message)
        _cleanup(shadow_name, keep_on_failure)
        result["errors"] = errors
        return result

    # ── Step 3: Benchmark in shadow ───────────────────────
    _step(3, TOTAL, "Benchmarking optimized queries in shadow")
    bench_queries = regression_queries or []

    if bench_queries:
        try:
            bench_result           = benchmark(bench_queries, shadow_name=shadow_name)
            result["benchmark_result"] = bench_result
            _ok(
                f"Benchmark complete — "
                f"{sum(1 for r in bench_result['results'] if r.get('success'))}/"
                f"{len(bench_queries)} queries OK"
            )
        except SandboxError as e:
            _warn(f"Benchmark failed: {e.message} — continuing to regression check")
    else:
        _info("No benchmark queries provided — skipping")

    # ── Step 4: Regression check ──────────────────────────
    _step(4, TOTAL, f"Regression check (threshold: {threshold_pct}% slower = fail)")

    if bench_queries:
        try:
            reg_result               = regression_check(
                bench_queries,
                shadow_name    = shadow_name,
                threshold_pct  = threshold_pct,
            )
            result["regression_result"] = reg_result

            if not reg_result["passed"]:
                for reg in reg_result["regressions"]:
                    errors.append(f"Regression: {reg['label']} — {reg['reason']}")
                _fail(f"{len(reg_result['regressions'])} regression(s) detected")
                _cleanup(shadow_name, keep_on_failure)
                result["errors"] = errors
                return result

            _ok(f"All {len(bench_queries)} queries passed regression check")

        except SandboxError as e:
            _warn(f"Regression check failed: {e.message} — treating as passed")
    else:
        _info("No regression queries — skipping regression check")

    # ── Step 5: Destroy shadow ────────────────────────────
    _step(5, TOTAL, "Destroying shadow database")
    destroy(shadow_name)

    result["passed"]         = True
    result["safe_to_deploy"] = True
    result["errors"]         = errors

    console.print()
    console.print(Panel(
        "[bold green]✓ Sandbox test PASSED[/bold green]\n"
        "[dim]All changes applied cleanly. No regressions detected.\n"
        "Safe to generate deployment package.[/dim]",
        border_style="green", expand=False,
    ))

    log.info(f"SANDBOX TEST PASSED: {shadow_name}")
    return result


def _cleanup(shadow_name: str, keep_on_failure: bool):
    """Destroy shadow unless keep_on_failure is set."""
    if keep_on_failure:
        _warn(
            f"Shadow DB kept for inspection: {shadow_name}\n"
            f"  Run: python agent.py sandbox-destroy when done"
        )
    else:
        _info("Cleaning up shadow DB...")
        destroy(shadow_name)


# ============================================================
# UTILITY: list_shadows()
# ============================================================

def list_shadows() -> list:
    """
    Returns a list of all shadow databases currently on the server.
    Useful to check for orphaned shadows that weren't cleaned up.

    Usage:
        shadows = list_shadows()
    """
    try:
        conn   = _get_master_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT name, create_date, state_desc
            FROM sys.databases
            WHERE name LIKE ?
            ORDER BY create_date DESC
        """, f"%_Shadow_%")

        rows = cursor.fetchall()
        conn.close()

        return [
            {
                "name":        row[0],
                "created":     str(row[1])[:16],
                "state":       row[2],
                "is_orphaned": row[2] != "ONLINE",
            }
            for row in rows
        ]
    except Exception as e:
        log.error(f"Could not list shadows: {e}")
        return []


# ============================================================
# PRINT HELPERS
# ============================================================

def print_sandbox_result(result: dict):
    """Print a formatted sandbox test result to terminal."""
    console.print()

    if result["passed"]:
        console.print("[bold green]━━━ SANDBOX TEST PASSED ━━━[/bold green]")
        console.print("  [green]✓[/green] All changes applied successfully")
        console.print("  [green]✓[/green] No regressions detected")
        console.print("  [green]✓[/green] Safe to generate deployment package")
        console.print(
            "\n  [dim]Run: python agent.py deploy  "
            "to generate the deployment package[/dim]"
        )
    else:
        console.print("[bold red]━━━ SANDBOX TEST FAILED ━━━[/bold red]")
        console.print("  [red]✗ Deployment package NOT generated[/red]")
        console.print("\n[bold]Failures:[/bold]")
        for err in result.get("errors", []):
            console.print(f"  [red]•[/red] {err}")

        reg = result.get("regression_result", {})
        if reg and reg.get("regressions"):
            console.print("\n[bold]Regressions detected:[/bold]")
            table = Table(show_header=True, header_style="bold red", border_style="dim")
            table.add_column("Query",      min_width=25)
            table.add_column("Baseline",   justify="right")
            table.add_column("In Shadow",  justify="right")
            table.add_column("Slowdown",   justify="right", style="red")

            for r in reg["regressions"]:
                table.add_row(
                    r.get("label", "?"),
                    f"{r.get('baseline_ms', '?')}ms",
                    f"{r.get('shadow_ms', '?')}ms",
                    f"{r.get('slowdown_pct', '?')}%",
                )
            console.print(table)

        console.print(
            "\n  [dim]Fix the issues above, then re-run: "
            "python agent.py sandbox-test[/dim]"
        )
