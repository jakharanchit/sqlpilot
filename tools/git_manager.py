# ============================================================
# tools/git_manager.py
# Auto-commits every meaningful action to Git with structured,
# informative commit messages.
#
# WHY AUTO-COMMIT:
#   Manual Git is easy to forget. If you optimize 5 queries
#   in a session and forget to commit, you lose the history
#   of what changed and why. Auto-commit means the record
#   is always there without you thinking about it.
#
# COMMIT TYPES:
#   [optimize]  — after a query/view optimization run
#   [benchmark] — after a before/after benchmark
#   [migrate]   — after a migration file is generated
#   [deploy]    — after a deployment package is created
#   [watch]     — after schema watcher runs and finds changes
#   [baseline]  — initial project or client setup
#
# WHAT GETS COMMITTED:
#   ✓ Migration files (migrations/*.sql)
#   ✓ Registry (migrations/registry.json)
#   ✓ Deployment packages (deployments/**)
#   ✓ Reports (reports/**)
#   ✓ Schema snapshots (when watcher runs)
#
# WHAT DOES NOT GET COMMITTED:
#   ✗ runs/*.md       — may contain sensitive query data
#   ✗ *.bak           — too large, contains client data
#   ✗ history.db      — local only
#   ✗ query_history.db — local only
#   ✗ config.py       — contains connection strings
# ============================================================

import os
from datetime import datetime
from pathlib import Path

from rich.console import Console

from config import BASE_DIR, AUTO_COMMIT_GIT

console = Console()


def _get_repo():
    """
    Returns a GitPython Repo object for the project directory.
    Returns None if Git is not initialized or gitpython not installed.
    """
    try:
        import git
        return git.Repo(BASE_DIR)
    except Exception:
        return None


def _git_available() -> bool:
    """Check if git is initialized and gitpython is installed."""
    try:
        import git
        git.Repo(BASE_DIR)
        return True
    except ImportError:
        console.print("  [dim]⚠ gitpython not installed — skipping Git commit[/dim]")
        console.print("  [dim]  Install with: pip install gitpython[/dim]")
        return False
    except Exception:
        console.print("  [dim]⚠ Git not initialized in project — skipping commit[/dim]")
        console.print(f"  [dim]  Run: git init  (in {BASE_DIR})[/dim]")
        return False


# ============================================================
# CORE: commit
# ============================================================

def commit(
    message:      str,
    paths:        list = None,
    commit_type:  str  = "update",
    skip_if_clean: bool = True,
) -> bool:
    """
    Stage and commit specific files or all changed files.

    Args:
        message:       commit message body (type prefix added automatically)
        paths:         list of file paths to stage — None stages all changed files
        commit_type:   prefix: optimize | benchmark | migrate | deploy | watch | baseline
        skip_if_clean: skip silently if nothing changed

    Returns:
        True if committed, False if skipped or failed

    Usage:
        commit("vw_dashboard — 847ms → 12ms (98.6%)", commit_type="optimize",
               paths=["migrations/004_optimize_vw_dashboard.sql"])
    """
    if not AUTO_COMMIT_GIT:
        console.print("  [dim]Auto-commit disabled in config.py[/dim]")
        return False

    if not _git_available():
        return False

    import git
    repo = git.Repo(BASE_DIR)

    try:
        # Stage specified paths or all changes
        if paths:
            # Convert to absolute paths and only stage files that exist
            abs_paths = []
            for p in paths:
                abs_p = Path(BASE_DIR) / p if not Path(p).is_absolute() else Path(p)
                if abs_p.exists():
                    abs_paths.append(str(abs_p))
                else:
                    console.print(f"  [dim]⚠ File not found for staging: {p}[/dim]")

            if abs_paths:
                repo.index.add(abs_paths)
        else:
            # Stage all tracked and untracked files (respecting .gitignore)
            repo.git.add("--all")

        # Check if there's anything to commit
        if skip_if_clean and not repo.index.diff("HEAD") and not repo.untracked_files:
            console.print("  [dim]Nothing to commit — working tree clean[/dim]")
            return False

        # Build full commit message
        full_message = f"[{commit_type}] {message}\n\nDate: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\nAgent: SQL Optimization Agent v2"

        repo.index.commit(full_message)
        short_hash = repo.head.commit.hexsha[:7]
        console.print(
            f"  [green]✓[/green] Git committed: "
            f"[cyan][{commit_type}][/cyan] {message[:60]} "
            f"[dim]({short_hash})[/dim]"
        )
        return True

    except git.exc.GitCommandError as e:
        console.print(f"  [yellow]⚠ Git commit failed: {e}[/yellow]")
        console.print("  [dim]Changes are saved to disk — commit manually if needed[/dim]")
        return False
    except Exception as e:
        console.print(f"  [yellow]⚠ Git error: {e}[/yellow]")
        return False


# ============================================================
# TYPED COMMIT HELPERS
# Makes calling code cleaner — no need to pass commit_type
# ============================================================

def commit_optimization(
    query_label:      str,
    migration_path:   str = None,
    before_ms:        float = None,
    after_ms:         float = None,
    improvement_pct:  float = None,
):
    """
    Commit after a query/view optimization.

    Usage:
        commit_optimization(
            query_label     = "vw_dashboard machine filter",
            migration_path  = "migrations/004_optimize_vw_dashboard.sql",
            before_ms       = 847.3,
            after_ms        = 12.1,
            improvement_pct = 98.6,
        )
    """
    if before_ms and after_ms:
        msg = f"{query_label} — {before_ms}ms → {after_ms}ms ({improvement_pct}%)"
    else:
        msg = f"{query_label} — optimized"

    paths = ["migrations/registry.json"]
    if migration_path:
        paths.append(migration_path)

    return commit(msg, paths=paths, commit_type="optimize")


def commit_migration(migration_number: int, description: str, filename: str):
    """
    Commit a newly generated migration file.

    Usage:
        commit_migration(4, "add covering index for machine filter",
                         "migrations/004_add_covering_index.sql")
    """
    msg   = f"migration {migration_number:03d} — {description}"
    paths = [filename, "migrations/registry.json"]
    return commit(msg, paths=paths, commit_type="migrate")


def commit_benchmark(label: str, before_ms: float, after_ms: float, improvement_pct: float):
    """
    Commit benchmark results (updates run log and registry).

    Usage:
        commit_benchmark("vw_dashboard", 847.3, 12.1, 98.6)
    """
    msg = f"{label} — {before_ms}ms → {after_ms}ms ({improvement_pct}% improvement)"
    return commit(msg, commit_type="benchmark")


def commit_deployment(client: str, migration_range: str, package_path: str):
    """
    Commit after a deployment package is generated.

    Usage:
        commit_deployment("client_acme", "004-008", "deployments/client_acme_2026_03_20/")
    """
    msg   = f"{client} — package generated — migrations {migration_range}"
    paths = [package_path]
    return commit(msg, paths=paths, commit_type="deploy")


def commit_schema_watch(changes_summary: str):
    """
    Commit after schema watcher detects changes.

    Usage:
        commit_schema_watch("measurements.sensor_value INT→FLOAT — 3 queries affected")
    """
    return commit(changes_summary, commit_type="watch")


def commit_baseline(client: str):
    """
    Initial commit for a new client workspace.

    Usage:
        commit_baseline("client_acme")
    """
    msg = f"{client} — baseline initialized"
    return commit(msg, commit_type="baseline")


# ============================================================
# GIT LOG READER
# ============================================================

def get_recent_commits(limit: int = 10) -> list:
    """
    Returns recent commits from the Git log.

    Returns:
        list of dicts with hash, message, date, type
    """
    if not _git_available():
        return []

    import git
    repo    = git.Repo(BASE_DIR)
    commits = []

    try:
        for c in repo.iter_commits(max_count=limit):
            # Parse commit type from message prefix [type]
            msg       = c.message.strip().splitlines()[0]
            type_match = __import__("re").match(r"^\[(\w+)\]", msg)
            commit_type = type_match.group(1) if type_match else "other"

            commits.append({
                "hash":    c.hexsha[:7],
                "message": msg,
                "type":    commit_type,
                "date":    datetime.fromtimestamp(c.committed_date).strftime("%Y-%m-%d %H:%M"),
                "author":  str(c.author),
            })
    except Exception as e:
        console.print(f"  [dim]⚠ Could not read git log: {e}[/dim]")

    return commits


def get_status() -> dict:
    """
    Returns current Git status — modified files, untracked, branch.

    Returns:
        dict with branch, modified, untracked, is_dirty
    """
    if not _git_available():
        return {"error": "Git not available"}

    import git
    repo = git.Repo(BASE_DIR)

    try:
        return {
            "branch":    repo.active_branch.name,
            "modified":  [item.a_path for item in repo.index.diff(None)],
            "untracked": repo.untracked_files,
            "is_dirty":  repo.is_dirty(untracked_files=True),
        }
    except Exception as e:
        return {"error": str(e)}


def init_git_if_needed() -> bool:
    """
    Initialize a Git repository in the project directory if one
    doesn't exist yet. Called during new-client setup.

    Returns True if initialized or already exists.
    """
    try:
        import git

        project_path = Path(BASE_DIR)
        git_dir      = project_path / ".git"

        if git_dir.exists():
            console.print("  [dim]Git already initialized[/dim]")
            return True

        repo = git.Repo.init(BASE_DIR)
        console.print(f"  [green]✓[/green] Git initialized in {BASE_DIR}")

        # Initial commit with project skeleton
        repo.git.add("--all")
        try:
            repo.index.commit(
                "[baseline] project initialized\n\n"
                f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                "Agent: SQL Optimization Agent"
            )
            console.print("  [green]✓[/green] Initial commit created")
        except Exception:
            console.print("  [dim]Nothing to commit for initial baseline[/dim]")

        return True

    except ImportError:
        console.print("  [yellow]⚠ gitpython not installed — Git tracking disabled[/yellow]")
        console.print("  [dim]Install with: pip install gitpython[/dim]")
        return False
    except Exception as e:
        console.print(f"  [yellow]⚠ Git init failed: {e}[/yellow]")
        return False
