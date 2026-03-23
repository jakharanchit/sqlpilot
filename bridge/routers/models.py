"""
bridge/routers/models.py
Phase 5 — Ollama model management endpoints.
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import requests as _req

try:
    from config import OLLAMA_BASE_URL, MODELS
except ImportError:
    OLLAMA_BASE_URL = "http://localhost:11434"
    MODELS = {}

router = APIRouter(prefix="/api/models", tags=["models"])


def _bytes_to_gb(b: int) -> str:
    return f"{b / 1_073_741_824:.1f} GB"


def _ollama(path: str, method: str = "GET", **kwargs):
    """Simple wrapper around the Ollama HTTP API."""
    url = f"{OLLAMA_BASE_URL}{path}"
    try:
        r = _req.request(method, url, timeout=10, **kwargs)
        r.raise_for_status()
        return r
    except _req.exceptions.ConnectionError:
        raise HTTPException(503, "Ollama is not running. Start it with: ollama serve")
    except _req.exceptions.HTTPError as e:
        raise HTTPException(r.status_code, str(e))


@router.get("")
def list_models():
    """
    Returns all models pulled in Ollama plus which are configured as active
    (optimizer / reasoner from config.py).
    """
    r = _ollama("/api/tags")
    raw_models = r.json().get("models", [])

    models = []
    for m in raw_models:
        details = m.get("details", {})
        models.append({
            "name":           m["name"],
            "size":           m.get("size", 0),
            "size_gb":        _bytes_to_gb(m.get("size", 0)),
            "digest":         m.get("digest", "")[:12],
            "modified_at":    m.get("modified_at", ""),
            "family":         details.get("family", ""),
            "parameter_size": details.get("parameter_size", ""),
            "quantization":   details.get("quantization_level", ""),
        })

    pulled_names = {m["name"] for m in models}
    active = {
        "optimizer":           MODELS.get("optimizer", ""),
        "reasoner":            MODELS.get("reasoner", ""),
        "optimizer_available": MODELS.get("optimizer", "") in pulled_names,
        "reasoner_available":  MODELS.get("reasoner", "") in pulled_names,
    }

    return {"models": models, "active": active}


@router.get("/running")
def running_models():
    """Returns models currently loaded in Ollama memory."""
    r = _ollama("/api/ps")
    raw = r.json().get("models", [])
    return [
        {
            "name":         m["name"],
            "size_vram":    m.get("size_vram", 0),
            "size_vram_gb": _bytes_to_gb(m.get("size_vram", 0)),
            "expires_at":   m.get("expires_at", ""),
        }
        for m in raw
    ]


class PullRequest(BaseModel):
    name: str


@router.post("/pull")
def pull_model(body: PullRequest):
    """
    Enqueues a model pull as a background job.
    Stream download progress via GET /api/jobs/{id}/stream.
    """
    from bridge.services.job_queue import enqueue_job
    job = enqueue_job({
        "type":       "pull_model",
        "model_name": body.name.strip(),
    })
    return job


@router.delete("/{model_name:path}")
def delete_model(model_name: str):
    """
    Deletes a model from Ollama.
    model_name may contain a colon (e.g. "qwen2.5-coder:14b") — matched via :path.
    """
    _ollama("/api/delete", method="DELETE", json={"name": model_name})
    return {"deleted": True, "name": model_name}
