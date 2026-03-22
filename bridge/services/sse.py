"""SSE (Server-Sent Events) format helpers."""
import json
from typing import Any


def format_event(data: Any) -> str:
    """Format a server-sent event string (data-only, standard format)."""
    payload = json.dumps(data) if not isinstance(data, str) else data
    return f"data: {payload}\n\n"


def log_event(line: str, ts: str = "") -> str:
    return format_event({"type": "log", "line": line, "ts": ts})


def step_event(step: int, total: int, label: str) -> str:
    return format_event({"type": "step", "step": step, "total": total, "label": label})


def complete_event(result: dict) -> str:
    return format_event({"type": "complete", "result": result})


def error_event(message: str) -> str:
    return format_event({"type": "error", "message": message})


def ping_event() -> str:
    return format_event({"type": "ping"})
