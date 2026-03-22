# ============================================================
# tools/client_manager.py
# Multi-client workspace management for SQL Optimization Agent v3.
#
# DESIGN:
#   Each client gets a fully isolated workspace under projects/:
#
#   projects/
#   ├── _template/                ← copied for every new client
#   ├── client_acme/
#   │   ├── client.json           ← DB connection, .bak path, notes
#   │   ├── migrations/           ← migrations for THIS client only
#   │   ├── reports/
#   │   ├── deployments/
#   │   ├── snapshots/
#   │   ├── runs/
#   │   └── history.db            ← history for THIS client only
#   └── client_xyz/
#       └── ...
#
#   .active_client                ← plain text, name of current client
#                                    (in project root, not config.py)
#
# SWITCHING CLIENTS:
#   python agent.py client-switch client_xyz
#   → writes "client_xyz" to .active_client
#   → all tools now read/write to projects/client_xyz/
#
# GLOBAL vs PER-CLIENT:
#   Global (config.py):       Ollama URL, models, benchmark runs
#   Per-client (client.json): DB connection, .bak path, server name
#
# HOW TOOLS RESOLVE PATHS:
#   Instead of hardcoded MIGRATIONS_DIR from config.py, tools call:
#       from tools.client_manager import get_client_paths
#       paths = get_client_paths()
#       migrations_dir = paths["migrations"]
#   This returns the active client's folder automatically.
# ============================================================

import json
import re
import shutil
from datetime import datetime
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

import config
from tools.app_logger import get_logger
from tools.error_handler import ConfigError, AgentError

console = Console()
log     = get_logger("client_manager")

ACTIVE_CLIENT_FILE = Path(config.BASE_DIR) / ".active_client"
TEMPLATE_DIR       = Path(config.PROJECTS_DIR) / "_template"


# ============================================================
# ACTIVE CLIENT STATE
# ============================================================

def get_active_client() -> str:
    """
    Returns the name of the currently active client.

    Priority:
    1. .active_client file in project root
    2. ACTIVE_CLIENT from config.py
    3. Falls back to "client_acme" if neither is set

    Usage:
        client = get_active_client()
        print(f"Working on: {client}")
    """
    # .active_client file takes priority
    if ACTIVE_CLIENT_FILE.exists():
        name = ACTIVE_CLIENT_FILE.read_text(encoding="utf-8").strip()
        if name:
            return name

    # Fall back to config.py
    try:
        from config import ACTIVE_CLIENT
        if ACTIVE_CLIENT:
            return ACTIVE_CLIENT
    except ImportError:
        pass

    return "client_acme"


def set_active_client(name: str) -> None:
    """
    Set the active client by writing to .active_client file.
    Does not modify config.py.

    Args:
        name: client folder name e.g. "client_acme"

    Usage:
        set_active_client("client_xyz")
    """
    client_dir = Path(PROJECTS_DIR) / name
    if not client_dir.exists():
        raise ConfigError(
            f"Client '{name}'",
            detail=f"Folder not found: {client_dir}\nCreate it first: python agent.py new-client {name}",
        )

    ACTIVE_CLIENT_FILE.write_text(name, encoding="utf-8")
    log.info(f"CLIENT SWITCH: → {name}")


def get_client_paths(client: str = None) -> dict:
    """
    Returns all resolved paths for the active (or specified) client.

    Every tool should call this instead of using hardcoded paths
    from config.py. This is what makes multi-client work.

    Args:
        client: client name — defaults to active client

    Returns:
        dict with all path strings for this client:
            base, migrations, reports, deployments,
            snapshots, runs, history_db, config_file

    Usage:
        from tools.client_manager import get_client_paths
        paths = get_client_paths()
        # paths["migrations"] → "projects/client_acme/migrations"
        # paths["history_db"] → "projects/client_acme/history.db"
    """
    name       = client or get_active_client()
    client_dir = Path(PROJECTS_DIR) / name

    return {
        "name":        name,
        "base":        str(client_dir),
        "migrations":  str(client_dir / "migrations"),
        "reports":     str(client_dir / "reports"),
        "deployments": str(client_dir / "deployments"),
        "snapshots":   str(client_dir / "snapshots"),
        "runs":        str(client_dir / "runs"),
        "history_db":  str(client_dir / "history.db"),
        "config_file": str(client_dir / "client.json"),
        "git_dir":     str(client_dir / ".git"),
    }


def get_client_config(client: str = None) -> dict:
    """
    Returns the per-client configuration (from client.json).
    Falls back to global config.py values if client.json not set.

    The client config OVERRIDES global DB settings — this is how
    each client can have a different database, server, and .bak path.

    Args:
        client: client name — defaults to active client

    Returns:
        dict with all settings for this client

    Usage:
        cfg = get_client_config()
        print(cfg["db_config"]["server"])
        print(cfg["bak_path"])
    """
    paths       = get_client_paths(client)
    config_file = Path(paths["config_file"])

    # Start with global defaults
    merged = {
        "name":           client or get_active_client(),
        "display_name":   "",
        "created":        "",
        "notes":          "",
        "db_config":      dict(DB_CONFIG),    # global DB config as default
        "bak_path":       "",
        "sandbox_data_dir":"",
        "sandbox_timeout": 300,
    }

    # Override with per-client settings if client.json exists
    if config_file.exists():
        try:
            client_data = json.loads(config_file.read_text(encoding="utf-8"))
            # Deep merge db_config
            if "db_config" in client_data:
                merged["db_config"].update(client_data["db_config"])
            # Merge top-level keys
            for key in ("display_name", "created", "notes",
                        "bak_path", "sandbox_data_dir", "sandbox_timeout"):
                if key in client_data:
                    merged[key] = client_data[key]
        except (json.JSONDecodeError, Exception) as e:
            log.warning(f"Could not read client.json for {client}: {e}")

    return merged


# ============================================================
# CREATE NEW CLIENT
# ============================================================

def create_client(
    name:         str,
    display_name: str  = "",
    server:       str  = "",
    database:     str  = "",
    bak_path:     str  = "",
    notes:        str  = "",
    set_active:   bool = True,
) -> dict:
    """
    Creates a new client workspace from the _template folder.

    Args:
        name:         folder name — slug format e.g. "client_acme"
        display_name: human-readable name e.g. "Acme Corp"
        server:       SQL Server name for this client
        database:     database name for this client
        bak_path:     path to the .bak file for this client
        notes:        any notes about this client
        set_active:   make this the active client after creating

    Returns:
        dict with client paths and config

    Usage:
        create_client(
            name         = "client_xyz",
            display_name = "XYZ Manufacturing",
            server       = "localhost\\\\SQLEXPRESS",
            database     = "XYZProduction",
            bak_path     = r"C:\\Backups\\XYZ.bak",
        )
    """
    # Validate name
    if not re.match(r'^[a-zA-Z0-9_-]+$', name):
        raise ConfigError(
            "client name",
            detail=f"'{name}' contains invalid characters. Use only letters, numbers, _ and -",
        )

    client_dir = Path(PROJECTS_DIR) / name

    if client_dir.exists():
        raise ConfigError(
            f"Client '{name}'",
            detail=f"Already exists at {client_dir}",
        )

    console.print(f"\n[cyan]Creating client workspace:[/cyan] {name}")

    # ── Copy template ─────────────────────────────────────
    if TEMPLATE_DIR.exists():
        shutil.copytree(str(TEMPLATE_DIR), str(client_dir))
        console.print(f"  [green]✓[/green] Copied from _template/")
    else:
        client_dir.mkdir(parents=True)
        console.print(f"  [green]✓[/green] Created directory")

    # ── Create subdirectories ─────────────────────────────
    for subdir in ("migrations", "reports", "deployments", "snapshots", "runs"):
        (client_dir / subdir).mkdir(parents=True, exist_ok=True)

    # ── Write baseline migration marker ──────────────────
    baseline = (client_dir / "migrations" / "000_baseline.sql")
    if not baseline.exists():
        baseline.write_text(
            f"-- ============================================================\n"
            f"-- Migration: 000\n"
            f"-- Client:    {name} ({display_name or name})\n"
            f"-- Date:      {datetime.now().strftime('%Y-%m-%d')}\n"
            f"-- Type:      BASELINE\n"
            f"-- Description: Initial baseline for {display_name or name}\n"
            f"-- ============================================================\n"
            f"-- This file is a marker only. No SQL to run.\n",
            encoding="utf-8",
        )

    # ── Write client.json ─────────────────────────────────
    client_cfg = {
        "name":         name,
        "display_name": display_name or name,
        "created":      datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "notes":        notes,
        "db_config": {
            "server":           server   or DB_CONFIG.get("server", "localhost"),
            "database":         database or DB_CONFIG.get("database", ""),
            "driver":           DB_CONFIG.get("driver", "ODBC Driver 17 for SQL Server"),
            "trusted_connection": DB_CONFIG.get("trusted_connection", "yes"),
        },
        "bak_path":         bak_path,
        "sandbox_data_dir": "",
        "sandbox_timeout":  300,
    }

    config_path = client_dir / "client.json"
    config_path.write_text(
        json.dumps(client_cfg, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    console.print(f"  [green]✓[/green] client.json written")

    # ── Initialize Git ─────────────────────────────────────
    try:
        from tools.git_manager import init_git_if_needed
        import os
        orig_dir = os.getcwd()
        os.chdir(str(client_dir))
        init_git_if_needed()
        os.chdir(orig_dir)
        console.print(f"  [green]✓[/green] Git initialized")
    except Exception as e:
        console.print(f"  [dim]⚠ Git init skipped: {e}[/dim]")

    # ── Set as active ─────────────────────────────────────
    if set_active:
        set_active_client(name)
        console.print(f"  [green]✓[/green] Set as active client")

    paths = get_client_paths(name)
    log.info(f"CLIENT CREATED: {name} ({display_name})")

    console.print(Panel(
        f"[bold green]✓ Client workspace ready[/bold green]\n"
        f"[dim]projects/{name}/[/dim]",
        border_style="green", expand=False,
    ))

    return {"name": name, "paths": paths, "config": client_cfg}


# ============================================================
# LIST CLIENTS
# ============================================================

def list_clients() -> list:
    """
    Returns a list of all client workspaces.

    Returns:
        list of dicts with name, display_name, created, active, db_name

    Usage:
        clients = list_clients()
        for c in clients:
            print(c["name"], "★" if c["active"] else "")
    """
    projects_dir = Path(PROJECTS_DIR)
    active       = get_active_client()
    clients      = []

    for d in sorted(projects_dir.iterdir()):
        if not d.is_dir() or d.name.startswith("_"):
            continue

        config_file = d / "client.json"
        cfg         = {}

        if config_file.exists():
            try:
                cfg = json.loads(config_file.read_text(encoding="utf-8"))
            except Exception:
                pass

        # Count migrations
        migs_dir   = d / "migrations"
        mig_count  = len(list(migs_dir.glob("*.sql"))) - 1 if migs_dir.exists() else 0  # exclude baseline

        # Count runs
        runs_dir   = d / "runs"
        run_count  = len(list(runs_dir.glob("*.md"))) if runs_dir.exists() else 0

        clients.append({
            "name":         d.name,
            "display_name": cfg.get("display_name", d.name),
            "created":      cfg.get("created", "")[:10],
            "database":     cfg.get("db_config", {}).get("database", "—"),
            "server":       cfg.get("db_config", {}).get("server", "—"),
            "bak_path":     cfg.get("bak_path", ""),
            "migrations":   max(mig_count, 0),
            "runs":         run_count,
            "active":       d.name == active,
        })

    return clients


# ============================================================
# UPDATE CLIENT CONFIG
# ============================================================

def update_client_config(
    client:       str  = None,
    display_name: str  = None,
    server:       str  = None,
    database:     str  = None,
    bak_path:     str  = None,
    notes:        str  = None,
) -> dict:
    """
    Update settings in a client's client.json.
    Only updates fields that are explicitly provided (not None).

    Args:
        client:       client name (default: active client)
        display_name: human-readable name
        server:       SQL Server instance name
        database:     database name
        bak_path:     path to .bak file
        notes:        free-text notes

    Returns:
        updated config dict

    Usage:
        update_client_config(
            database = "AcmeDev_v2",
            bak_path = r"C:\\Backups\\AcmeDev_v2.bak",
        )
    """
    name        = client or get_active_client()
    paths       = get_client_paths(name)
    config_file = Path(paths["config_file"])

    if not config_file.exists():
        raise ConfigError(
            f"client.json for '{name}'",
            detail=f"File not found: {config_file}\nCreate the client first.",
        )

    cfg = json.loads(config_file.read_text(encoding="utf-8"))

    # Apply updates
    if display_name is not None:
        cfg["display_name"] = display_name
    if notes is not None:
        cfg["notes"] = notes
    if bak_path is not None:
        cfg["bak_path"] = bak_path
    if server is not None:
        cfg.setdefault("db_config", {})["server"] = server
    if database is not None:
        cfg.setdefault("db_config", {})["database"] = database

    config_file.write_text(
        json.dumps(cfg, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    log.info(f"CLIENT CONFIG UPDATED: {name}")
    return cfg


# ============================================================
# CONTEXT MANAGER: with_client()
# ============================================================

class with_client:
    """
    Context manager that temporarily switches the active client.
    Restores the previous client on exit.

    Used internally for multi-client batch operations.

    Usage:
        with with_client("client_xyz"):
            run_single("SELECT * FROM vw_dashboard")
        # automatically switches back to previous client
    """

    def __init__(self, name: str):
        self.name     = name
        self.previous = None

    def __enter__(self):
        self.previous = get_active_client()
        set_active_client(self.name)
        return self

    def __exit__(self, *args):
        if self.previous:
            set_active_client(self.previous)


# ============================================================
# TERMINAL OUTPUT
# ============================================================

def print_client_list(clients: list):
    """Print a formatted client list table."""
    if not clients:
        console.print("[yellow]No client workspaces found.[/yellow]")
        console.print("[dim]Create one: python agent.py new-client ClientName[/dim]")
        return

    table = Table(
        show_header=True,
        header_style="bold cyan",
        border_style="dim",
    )
    table.add_column("",             width=2)           # active marker
    table.add_column("Client",       min_width=18)
    table.add_column("Display Name", min_width=20, style="dim")
    table.add_column("Database",     min_width=15)
    table.add_column("Migrations",   justify="right", style="dim")
    table.add_column("Runs",         justify="right", style="dim")
    table.add_column("Created",      style="dim")

    for c in clients:
        marker = "[bold cyan]★[/bold cyan]" if c["active"] else ""
        name   = f"[bold]{c['name']}[/bold]" if c["active"] else c["name"]
        table.add_row(
            marker,
            name,
            c["display_name"],
            c["database"],
            str(c["migrations"]),
            str(c["runs"]),
            c["created"],
        )

    console.print(table)
    active = next((c for c in clients if c["active"]), None)
    if active:
        console.print(
            f"\n[dim]Active client: [cyan]{active['name']}[/cyan] "
            f"({active['display_name']})[/dim]"
        )
        console.print(
            "[dim]Switch with: python agent.py client-switch <name>[/dim]"
        )


def print_client_detail(cfg: dict, paths: dict):
    """Print full detail for a single client."""
    console.print(Panel(
        f"[bold cyan]{cfg['display_name']}[/bold cyan]  "
        f"[dim]({cfg['name']})[/dim]",
        border_style="cyan", expand=False,
    ))

    db = cfg.get("db_config", {})
    console.print(f"\n  [bold]Database[/bold]")
    console.print(f"  Server:   [cyan]{db.get('server', '—')}[/cyan]")
    console.print(f"  Database: [cyan]{db.get('database', '—')}[/cyan]")
    console.print(f"  Auth:     [dim]{'Windows' if db.get('trusted_connection','yes')=='yes' else 'SQL Login'}[/dim]")

    console.print(f"\n  [bold]Sandbox[/bold]")
    console.print(
        f"  BAK path: [dim]{cfg.get('bak_path') or 'not set — add to client.json'}[/dim]"
    )

    console.print(f"\n  [bold]Workspace[/bold]")
    for label, key in [
        ("Migrations",  "migrations"),
        ("Reports",     "reports"),
        ("Deployments", "deployments"),
        ("Runs",        "runs"),
        ("History DB",  "history_db"),
    ]:
        console.print(f"  {label:<14} [dim]{paths[key]}[/dim]")

    if cfg.get("notes"):
        console.print(f"\n  [bold]Notes[/bold]")
        console.print(f"  [dim]{cfg['notes']}[/dim]")
