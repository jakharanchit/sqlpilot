"""
/api/jobs  — job management and SSE streaming.
"""

import asyncio
import json
import queue as _queue_mod
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from bridge.services.job_queue import get_queue
from bridge.services.sse import complete_event, error_event, log_event, ping_event, step_event

router = APIRouter(prefix="/api/jobs", tags=["jobs"])


# ── Request / Response models ────────────────────────────────────────────────

class JobCreateRequest(BaseModel):
    type: str
    params: dict = {}


class JobCreateResponse(BaseModel):
    job_id: str
    status: str
    created_at: str
    type: str


# ── Routes ───────────────────────────────────────────────────────────────────

@router.post("", response_model=JobCreateResponse)
def create_job(body: JobCreateRequest):
    """Submit a new optimization job."""
    valid_types = {"full_run", "analyze", "benchmark", "sandbox_test", "watch", "deploy"}
    if body.type not in valid_types:
        raise HTTPException(status_code=400, detail=f"Unknown job type: {body.type}. Valid: {valid_types}")

    q   = get_queue()
    job = q.submit(body.type, body.params)

    return JobCreateResponse(
        job_id     = job.job_id,
        status     = job.status,
        created_at = job.created_at,
        type       = job.type,
    )


@router.get("")
def list_jobs(
    type:   Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    limit:  int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """List jobs from history, most recent first."""
    return get_queue().list_jobs(type=type, status=status, limit=limit, offset=offset)


@router.get("/{job_id}")
def get_job(job_id: str):
    """Get a single job by ID, including result."""
    q   = get_queue()
    job = q.get_job(job_id)
    if job:
        return q.job_as_dict(job)

    # Fall back to DB for completed jobs not in memory
    rows = q.list_jobs()
    for r in rows:
        if r["job_id"] == job_id:
            return r

    raise HTTPException(status_code=404, detail=f"Job {job_id} not found")


@router.delete("/{job_id}")
def cancel_job(job_id: str):
    """Cancel a running or queued job."""
    cancelled = get_queue().cancel(job_id)
    if not cancelled:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found or already finished")
    return {"cancelled": True, "job_id": job_id}


@router.get("/{job_id}/stream")
async def stream_job(job_id: str):
    """
    SSE stream for a job.  Client receives events:
      {"type": "log",      "line": "...", "ts": "HH:MM:SS"}
      {"type": "step",     "step": 3, "total": 9, "label": "..."}
      {"type": "complete", "result": {...}}
      {"type": "error",    "message": "..."}
      {"type": "ping"}
    """
    q   = get_queue()
    job = q.get_job(job_id)
    if not job:
        async def _not_found():
            yield error_event(f"Job {job_id} not found")
        return StreamingResponse(_not_found(), media_type="text/event-stream")

    async def _generate():
        while True:
            # Drain any pending events without blocking
            drained = 0
            while True:
                try:
                    event = job.log_queue.get_nowait()
                    drained += 1
                    if event["type"] == "log":
                        yield log_event(event["line"], event.get("ts", ""))
                    elif event["type"] == "step":
                        yield step_event(event["step"], event["total"], event["label"])
                    elif event["type"] == "complete":
                        yield complete_event(event.get("result") or {})
                        return
                    elif event["type"] == "error":
                        yield error_event(event.get("message", "Unknown error"))
                        return
                    # ping: ignore (we'll send our own below if idle)
                except _queue_mod.Empty:
                    break

            # Check if job finished but queue is empty (all drained)
            if drained == 0 and job.status in ("completed", "failed", "cancelled"):
                if job.status == "completed":
                    yield complete_event(job.result or {})
                else:
                    yield error_event(job.error or f"Job {job.status}")
                return

            # Keep-alive ping while waiting for next event
            yield ping_event()
            await asyncio.sleep(0.08)

    return StreamingResponse(
        _generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control":  "no-cache",
            "X-Accel-Buffering": "no",  # disable nginx buffering if behind a proxy
        },
    )
