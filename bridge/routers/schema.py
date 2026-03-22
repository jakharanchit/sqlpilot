"""
bridge/routers/schema.py

GET /api/schema/tables          — list all tables
GET /api/schema/views           — list all views
GET /api/schema/table/{name}    — columns, indexes, row count
GET /api/schema/view/{name}     — view DDL + referenced tables
"""

from fastapi import APIRouter, HTTPException

router = APIRouter()


def _import_schema():
    """Lazy import to give a clear error if tools/ is not on the path."""
    try:
        from tools import schema as _schema
        return _schema
    except ImportError as e:
        raise HTTPException(
            status_code=503,
            detail=f"tools/schema.py not importable. Start bridge from project root. ({e})",
        )


# ── /api/schema/tables ───────────────────────────────────────────────────────

@router.get("/tables")
async def list_tables():
    schema = _import_schema()
    try:
        tables = schema.list_all_tables()
        return {"tables": tables, "count": len(tables)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── /api/schema/views ────────────────────────────────────────────────────────

@router.get("/views")
async def list_views():
    schema = _import_schema()
    try:
        views = schema.list_all_views()
        return {"views": views, "count": len(views)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── /api/schema/table/{name} ─────────────────────────────────────────────────

@router.get("/table/{name}")
async def get_table(name: str):
    schema = _import_schema()
    try:
        result = schema.get_schema(name)
        if "error" in result:
            raise HTTPException(status_code=404, detail=result["error"])
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── /api/schema/view/{name} ──────────────────────────────────────────────────

@router.get("/view/{name}")
async def get_view(name: str):
    schema = _import_schema()
    try:
        result = schema.get_view_definition(name)
        if "error" in result:
            raise HTTPException(status_code=404, detail=result["error"])
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── /api/schema/all — combined snapshot for sidebar tree ─────────────────────

@router.get("/all")
async def get_all():
    """
    Returns tables + views in a single call.
    Used by the sidebar schema tree on initial load.
    """
    schema = _import_schema()
    try:
        tables = schema.list_all_tables()
        views  = schema.list_all_views()
        return {
            "tables": tables,
            "views":  views,
            "table_count": len(tables),
            "view_count":  len(views),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
