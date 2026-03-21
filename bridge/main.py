# ============================================================
# bridge/main.py
# FastAPI Bridge Layer — connects the Web UI to the SQL Agent.
# ============================================================

import uuid
from typing import Optional
from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from bridge.streamer import tail_logs
from tools.history import create_job, update_job, get_job, record_from_pipeline
from tools.pipeline import run_single

app = FastAPI(title="SQL Optimization Agent Bridge")

# ============================================================
# MODELS
# ============================================================

class FullRunRequest(BaseModel):
    query:          str
    label:          Optional[str] = None
    benchmark_runs: Optional[int] = None
    skip_deploy:    bool = False

class JobStatus(BaseModel):
    job_id: str
    status: str
    created_at: str
    started_at: Optional[str] = None
    finished_at: Optional[str] = None
    result: Optional[dict] = None
    error: Optional[str] = None

# ============================================================
# BACKGROUND WORKERS
# ============================================================

def background_full_run(job_id: str, req: FullRunRequest):
    \"\"\"
    Worker function that executes the long-running pipeline.
    \"\"\"
    try:
        update_job(job_id, status='running')
        
        # Execute the mature synchronous logic from tools/pipeline.py
        result = run_single(
            query          = req.query,
            label          = req.label or \"\",
            benchmark_runs = req.benchmark_runs,
            skip_deploy    = req.skip_deploy
        )
        
        if result.get(\"success\"):
            # Record to history.db (runs table) as well
            record_from_pipeline(result)
            update_job(job_id, status='completed', result=result)
        else:
            errors = \", \".join(result.get(\"errors\", []))
            update_job(job_id, status='failed', error=f\"Pipeline failed: {errors}\")
            
    except Exception as e:
        update_job(job_id, status='failed', error=str(e))

# ============================================================
# ENDPOINTS
# ============================================================

@app.post(\"/api/full-run\", status_code=202)
async def trigger_full_run(req: FullRunRequest, bg_tasks: BackgroundTasks):
    \"\"\"
    Non-blocking endpoint to start a SQL optimization pipeline.
    \"\"\"
    job_id = str(uuid.uuid4())
    create_job(job_id, job_type='full-run', payload=req.dict())
    
    # Offload to background thread
    bg_tasks.add_task(background_full_run, job_id, req)
    
    return {\"job_id\": job_id, \"status\": \"pending\"}

@app.get(\"/api/jobs/{job_id}\", response_model=JobStatus)
async def get_job_status(job_id: str):
    \"\"\"
    Poll the status of a long-running job.
    \"\"\"
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=\"Job not found\")
    
    return JobStatus(
        job_id      = job['id'],
        status      = job['status'],
        created_at  = job['created_at'],
        started_at  = job['started_at'],
        finished_at = job['finished_at'],
        result      = job['result'],
        error       = job['error']
    )

@app.get(\"/api/logs/stream\")
async def stream_agent_logs():
    \"\"\"
    SSE endpoint that pipes app_logger.py output to the browser.
    \"\"\"
    return StreamingResponse(
        tail_logs(), 
        media_type=\"text/event-stream\"
    )

# ============================================================
# HEALTH & UTILITIES (Mapping simpler commands)
# ============================================================

@app.get(\"/api/health\")
async def health_check():
    from tools.config_validator import run_checks
    return run_checks()

@app.get(\"/api/db/objects\")
async def list_db_objects():
    from tools.schema import list_all_tables, list_all_views
    return {
        \"tables\": list_all_tables(),
        \"views\":  list_all_views()
    }
