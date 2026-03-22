"""
bridge/routers/sandbox.py
Phase 4 — Shadow DB sandbox endpoints.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from pathlib import Path

from tools.sandbox import list_shadows, destroy, _shadow_name, _shadow_exists
from tools.migrator import get_pending_migrations, list_migrations
from tools.reporter import _extract_apply_section
from config import BASE_DIR

try:
    from config import SANDBOX_BAK_PATH
except ImportError:
    SANDBOX_BAK_PATH = ""

router = APIRouter(prefix="/api/sandbox", tags=["sandbox"])


class SandboxTestRequest(BaseModel):
    migration_numbers: Optional[List[int]] = None
    bak_path:          Optional[str]       = None
    threshold_pct:     float               = 30.0


@router.post("/test")
def run_sandbox_test_endpoint(body: SandboxTestRequest):
    """
    Enqueues a sandbox test as a background job.
    Returns a Job — client streams progress via /api/jobs/{id}/stream.
    """
    from bridge.services.job_queue import enqueue_job

    # Resolve which migrations to test
    if body.migration_numbers:
        migrations = [m for m in list_migrations()
                      if m["number"] in body.migration_numbers]
    else:
        migrations = get_pending_migrations()

    # Extract apply SQL from each migration file
    sql_statements: List[str] = []
    for m in migrations:
        # Try client-aware path first, fall back to global migrations dir
        try:
            from tools.client_manager import get_client_paths
            migrations_dir = get_client_paths()["migrations"]
        except Exception:
            try:
                from config import MIGRATIONS_DIR
                migrations_dir = MIGRATIONS_DIR
            except Exception:
                migrations_dir = str(Path(BASE_DIR) / "migrations")

        mig_file = Path(migrations_dir) / m["filename"]
        if mig_file.exists():
            apply_sql = _extract_apply_section(mig_file.read_text(encoding="utf-8"))
            if apply_sql and "No apply SQL" not in apply_sql:
                sql_statements.append(apply_sql)

    # Build regression queries from recent history
    from tools.history import get_history
    history_runs = get_history(limit=5)
    regression_queries = [
        {
            "label":       r.get("label") or r.get("query_preview", "")[:30],
            "sql":         r.get("query_preview", ""),
            "baseline_ms": r.get("after_ms"),
        }
        for r in history_runs
        if r.get("after_ms") and r.get("query_preview")
    ]

    job = enqueue_job({
        "type":               "sandbox_test",
        "sql_statements":     sql_statements,
        "regression_queries": regression_queries,
        "bak_path":           body.bak_path or SANDBOX_BAK_PATH or None,
        "threshold_pct":      body.threshold_pct,
        "migration_numbers":  [m["number"] for m in migrations],
    })
    return job


@router.get("/shadows")
def get_shadows():
    """List all shadow databases currently on SQL Server."""
    return list_shadows()


@router.delete("/shadows/{name}")
def destroy_shadow(name: str):
    """Destroy a named shadow database."""
    destroyed = destroy(name)
    return {"destroyed": destroyed, "name": name}


@router.get("/config")
def sandbox_config():
    """Return sandbox configuration status."""
    bak = SANDBOX_BAK_PATH or ""
    return {
        "configured":  bool(bak),
        "bak_path":    bak,
        "bak_exists":  bool(bak) and Path(bak).exists(),
        "shadow_name": _shadow_name(),
    }
