from fastapi import APIRouter, Query, HTTPException
from tools.history import (
    get_history,
    get_stats,
    get_trend,
    get_regressions,
    get_top_improvements,
    compare_runs,
)

router = APIRouter(prefix="/api/history", tags=["history"])


@router.get("")
def list_history(
    query:       str  = Query(None),
    table:       str  = Query(None),
    type:        str  = Query(None),
    limit:       int  = Query(50),
    offset:      int  = Query(0),
    top:         bool = Query(False),
    regressions: bool = Query(False),
):
    if top:
        return get_top_improvements(limit=limit)
    if regressions:
        return get_regressions()

    # Fetch with enough headroom to support offset slicing
    runs = get_history(query=query, table_name=table, limit=limit + offset)

    # Filter by run_type if provided
    if type:
        runs = [r for r in runs if r.get("run_type") == type]

    return runs[offset:]


@router.get("/stats")
def history_stats():
    return get_stats()


@router.get("/trend")
def trend(
    table:      str = Query(None),
    query_hash: str = Query(None),
):
    if not table and not query_hash:
        raise HTTPException(400, "Provide table or query_hash")
    return get_trend(table_name=table, query_hash=query_hash)


@router.get("/compare")
def compare(
    a: int = Query(...),
    b: int = Query(...),
):
    result = compare_runs(a, b)
    if "error" in result:
        raise HTTPException(404, result["error"])
    return result


@router.get("/{run_id}")
def get_run(run_id: int):
    # Pull a broad slice and find the matching ID
    runs = get_history(limit=5000)
    match = next((r for r in runs if r["id"] == run_id), None)
    if not match:
        raise HTTPException(404, f"Run {run_id} not found")
    return match


@router.delete("/{run_id}")
def delete_run(run_id: int):
    from tools.history import _get_conn
    conn = _get_conn()
    conn.execute("DELETE FROM runs WHERE id = ?", (run_id,))
    conn.commit()
    conn.close()
    return {"deleted": True, "id": run_id}
