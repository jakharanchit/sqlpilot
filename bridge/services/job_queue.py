"""
Job queue service.

Runs optimization pipeline jobs in background threads.
Streams output via per-job log queues consumed by SSE endpoints.
Persists job state to jobs.db (SQLite).
"""

import json
import queue
import re
import sqlite3
import sys
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime
from io import StringIO
from pathlib import Path
from typing import Any, Dict, List, Optional

# ── path setup so bridge can import tools/ ─────────────────────────────────
_ROOT = Path(__file__).parent.parent.parent  # project root
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from config import BASE_DIR  # noqa: E402

JOBS_DB = Path(BASE_DIR) / "jobs.db"

# ANSI escape stripper (Rich may emit these even with no_color=True on some systems)
_ANSI = re.compile(r"\x1b\[[0-9;]*[a-zA-Z]")
# Step detector: "Step 1/9 — ..."
_STEP_RE = re.compile(r"Step\s+(\d+)/(\d+)\s*[—-]?\s*(.*)")


# ── Job data ────────────────────────────────────────────────────────────────

@dataclass
class JobState:
    job_id: str
    type: str
    params: dict
    status: str  # queued | running | completed | failed | cancelled
    created_at: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    result: Optional[dict] = None
    error: Optional[str] = None
    current_step: int = 0
    total_steps: int = 9
    step_label: str = ""
    # in-memory log queue — consumed by SSE endpoint
    log_queue: queue.Queue = field(default_factory=queue.Queue, repr=False)


# ── SQLite helpers ──────────────────────────────────────────────────────────

def _get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(str(JOBS_DB))
    conn.row_factory = sqlite3.Row
    return conn


def _ensure_schema():
    with _get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS jobs (
                job_id       TEXT PRIMARY KEY,
                type         TEXT NOT NULL,
                params       TEXT NOT NULL,
                status       TEXT NOT NULL DEFAULT 'queued',
                created_at   TEXT NOT NULL,
                started_at   TEXT,
                completed_at TEXT,
                result       TEXT,
                error        TEXT,
                current_step INTEGER DEFAULT 0,
                total_steps  INTEGER DEFAULT 9,
                step_label   TEXT DEFAULT ''
            )
        """)
        conn.commit()


def _upsert_job(job: JobState):
    with _get_conn() as conn:
        conn.execute("""
            INSERT INTO jobs
                (job_id, type, params, status, created_at, started_at, completed_at,
                 result, error, current_step, total_steps, step_label)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
            ON CONFLICT(job_id) DO UPDATE SET
                status       = excluded.status,
                started_at   = excluded.started_at,
                completed_at = excluded.completed_at,
                result       = excluded.result,
                error        = excluded.error,
                current_step = excluded.current_step,
                total_steps  = excluded.total_steps,
                step_label   = excluded.step_label
        """, (
            job.job_id, job.type,
            json.dumps(job.params),
            job.status,
            job.created_at, job.started_at, job.completed_at,
            json.dumps(job.result) if job.result else None,
            job.error,
            job.current_step, job.total_steps, job.step_label,
        ))
        conn.commit()


def _row_to_dict(row: sqlite3.Row) -> dict:
    d = dict(row)
    d["params"] = json.loads(d["params"]) if d["params"] else {}
    d["result"] = json.loads(d["result"]) if d["result"] else None
    return d


# ── Console redirect ─────────────────────────────────────────────────────────

class _JobConsole:
    """
    Drop-in replacement for Rich Console that:
    1. Renders markup to plain text via an in-memory Rich Console
    2. Strips ANSI escapes
    3. Puts the clean text + metadata into the job's log_queue
    4. Detects "Step N/M" lines and emits step events too
    """

    def __init__(self, job: JobState):
        self._job = job
        # Import here so the real Rich Console class is captured, not our replacement
        from rich.console import Console as _RichConsole
        self._RichConsole = _RichConsole

    def _ts(self) -> str:
        return datetime.now().strftime("%H:%M:%S")

    def print(self, *args, **kwargs):
        buf = StringIO()
        c = self._RichConsole(
            file=buf,
            highlight=False,
            no_color=True,
            force_terminal=False,
            width=200,
        )
        c.print(*args, **kwargs)
        raw = buf.getvalue()
        text = _ANSI.sub("", raw).rstrip()

        if not text:
            return

        ts = self._ts()

        # Emit log event for each non-empty line
        for line in text.splitlines():
            stripped = line.rstrip()
            if not stripped:
                continue
            self._job.log_queue.put({"type": "log", "line": stripped, "ts": ts})

            # Detect step lines → emit step event
            m = _STEP_RE.search(stripped)
            if m:
                step  = int(m.group(1))
                total = int(m.group(2))
                label = m.group(3).strip()
                self._job.current_step = step
                self._job.total_steps  = total
                self._job.step_label   = label
                self._job.log_queue.put({
                    "type": "step", "step": step, "total": total, "label": label
                })

    def __getattr__(self, name):
        # Proxy any other attribute access (e.g. .status, .width) to a no-op or default
        return lambda *a, **kw: None


def _patch_consoles(job: JobState) -> dict:
    """Replace console in all tool modules. Returns originals for restore."""
    originals = {}
    module_names = [
        "tools.optimizer",
        "tools.pipeline",
        "tools.schema",
        "tools.executor",
        "tools.benchmarker",
        "tools.migrator",
        "tools.reporter",
        "tools.history",
        "tools.watcher",
        "tools.sandbox",
        "tools.lv_monitor",
        "tools.git_manager",
        "tools.planner",
    ]
    jc = _JobConsole(job)
    for name in module_names:
        try:
            mod = sys.modules.get(name)
            if mod is None:
                import importlib
                mod = importlib.import_module(name)
            if hasattr(mod, "console"):
                originals[name] = (mod, mod.console)
                mod.console = jc
        except Exception:
            pass
    return originals


def _restore_consoles(originals: dict):
    for name, (mod, orig) in originals.items():
        try:
            mod.console = orig
        except Exception:
            pass


# ── Job execution ────────────────────────────────────────────────────────────

def _auto_fetch_schemas(query: str) -> list:
    from tools.schema import get_schema, list_all_tables, list_all_views, get_view_definition
    all_tables  = list_all_tables()
    all_views   = list_all_views()
    all_objects = all_tables + all_views
    query_upper = query.upper()
    found = [obj for obj in all_objects if obj.upper() in query_upper]
    if not found:
        found = all_tables

    schemas = []
    for obj in found:
        if obj in all_tables:
            schemas.append(get_schema(obj))
        else:
            vd = get_view_definition(obj)
            for ref in vd.get("referenced_tables", []):
                if ref in all_tables:
                    s = get_schema(ref)
                    if s not in schemas:
                        schemas.append(s)
    return schemas


def _run_job(job: JobState):
    """Execute a job in a background thread."""
    job.status     = "running"
    job.started_at = datetime.now().isoformat()
    _upsert_job(job)

    originals = _patch_consoles(job)

    try:
        result = _dispatch(job)
        job.status       = "completed"
        job.result       = result
        job.completed_at = datetime.now().isoformat()
        job.current_step = job.total_steps
        # Signal completion via queue
        job.log_queue.put({"type": "complete", "result": result})

    except Exception as exc:
        job.status       = "failed"
        job.error        = str(exc)
        job.completed_at = datetime.now().isoformat()
        job.log_queue.put({"type": "error", "message": str(exc)})

    finally:
        _restore_consoles(originals)
        _upsert_job(job)


def _dispatch(job: JobState) -> dict:
    t   = job.type
    p   = job.params

    if t == "full_run":
        from tools.pipeline import run_single
        return run_single(
            query          = p["query"],
            label          = p.get("label", ""),
            benchmark_runs = p.get("benchmark_runs"),
            skip_deploy    = p.get("no_deploy", False),
        )

    elif t == "analyze":
        from tools.optimizer import optimize_query
        schema_list = _auto_fetch_schemas(p["query"])
        result = optimize_query(p["query"], schema_list)
        return {"success": True, "optimization": result}

    elif t == "benchmark":
        from tools.benchmarker import benchmark_query
        result = benchmark_query(
            original_query  = p["before"],
            optimized_query = p["after"],
            label           = p.get("label", "benchmark"),
            runs            = p.get("runs"),
        )
        return {"success": "error" not in result, "benchmark": result}

    elif t == "sandbox_test":
        from tools.sandbox import run_sandbox_test
        result = run_sandbox_test(
            sql_statements     = p.get("sql_statements", []),
            regression_queries = p.get("regression_queries", []),
            bak_path           = p.get("bak_path"),
            threshold_pct      = p.get("threshold_pct", 30.0),
        )
        return result

    elif t == "watch":
        from tools.watcher import run_watch
        return run_watch(force=p.get("force", False))

    elif t == "deploy":
        from tools.reporter import generate_deployment_package
        return generate_deployment_package(
            client      = p.get("client"),
            include_all = p.get("include_all", False),
        )

    else:
        raise ValueError(f"Unknown job type: {t}")


# ── Queue singleton ──────────────────────────────────────────────────────────

class JobQueue:
    def __init__(self):
        _ensure_schema()
        self._jobs:    Dict[str, JobState] = {}
        self._lock     = threading.Lock()
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="job-worker")

    def create(self, type: str, params: dict) -> JobState:
        job = JobState(
            job_id     = str(uuid.uuid4()),
            type       = type,
            params     = params,
            status     = "queued",
            created_at = datetime.now().isoformat(),
        )
        with self._lock:
            self._jobs[job.job_id] = job
        _upsert_job(job)
        return job

    def submit(self, type: str, params: dict) -> JobState:
        job = self.create(type, params)
        self._executor.submit(_run_job, job)
        return job

    def get_job(self, job_id: str) -> Optional[JobState]:
        with self._lock:
            return self._jobs.get(job_id)

    def list_jobs(
        self,
        type:   Optional[str] = None,
        status: Optional[str] = None,
        limit:  int = 50,
        offset: int = 0,
    ) -> List[dict]:
        with _get_conn() as conn:
            where  = []
            params = []
            if type:
                where.append("type = ?")
                params.append(type)
            if status:
                where.append("status = ?")
                params.append(status)
            clause = f"WHERE {' AND '.join(where)}" if where else ""
            rows   = conn.execute(
                f"SELECT * FROM jobs {clause} ORDER BY created_at DESC LIMIT ? OFFSET ?",
                params + [limit, offset],
            ).fetchall()
        return [_row_to_dict(r) for r in rows]

    def cancel(self, job_id: str) -> bool:
        job = self.get_job(job_id)
        if not job:
            return False
        if job.status in ("completed", "failed", "cancelled"):
            return False
        job.status = "cancelled"
        job.log_queue.put({"type": "error", "message": "Job cancelled by user"})
        _upsert_job(job)
        return True

    def job_as_dict(self, job: JobState) -> dict:
        return {
            "job_id":       job.job_id,
            "type":         job.type,
            "params":       job.params,
            "status":       job.status,
            "created_at":   job.created_at,
            "started_at":   job.started_at,
            "completed_at": job.completed_at,
            "result":       job.result,
            "error":        job.error,
            "current_step": job.current_step,
            "total_steps":  job.total_steps,
            "step_label":   job.step_label,
        }


# ── Global singleton ─────────────────────────────────────────────────────────

_queue: Optional[JobQueue] = None


def get_queue() -> JobQueue:
    global _queue
    if _queue is None:
        _queue = JobQueue()
    return _queue
