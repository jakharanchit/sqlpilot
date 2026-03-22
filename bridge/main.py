"""
bridge/main.py
FastAPI application factory for SQL Agent V4 Web UI.

Dev mode:  FastAPI on :8000, Vite dev server on :5173
Prod mode: FastAPI on :8000 serves web/dist/ as static files
"""

import sys
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

# ── Resolve project root so we can import tools/ from agent project ──────────
# bridge/ lives one level below the project root (sql-agent/)
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# ── FastAPI app ───────────────────────────────────────────────────────────────
app = FastAPI(
    title="SQL Agent API",
    description="Backend bridge for SQL Optimization Agent V4 Web UI",
    version="4.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

# ── CORS — allow Vite dev server ──────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",   # Vite dev server
        "http://127.0.0.1:5173",
        "http://localhost:8000",   # Self (production build)
        "http://127.0.0.1:8000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ───────────────────────────────────────────────────────────────────
from bridge.routers import system, schema as schema_router

app.include_router(system.router,        prefix="/api/system",  tags=["system"])
app.include_router(schema_router.router, prefix="/api/schema",  tags=["schema"])

# ── Health check ──────────────────────────────────────────────────────────────
@app.get("/api/health", tags=["system"])
async def health():
    return {"status": "ok", "version": "4.0.0"}

# ── Serve React build in production ──────────────────────────────────────────
# The Vite build output is written to bridge/static/ (per vite.config.ts)
STATIC_DIR = Path(__file__).parent / "static"

if STATIC_DIR.exists() and any(STATIC_DIR.iterdir()):
    app.mount("/assets", StaticFiles(directory=STATIC_DIR / "assets"), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_spa(full_path: str):
        """Serve the React SPA for any non-API route."""
        index = STATIC_DIR / "index.html"
        return FileResponse(index)
