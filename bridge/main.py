"""
bridge/main.py — FastAPI application for SQL Optimization Agent web UI.

Serves:
  /api/health        — quick liveness check
  /api/system/*      — hardware stats, config check
  /api/schema/*      — DB schema inspection
  /api/jobs/*        — job lifecycle + SSE streaming
  /                  — React static files (production build)
"""
import sys
from pathlib import Path

# Allow importing from project root (tools/, config.py, etc.)
_ROOT = Path(__file__).parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from bridge.routers import jobs, schema, system, history, migrations
from bridge.routers import deploy, sandbox, clients, models, plan, settings
from bridge.services.hardware import HardwareMonitor

app = FastAPI(
    title       = "SQL Optimization Agent API",
    description = "Bridge between the React UI and the local Python CLI tools",
    version     = "7.0.0",
)

# ── CORS (dev: allow Vite dev server) ────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins     = ["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials = True,
    allow_methods     = ["*"],
    allow_headers     = ["*"],
)

# ── Routers ──────────────────────────────────────────────────────────────────
app.include_router(system.router)
app.include_router(schema.router)
app.include_router(jobs.router)
app.include_router(history.router)
app.include_router(migrations.router)
app.include_router(deploy.router)
app.include_router(sandbox.router)
app.include_router(clients.router)
app.include_router(models.router)
app.include_router(plan.router)
app.include_router(settings.router)

@app.get("/api/health")
def health():
    return {"status": "ok", "service": "sql-agent-bridge"}


# ── On startup: begin hardware polling ───────────────────────────────────────
@app.on_event("startup")
def startup_event():
    svc = HardwareMonitor.get()
    svc.set_interval(2.0)
    svc.start()


@app.on_event("shutdown")
def shutdown_event():
    svc = HardwareMonitor.get()
    svc.stop()


# ── Serve React build (production) ───────────────────────────────────────────
from fastapi.responses import FileResponse
_STATIC = Path(__file__).parent / "static"

if _STATIC.exists():
    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_spa(full_path: str):
        """Serve the React SPA for any non-API route."""
        path = _STATIC / full_path
        if path.is_file():
            return FileResponse(path)
        
        index = _STATIC / "index.html"
        return FileResponse(index)