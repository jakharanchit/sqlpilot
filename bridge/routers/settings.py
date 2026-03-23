"""
bridge/routers/settings.py
Phase 7 — Read and write config.py settings from the web UI.

Strategy:
  READ:  import config directly (fast, always accurate).
  WRITE: read config.py as text, apply targeted regex replacements,
         write the modified text back. Never rewrites the whole file.
         Only touches the specific variables it knows about.
"""
import importlib
import re
import sys
from pathlib import Path

import pyodbc
import requests
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/api/settings", tags=["settings"])


# ── Helpers: locate config.py ──────────────────────────────────────────────────

def _config_path() -> Path:
    """Return the absolute path to config.py (always in the project root)."""
    import config as _cfg
    return Path(_cfg.__file__).resolve()


def _reload_config():
    """Reload config module so changes to config.py are reflected immediately."""
    if "config" in sys.modules:
        importlib.reload(sys.modules["config"])


# ── Read ───────────────────────────────────────────────────────────────────────

@router.get("")
def get_settings():
    """Return all editable config.py values grouped by section."""
    _reload_config()
    import config as cfg

    db     = getattr(cfg, "DB_CONFIG", {})
    models = getattr(cfg, "MODELS", {})

    return {
        "db": {
            "server":             db.get("server", ""),
            "database":           db.get("database", ""),
            "driver":             db.get("driver", "ODBC Driver 17 for SQL Server"),
            "trusted_connection": db.get("trusted_connection", "yes"),
            "username":           db.get("username", ""),
            "password":           "",   # never expose password in GET response
        },
        "ollama": {
            "base_url": getattr(cfg, "OLLAMA_BASE_URL", "http://localhost:11434"),
            "models": {
                "optimizer": models.get("optimizer", ""),
                "reasoner":  models.get("reasoner",  ""),
            },
        },
        "sandbox": {
            "bak_path":  getattr(cfg, "SANDBOX_BAK_PATH", ""),
            "data_dir":  getattr(cfg, "SANDBOX_DATA_DIR", ""),
            "timeout_s": getattr(cfg, "SANDBOX_TIMEOUT",  300),
        },
        "agent": {
            "benchmark_runs":  getattr(cfg, "BENCHMARK_RUNS",  10),
            "auto_commit_git": getattr(cfg, "AUTO_COMMIT_GIT", True),
            "save_reports":    getattr(cfg, "SAVE_REPORTS",    True),
        },
        "active_client": getattr(cfg, "ACTIVE_CLIENT", ""),
        "config_path":   str(_config_path()),
    }


# ── Write helpers ──────────────────────────────────────────────────────────────

def _read_config_text() -> str:
    return _config_path().read_text(encoding="utf-8")


def _write_config_text(text: str):
    _config_path().write_text(text, encoding="utf-8")
    _reload_config()


def _replace_simple(text: str, var_name: str, new_value) -> str:
    """
    Replace a top-level scalar assignment:
        VAR_NAME    = <old_value>
    →   VAR_NAME    = <new_value>

    Works for: strings (adds quotes), booleans, integers.
    Preserves surrounding whitespace and trailing comments.
    """
    if isinstance(new_value, bool):
        py_val = "True" if new_value else "False"
    elif isinstance(new_value, int):
        py_val = str(new_value)
    elif isinstance(new_value, str):
        # Use raw string if value contains backslashes (e.g. Windows paths)
        if "\\" in new_value:
            py_val = f'r"{new_value}"'
        else:
            py_val = f'"{new_value}"'
    else:
        py_val = repr(new_value)

    pattern = rf'^({re.escape(var_name)}\s*=\s*).*$'
    replacement = rf'\g<1>{py_val}'
    new_text, count = re.subn(pattern, replacement, text, flags=re.MULTILINE)
    if count == 0:
        raise ValueError(f"Could not find '{var_name}' in config.py")
    return new_text


def _replace_dict_value(text: str, dict_name: str, key: str, new_value) -> str:
    """
    Replace a value inside a top-level dict literal:
        DICT_NAME = {
            "key":  <old>,     ← this line is replaced
        }

    Only replaces the first occurrence of `"key"` inside the dict block.
    Preserves indentation.
    """
    if isinstance(new_value, str):
        if "\\" in new_value:
            py_val = f'r"{new_value}"'
        else:
            py_val = f'"{new_value}"'
    elif isinstance(new_value, bool):
        py_val = "True" if new_value else "False"
    else:
        py_val = repr(new_value)

    # Match the dict key line (with optional comment after)
    pattern = rf'(\s*"{re.escape(key)}"\s*:\s*)([^,\n#]+)(.*)'
    replacement = rf'\g<1>{py_val}\g<3>'
    new_text, count = re.subn(pattern, replacement, text, count=1)
    if count == 0:
        # Key might be commented out — try to find and uncomment it
        # (e.g. # "username": "sa",)
        uncomment_pattern = rf'(\s*)#\s*("{re.escape(key)}"\s*:\s*).*'
        new_text, count2 = re.subn(
            uncomment_pattern,
            rf'\g<1>\g<2>{py_val},',
            text, count=1,
        )
        if count2 == 0:
            raise ValueError(f"Could not find key '{key}' in {dict_name} dict in config.py")
    return new_text


# ── POST /database ─────────────────────────────────────────────────────────────

class DbRequest(BaseModel):
    server:             str
    database:           str
    driver:             str = "ODBC Driver 17 for SQL Server"
    trusted_connection: str = "yes"
    username:           str = ""
    password:           str = ""   # empty = don't change existing password


@router.post("/database")
def save_database(body: DbRequest):
    """Update DB_CONFIG fields in config.py."""
    try:
        text = _read_config_text()
        text = _replace_dict_value(text, "DB_CONFIG", "server",             body.server)
        text = _replace_dict_value(text, "DB_CONFIG", "database",           body.database)
        text = _replace_dict_value(text, "DB_CONFIG", "driver",             body.driver)
        text = _replace_dict_value(text, "DB_CONFIG", "trusted_connection", body.trusted_connection)

        if body.trusted_connection.lower() == "no":
            if body.username:
                text = _replace_dict_value(text, "DB_CONFIG", "username", body.username)
            if body.password:
                text = _replace_dict_value(text, "DB_CONFIG", "password", body.password)

        _write_config_text(text)
        return {"ok": True}
    except Exception as e:
        raise HTTPException(500, f"Failed to save database settings: {e}")


# ── POST /ollama ───────────────────────────────────────────────────────────────

class OllamaRequest(BaseModel):
    base_url:  str
    optimizer: str
    reasoner:  str


@router.post("/ollama")
def save_ollama(body: OllamaRequest):
    """Update OLLAMA_BASE_URL and MODELS in config.py."""
    try:
        text = _read_config_text()
        text = _replace_simple(text, "OLLAMA_BASE_URL", body.base_url)
        text = _replace_dict_value(text, "MODELS", "optimizer", body.optimizer)
        text = _replace_dict_value(text, "MODELS", "reasoner",  body.reasoner)
        _write_config_text(text)
        return {"ok": True}
    except Exception as e:
        raise HTTPException(500, f"Failed to save Ollama settings: {e}")


# ── POST /agent ────────────────────────────────────────────────────────────────

class AgentRequest(BaseModel):
    benchmark_runs:  int  = 10
    auto_commit_git: bool = True
    save_reports:    bool = True


@router.post("/agent")
def save_agent(body: AgentRequest):
    """Update BENCHMARK_RUNS, AUTO_COMMIT_GIT, SAVE_REPORTS in config.py."""
    if body.benchmark_runs < 1 or body.benchmark_runs > 100:
        raise HTTPException(400, "benchmark_runs must be between 1 and 100")
    try:
        text = _read_config_text()
        text = _replace_simple(text, "BENCHMARK_RUNS",  body.benchmark_runs)
        text = _replace_simple(text, "AUTO_COMMIT_GIT", body.auto_commit_git)
        text = _replace_simple(text, "SAVE_REPORTS",    body.save_reports)
        _write_config_text(text)
        return {"ok": True}
    except Exception as e:
        raise HTTPException(500, f"Failed to save agent settings: {e}")


# ── POST /sandbox ──────────────────────────────────────────────────────────────

class SandboxRequest(BaseModel):
    bak_path:  str = ""
    data_dir:  str = ""
    timeout_s: int = 300


@router.post("/sandbox")
def save_sandbox(body: SandboxRequest):
    """Update SANDBOX_BAK_PATH, SANDBOX_DATA_DIR, SANDBOX_TIMEOUT in config.py."""
    if body.timeout_s < 30 or body.timeout_s > 3600:
        raise HTTPException(400, "timeout_s must be between 30 and 3600")
    try:
        text = _read_config_text()
        text = _replace_simple(text, "SANDBOX_BAK_PATH", body.bak_path)
        text = _replace_simple(text, "SANDBOX_DATA_DIR", body.data_dir)
        text = _replace_simple(text, "SANDBOX_TIMEOUT",  body.timeout_s)
        _write_config_text(text)
        return {"ok": True}
    except Exception as e:
        raise HTTPException(500, f"Failed to save sandbox settings: {e}")


# ── GET /test-connection ───────────────────────────────────────────────────────

@router.get("/test-connection")
def test_connection():
    """Test current DB_CONFIG live. Does not save anything."""
    _reload_config()
    import config as cfg

    db = cfg.DB_CONFIG
    try:
        if db.get("trusted_connection", "no").lower() == "yes":
            conn_str = (
                f"DRIVER={{{db['driver']}}};"
                f"SERVER={db['server']};"
                f"DATABASE={db['database']};"
                f"Trusted_Connection=yes;"
            )
        else:
            conn_str = (
                f"DRIVER={{{db['driver']}}};"
                f"SERVER={db['server']};"
                f"DATABASE={db['database']};"
                f"UID={db.get('username', '')};"
                f"PWD={db.get('password', '')};"
            )
        conn = pyodbc.connect(conn_str, timeout=5)
        cursor = conn.cursor()
        cursor.execute("SELECT @@VERSION, DB_NAME()")
        row = cursor.fetchone()
        version_line = row[0].split("\n")[0].strip()[:80] if row else "unknown"
        db_name = row[1] if row else db.get("database", "?")
        conn.close()
        return {"ok": True, "message": f"Connected to {db_name} — {version_line}"}
    except Exception as e:
        return {"ok": False, "message": str(e)}


# ── GET /test-ollama ───────────────────────────────────────────────────────────

@router.get("/test-ollama")
def test_ollama():
    """Test OLLAMA_BASE_URL live. Does not save anything."""
    _reload_config()
    import config as cfg

    url = getattr(cfg, "OLLAMA_BASE_URL", "http://localhost:11434")
    try:
        r = requests.get(f"{url}/api/tags", timeout=5)
        r.raise_for_status()
        models_list = [m["name"] for m in r.json().get("models", [])]
        return {
            "ok": True,
            "message": f"Ollama reachable at {url} — {len(models_list)} model(s) available",
        }
    except requests.exceptions.ConnectionError:
        return {"ok": False, "message": f"Cannot reach Ollama at {url} — is 'ollama serve' running?"}
    except Exception as e:
        return {"ok": False, "message": str(e)}
