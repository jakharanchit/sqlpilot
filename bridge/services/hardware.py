"""
bridge/services/hardware.py

Hardware stats provider.
- CPU and RAM via psutil
- VRAM: try pynvml first, fall back to nvidia-smi subprocess
- Background polling thread keeps a cached snapshot fresh
"""

import subprocess
import threading
import time
from dataclasses import dataclass, field
from typing import Optional

import psutil

# ── Data classes ──────────────────────────────────────────────────────────────

@dataclass
class GpuStats:
    name: str
    vram_usage_mb: int
    vram_total_mb: int
    vram_pct: float
    utilization_pct: int
    source: str  # "pynvml" | "nvidia-smi"


@dataclass
class OllamaStatus:
    status: str           # "online" | "offline"
    active_models: list   # model names currently loaded
    url: str


@dataclass
class DbStatus:
    status: str           # "online" | "offline" | "error"
    database: str
    server: str
    error: Optional[str] = None


@dataclass
class HardwareStats:
    cpu_usage: float
    ram_usage_mb: int
    ram_total_mb: int
    ram_pct: float
    gpu: Optional[GpuStats]
    ollama: OllamaStatus
    db: DbStatus
    gpu_source: str       # "pynvml" | "nvidia-smi" | "unavailable"


# ── VRAM detection ────────────────────────────────────────────────────────────

def _try_pynvml() -> Optional[GpuStats]:
    """Try to read VRAM via pynvml (NVML Python bindings)."""
    try:
        import pynvml
        pynvml.nvmlInit()
        handle = pynvml.nvmlDeviceGetHandleByIndex(0)
        mem    = pynvml.nvmlDeviceGetMemoryInfo(handle)
        name   = pynvml.nvmlDeviceGetName(handle)
        util   = pynvml.nvmlDeviceGetUtilizationRates(handle)

        # pynvml may return bytes or str depending on version
        if isinstance(name, bytes):
            name = name.decode("utf-8")

        used_mb  = mem.used  // (1024 * 1024)
        total_mb = mem.total // (1024 * 1024)
        pct      = round(used_mb / total_mb * 100, 1) if total_mb > 0 else 0.0

        return GpuStats(
            name=name,
            vram_usage_mb=used_mb,
            vram_total_mb=total_mb,
            vram_pct=pct,
            utilization_pct=util.gpu,
            source="pynvml",
        )
    except Exception:
        return None


def _try_nvidia_smi() -> Optional[GpuStats]:
    """Fall back to parsing nvidia-smi output."""
    try:
        query = (
            "name,memory.used,memory.total,utilization.gpu"
        )
        result = subprocess.run(
            [
                "nvidia-smi",
                f"--query-gpu={query}",
                "--format=csv,noheader,nounits",
            ],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode != 0:
            return None

        line  = result.stdout.strip().splitlines()[0]
        parts = [p.strip() for p in line.split(",")]
        if len(parts) < 4:
            return None

        name         = parts[0]
        used_mb      = int(float(parts[1]))
        total_mb     = int(float(parts[2]))
        util_pct     = int(float(parts[3])) if parts[3] not in ("N/A", "[N/A]") else 0
        pct          = round(used_mb / total_mb * 100, 1) if total_mb > 0 else 0.0

        return GpuStats(
            name=name,
            vram_usage_mb=used_mb,
            vram_total_mb=total_mb,
            vram_pct=pct,
            utilization_pct=util_pct,
            source="nvidia-smi",
        )
    except Exception:
        return None


def _get_gpu_stats() -> tuple[Optional[GpuStats], str]:
    """Try pynvml, fall back to nvidia-smi, return (stats, source)."""
    gpu = _try_pynvml()
    if gpu:
        return gpu, "pynvml"
    gpu = _try_nvidia_smi()
    if gpu:
        return gpu, "nvidia-smi"
    return None, "unavailable"


# ── Ollama status ─────────────────────────────────────────────────────────────

def _get_ollama_status() -> OllamaStatus:
    """Check Ollama availability and loaded models."""
    try:
        import urllib.request, json as _json
        from config import OLLAMA_BASE_URL
        url = OLLAMA_BASE_URL
    except Exception:
        url = "http://localhost:11434"

    try:
        import urllib.request, json as _json
        with urllib.request.urlopen(f"{url}/api/tags", timeout=3) as resp:
            data   = _json.loads(resp.read())
            models = [m["name"] for m in data.get("models", [])]
        return OllamaStatus(status="online", active_models=models, url=url)
    except Exception:
        return OllamaStatus(status="offline", active_models=[], url=url)


# ── DB status ─────────────────────────────────────────────────────────────────

def _get_db_status() -> DbStatus:
    """Quick DB ping using the project's config."""
    try:
        from config import DB_CONFIG
        import pyodbc

        cfg = DB_CONFIG
        if cfg.get("trusted_connection", "no").lower() == "yes":
            conn_str = (
                f"DRIVER={{{cfg['driver']}}};"
                f"SERVER={cfg['server']};"
                f"DATABASE={cfg['database']};"
                f"Trusted_Connection=yes;"
            )
        else:
            conn_str = (
                f"DRIVER={{{cfg['driver']}}};"
                f"SERVER={cfg['server']};"
                f"DATABASE={cfg['database']};"
                f"UID={cfg.get('username', '')};"
                f"PWD={cfg.get('password', '')};"
            )
        conn = pyodbc.connect(conn_str, timeout=3)
        conn.close()
        return DbStatus(
            status="online",
            database=cfg.get("database", ""),
            server=cfg.get("server", ""),
        )
    except Exception as e:
        try:
            from config import DB_CONFIG as _cfg
            return DbStatus(
                status="offline",
                database=_cfg.get("database", ""),
                server=_cfg.get("server", ""),
                error=str(e)[:120],
            )
        except Exception:
            return DbStatus(status="offline", database="", server="", error=str(e)[:120])


# ── Polling cache ─────────────────────────────────────────────────────────────

class HardwareMonitor:
    """
    Singleton background thread that refreshes hardware stats on a schedule.
    Frontend polls /api/system/stats; this class serves cached results
    so the endpoint is always fast.
    """

    _instance: Optional["HardwareMonitor"] = None

    def __init__(self):
        self._lock    = threading.Lock()
        self._stats:  Optional[HardwareStats] = None
        self._interval = 2.0       # seconds between refreshes
        self._running  = False
        self._thread:  Optional[threading.Thread] = None

    @classmethod
    def get(cls) -> "HardwareMonitor":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread  = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def _loop(self):
        while self._running:
            self._refresh()
            time.sleep(self._interval)

    def _refresh(self):
        cpu_pct   = psutil.cpu_percent(interval=0.2)
        vm        = psutil.virtual_memory()
        ram_used  = vm.used  // (1024 * 1024)
        ram_total = vm.total // (1024 * 1024)
        ram_pct   = round(vm.percent, 1)

        gpu, source = _get_gpu_stats()
        ollama      = _get_ollama_status()
        db          = _get_db_status()

        stats = HardwareStats(
            cpu_usage=round(cpu_pct, 1),
            ram_usage_mb=ram_used,
            ram_total_mb=ram_total,
            ram_pct=ram_pct,
            gpu=gpu,
            ollama=ollama,
            db=db,
            gpu_source=source,
        )
        with self._lock:
            self._stats = stats

    def get_stats(self) -> Optional[HardwareStats]:
        with self._lock:
            return self._stats

    def set_interval(self, seconds: float):
        self._interval = max(0.5, seconds)

    def stop(self):
        self._running = False


# ── Convenience ───────────────────────────────────────────────────────────────

_monitor = HardwareMonitor.get()


def start_monitor():
    """Call once at app startup."""
    _monitor.start()


def get_current_stats() -> Optional[HardwareStats]:
    """Returns the most recently cached hardware snapshot."""
    stats = _monitor.get_stats()
    if stats is None:
        # First call before background thread has run — do a synchronous read
        _monitor._refresh()
        stats = _monitor.get_stats()
    return stats


def set_poll_interval(seconds: float):
    """Frontend adjusts poll rate (2s idle, 0.5s during active inference)."""
    _monitor.set_interval(seconds)
