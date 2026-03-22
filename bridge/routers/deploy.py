"""
bridge/routers/deploy.py
Phase 4 — Deployment package endpoints.
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel
from typing import Optional
from pathlib import Path
from datetime import datetime

from tools.migrator import get_pending_migrations, list_migrations
from tools.reporter import (
    generate_deployment_package,
    _build_deploy_sql,
    _build_rollback_sql,
)
from config import BASE_DIR

# Client-aware path resolution with fallback
try:
    from tools.client_manager import get_active_client, get_client_paths
    def _deployments_dir() -> str:
        return get_client_paths()["deployments"]
    def _active_client() -> str:
        return get_active_client()
except Exception:
    try:
        from config import DEPLOYMENTS_DIR, ACTIVE_CLIENT
        def _deployments_dir() -> str:
            return DEPLOYMENTS_DIR
        def _active_client() -> str:
            return ACTIVE_CLIENT
    except Exception:
        def _deployments_dir() -> str:
            return str(Path(BASE_DIR) / "deployments")
        def _active_client() -> str:
            return "client"

router = APIRouter(prefix="/api/deploy", tags=["deploy"])

ALLOWED_FILES = {
    "deploy.sql", "rollback.sql", "pre_flight.md",
    "technical_report.md", "walkthrough.md", "session_log.txt",
}


class GenerateRequest(BaseModel):
    client:      Optional[str] = None
    include_all: bool          = False


@router.get("/preview")
def deploy_preview():
    """
    Build deploy.sql + rollback.sql in memory WITHOUT writing to disk.
    Returns full content for Monaco display.
    """
    client     = _active_client()
    migrations = get_pending_migrations()

    if not migrations:
        return {
            "client":             client,
            "migrations":         [],
            "deploy_sql":         "-- No pending migrations",
            "rollback_sql":       "-- No pending migrations",
            "migration_count":    0,
            "has_schema_changes": False,
        }

    deploy_sql   = _build_deploy_sql(migrations, client)
    rollback_sql = _build_rollback_sql(migrations, client)

    has_schema = any(
        m.get("index_scripts") or
        (m.get("reason") and "INDEX" in m.get("reason", "").upper())
        for m in migrations
    )

    return {
        "client":             client,
        "migrations":         migrations,
        "deploy_sql":         deploy_sql,
        "rollback_sql":       rollback_sql,
        "migration_count":    len(migrations),
        "has_schema_changes": has_schema,
    }


@router.post("/generate")
def generate_package(body: GenerateRequest = GenerateRequest()):
    """
    Calls generate_deployment_package() — writes files to disk.
    Returns package metadata.
    """
    result = generate_deployment_package(
        client      = body.client,
        include_all = body.include_all,
    )
    if "error" in result:
        raise HTTPException(400, result["error"])

    # Enrich with created_at timestamp from folder mtime
    pkg_path = Path(result["package_path"])
    result["created_at"] = (
        datetime.fromtimestamp(pkg_path.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S")
        if pkg_path.exists() else ""
    )
    return result


@router.get("/packages")
def list_packages():
    """List all deployment packages in the deployments/ folder."""
    deploy_dir = Path(_deployments_dir())
    if not deploy_dir.exists():
        return []

    packages = []
    for folder in sorted(deploy_dir.iterdir(), reverse=True):
        if not folder.is_dir():
            continue
        files = [f.name for f in folder.iterdir() if f.is_file()]
        # Extract client name from folder name (everything before last two _YYYY_MM_DD_HHMM segments)
        parts = folder.name.rsplit("_", 4)
        client_name = "_".join(parts[:-4]) if len(parts) > 4 else folder.name
        packages.append({
            "folder_name":  folder.name,
            "package_path": str(folder),
            "files":        sorted(files),
            "created_at":   datetime.fromtimestamp(
                folder.stat().st_mtime
            ).strftime("%Y-%m-%d %H:%M:%S"),
            "client":       client_name or folder.name,
            "migrations":   [],  # lightweight listing — don't re-parse migration files
        })
    return packages


@router.get("/packages/{folder_name}/files/{filename}")
def get_file_content(folder_name: str, filename: str):
    """Return raw file content as plain text for Monaco/pre display."""
    # Sanitize — prevent path traversal
    if ".." in folder_name or ".." in filename or "/" in filename or "\\" in filename:
        raise HTTPException(400, "Invalid path")
    if filename not in ALLOWED_FILES:
        raise HTTPException(400, f"File not allowed: {filename}")

    file_path = Path(_deployments_dir()) / folder_name / filename
    if not file_path.exists():
        raise HTTPException(404, f"File not found: {filename} in {folder_name}")

    return PlainTextResponse(
        file_path.read_text(encoding="utf-8"),
        media_type="text/plain",
    )
