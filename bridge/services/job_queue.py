"""
bridge/services/job_queue.py

Phase 1 skeleton — data structures and DB schema only.
Full job execution wired in Phase 2.
"""

import json
import sqlite3
import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from queue import Queue
from typing import Any, Dict, Literal, Optional

# ── Job types / statuses ──────────────────────────────────────────────────────

JobType   = Literal["full_run", "batch_run", "analyze", "benchmark",
                    "sandbox_test", "watch", "deploy"]
JobStatus = Literal["pending", "running", "completed", "failed", "cancelled"]


@dataclass
class JobState:
    job_id:       str
    type:         str
    status:       JobStatus
    params:       dict
    result:       Optional[dict]  = None
    error:        Optional[str]   = None
    log_queue:    Queue           = field(default_factory=Queue)
    created_at:   str             = field(default_factory=lambda: _now())
    started_at:   Optional[str]   = None
    completed_at: Optional[str]   = None
    client:       str             = ""


def _now() -> str:
    return datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")


# ── DB helpers ────────────────────────────────────────────────────────────────

def _get_history_db_path() -> Path:
    """Resolve history.db path from project config."""
    try:
        import sys
        from pathlib import Path as P
        root = P(__file__).resolve().parent.parent.parent
        if str(root) not in sys.path:
            sys.path.insert(0, str(root))
        from config import HISTORY_DB
        return Path(HISTORY_DB)
    except Exception:
        return Path("history.db")


def ensure_jobs_table():
    """
    Add the `jobs` table to history.db if it doesn't exist.
    Called once at startup. Does not touch existing tables.
    """
    db_path = _get_history_db_path()
    db_path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(str(db_path))
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS jobs (
            job_id        TEXT PRIMARY KEY,
            type          TEXT NOT NULL,
            status        TEXT NOT NULL DEFAULT 'pending',
            params        TEXT,
            result        TEXT,
            error         TEXT,
            log_lines     INTEGER DEFAULT 0,
            created_at    TEXT NOT NULL,
            started_at    TEXT,
            completed_at  TEXT,
            client        TEXT
        );

        CREATE INDEX IF NOT EXISTS idx_jobs_status   ON jobs (status);
        CREATE INDEX IF NOT EXISTS idx_jobs_created  ON jobs (created_at DESC);
        CREATE INDEX IF NOT EXISTS idx_jobs_client   ON jobs (client);
    """)
    conn.commit()
    conn.close()


# ── Job queue (Phase 1 skeleton) ──────────────────────────────────────────────

class JobQueue:
    """
    Phase 1: in-memory job registry + DB persistence.
    Phase 2: adds ThreadPoolExecutor and tool execution.
    """

    _instance: Optional["JobQueue"] = None

    def __init__(self):
        self._jobs:  Dict[str, JobState] = {}
        self._lock   = threading.Lock()
        self._db     = _get_history_db_path()

    @classmethod
    def get(cls) -> "JobQueue":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def create(self, type: str, params: dict, client: str = "") -> JobState:
        """Create a job record (does not execute — Phase 2 adds execution)."""
        job = JobState(
            job_id   = str(uuid.uuid4()),
            type     = type,
            status   = "pending",
            params   = params,
            client   = client,
        )
        with self._lock:
            self._jobs[job.job_id] = job
        self._persist(job)
        return job

    def get_job(self, job_id: str) -> Optional[JobState]:
        with self._lock:
            return self._jobs.get(job_id)

    def list_jobs(
        self,
        status: Optional[str] = None,
        type:   Optional[str] = None,
        limit:  int = 20,
        offset: int = 0,
    ) -> list[JobState]:
        conn = sqlite3.connect(str(self._db))
        conn.row_factory = sqlite3.Row

        where = []
        params: list = []
        if status:
            where.append("status = ?")
            params.append(status)
        if type:
            where.append("type = ?")
            params.append(type)

        clause = f"WHERE {' AND '.join(where)}" if where else ""
        rows = conn.execute(
            f"SELECT * FROM jobs {clause} ORDER BY created_at DESC LIMIT ? OFFSET ?",
            params + [limit, offset],
        ).fetchall()
        conn.close()

        results = []
        for row in rows:
            j = JobState(
                job_id     = row["job_id"],
                type       = row["type"],
                status     = row["status"],
                params     = json.loads(row["params"] or "{}"),
                result     = json.loads(row["result"]) if row["result"] else None,
                error      = row["error"],
                created_at = row["created_at"] or "",
                started_at = row["started_at"],
                completed_at=row["completed_at"],
                client     = row["client"] or "",
            )
            results.append(j)
        return results

    def _persist(self, job: JobState):
        """Write job to history.db."""
        try:
            conn = sqlite3.connect(str(self._db))
            conn.execute("""
                INSERT OR REPLACE INTO jobs
                    (job_id, type, status, params, result, error,
                     created_at, started_at, completed_at, client)
                VALUES (?,?,?,?,?,?,?,?,?,?)
            """, (
                job.job_id,
                job.type,
                job.status,
                json.dumps(job.params),
                json.dumps(job.result) if job.result else None,
                job.error,
                job.created_at,
                job.started_at,
                job.completed_at,
                job.client,
            ))
            conn.commit()
            conn.close()
        except Exception:
            pass  # DB not available yet — in-memory only


# ── Module-level singleton ────────────────────────────────────────────────────

_queue = JobQueue.get()


def get_queue() -> JobQueue:
    return _queue
