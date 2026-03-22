"""
bridge/routers/system.py

GET /api/system/stats   — hardware metrics (CPU, RAM, VRAM, Ollama, DB)
GET /api/system/check   — full pre-flight config_validator results
PUT /api/system/poll    — frontend tells bridge to change poll rate
"""

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from bridge.services.hardware import get_current_stats, set_poll_interval

router = APIRouter()


# ── /api/system/stats ─────────────────────────────────────────────────────────

@router.get("/stats")
async def get_stats():
    """
    Returns current hardware snapshot.
    Served from background-thread cache — always fast.
    Frontend polls this at 2s (idle) or 500ms (active inference).
    """
    stats = get_current_stats()
    if stats is None:
        return JSONResponse(status_code=503, content={"error": "Stats not yet available"})

    payload: dict = {
        "cpu_usage":    stats.cpu_usage,
        "ram_usage_mb": stats.ram_usage_mb,
        "ram_total_mb": stats.ram_total_mb,
        "ram_pct":      stats.ram_pct,
        "gpu":          None,
        "gpu_source":   stats.gpu_source,
        "ollama": {
            "status":        stats.ollama.status,
            "active_models": stats.ollama.active_models,
            "url":           stats.ollama.url,
        },
        "db": {
            "status":   stats.db.status,
            "database": stats.db.database,
            "server":   stats.db.server,
            "error":    stats.db.error,
        },
    }

    if stats.gpu:
        payload["gpu"] = {
            "name":            stats.gpu.name,
            "vram_usage_mb":   stats.gpu.vram_usage_mb,
            "vram_total_mb":   stats.gpu.vram_total_mb,
            "vram_pct":        stats.gpu.vram_pct,
            "utilization_pct": stats.gpu.utilization_pct,
            "source":          stats.gpu.source,
        }

    return payload


# ── /api/system/check ─────────────────────────────────────────────────────────

@router.get("/check")
async def get_check():
    """
    Runs config_validator.run_checks() and returns structured results.
    This is slow (~5s) — called once on page load, not polled.
    """
    try:
        # Import config_validator from project tools
        from tools.config_validator import run_checks, _check_config_fields, \
            _check_database, _check_ollama, _check_directories, \
            _check_migrations, _check_history_db, _check_schema_snapshot

        all_results = []
        checks = [
            _check_config_fields,
            _check_database,
            _check_ollama,
            _check_directories,
            _check_migrations,
            _check_history_db,
            _check_schema_snapshot,
        ]
        for fn in checks:
            try:
                all_results.extend(fn())
            except Exception as e:
                from tools.config_validator import CheckResult
                r = CheckResult(fn.__name__, "unknown")
                r.fail(f"Check crashed: {e}")
                all_results.append(r)

        critical_failures = [r for r in all_results if not r.passed and r.critical]
        warnings          = [r for r in all_results if r.warning]

        return {
            "passed":            len(critical_failures) == 0,
            "critical_failures": len(critical_failures),
            "warnings":          len(warnings),
            "checks": [
                {
                    "name":     r.name,
                    "category": r.category,
                    "passed":   r.passed,
                    "warning":  r.warning,
                    "critical": r.critical,
                    "message":  r.message,
                    "fix":      r.fix,
                }
                for r in all_results
            ],
        }

    except ImportError:
        # Tools not importable in isolated dev environment
        return {
            "passed": True,
            "critical_failures": 0,
            "warnings": 0,
            "checks": [
                {
                    "name": "Config validator",
                    "category": "System",
                    "passed": True,
                    "warning": True,
                    "critical": False,
                    "message": "tools/ not importable from bridge — run from project root",
                    "fix": "Start bridge from the sql-agent/ project root",
                }
            ],
        }


# ── /api/system/poll ─────────────────────────────────────────────────────────

@router.put("/poll")
async def set_poll_rate(interval_ms: int = 2000):
    """
    Frontend calls this to adjust hardware polling rate.
    500ms during active inference, 2000ms idle.
    """
    set_poll_interval(interval_ms / 1000)
    return {"interval_ms": interval_ms}
