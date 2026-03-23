"""
bridge/routers/clients.py
Phase 5 — Multi-client workspace management endpoints.
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from tools.client_manager import (
    list_clients,
    get_active_client,
    set_active_client,
    get_client_config,
    get_client_paths,
    create_client,
    update_client_config,
)
from tools.error_handler import ConfigError

router = APIRouter(prefix="/api/clients", tags=["clients"])


class NewClientBody(BaseModel):
    name:         str
    display_name: Optional[str] = ""
    server:       Optional[str] = ""
    database:     Optional[str] = ""
    bak_path:     Optional[str] = ""
    notes:        Optional[str] = ""


class UpdateClientBody(BaseModel):
    display_name: Optional[str] = None
    server:       Optional[str] = None
    database:     Optional[str] = None
    bak_path:     Optional[str] = None
    notes:        Optional[str] = None


def _client_detail(name: str) -> dict:
    """Returns a consistent {name, config, paths} dict for any client."""
    config = get_client_config(name)
    paths  = get_client_paths(name)
    # Strip password from config for safety
    if "db_config" in config and "password" in config["db_config"]:
        config["db_config"]["password"] = "***"
    return {"name": name, "config": config, "paths": paths}


@router.get("")
def get_clients():
    """List all client workspaces with summary stats."""
    return list_clients()


@router.get("/active")
def get_active():
    """Return full config and paths for the currently active client."""
    name = get_active_client()
    return _client_detail(name)


@router.post("/{name}/switch")
def switch_client(name: str):
    """Switch the active client. Returns the new active client's detail."""
    try:
        set_active_client(name)
    except ConfigError as e:
        raise HTTPException(404, str(e))
    return _client_detail(name)


@router.post("")
def new_client(body: NewClientBody):
    """Create a new client workspace from the body fields."""
    try:
        result = create_client(
            name         = body.name,
            display_name = body.display_name or "",
            server       = body.server       or "",
            database     = body.database     or "",
            bak_path     = body.bak_path     or "",
            notes        = body.notes        or "",
            set_active   = False,  # don't auto-switch — let user decide
        )
    except ConfigError as e:
        raise HTTPException(400, str(e))
    return _client_detail(result["name"])


@router.get("/{name}")
def get_client(name: str):
    """Return full config and paths for a named client."""
    try:
        return _client_detail(name)
    except Exception as e:
        raise HTTPException(404, str(e))


@router.put("/{name}")
def update_client(name: str, body: UpdateClientBody):
    """
    Update a client's settings. Only fields present in the body are changed
    (None fields are ignored by update_client_config).
    """
    try:
        cfg = update_client_config(
            client       = name,
            display_name = body.display_name,
            server       = body.server,
            database     = body.database,
            bak_path     = body.bak_path,
            notes        = body.notes,
        )
    except ConfigError as e:
        raise HTTPException(400, str(e))
    # Strip password
    if "db_config" in cfg and "password" in cfg["db_config"]:
        cfg["db_config"]["password"] = "***"
    return cfg


@router.delete("/{name}")
def delete_client(name: str):
    """
    Delete a client workspace folder.
    Safety rule: cannot delete the currently active client.
    """
    active = get_active_client()
    if name == active:
        raise HTTPException(
            400,
            f"Cannot delete the active client '{name}'. Switch to another client first."
        )

    import shutil
    from pathlib import Path

    try:
        from config import PROJECTS_DIR
    except ImportError:
        try:
            from config import BASE_DIR
            PROJECTS_DIR = str(Path(BASE_DIR) / "projects")
        except ImportError:
            PROJECTS_DIR = "projects"

    client_dir = Path(PROJECTS_DIR) / name
    if not client_dir.exists():
        raise HTTPException(404, f"Client '{name}' not found")

    shutil.rmtree(str(client_dir))
    return {"deleted": True, "name": name}
