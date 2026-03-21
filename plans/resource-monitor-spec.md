# Spec: Hardware-Aware Resource Monitor

## 1. Backend Metrics Provider (FastAPI expansion)
The FastAPI bridge must provide a high-frequency telemetry endpoint.

### Endpoint: `GET /api/system/stats`
*   **Library:** `psutil` (CPU/RAM), `pynvml` (NVIDIA VRAM) or parsing `nvidia-smi`.
*   **Payload Schema:**
```json
{
  "cpu_usage": 45.2,
  "ram_usage": 12400,
  "ram_total": 32000,
  "gpu": {
    "name": "NVIDIA RTX 3080",
    "vram_usage": 8400,
    "vram_total": 10240,
    "utilization": 92
  },
  "ollama": {
    "status": "online",
    "active_models": ["qwen2.5-coder:14b"]
  }
}
```

## 2. UI Component: `ModelManager`
A sidebar component that lists local Ollama inventory.
*   **Data Source:** `GET http://localhost:11434/api/tags`.
*   **Status Indicators:**
    *   **Green Dot:** Model is currently loaded in VRAM.
    *   **Size Label:** Show GB size (e.g., `9.1 GB`).
    *   **Model Switching:** Allow the user to "Pre-load" a model to VRAM.

## 3. UI Component: `HardwareGauges`
Dashboard widgets using circular or linear progress bars.
*   **VRAM Critical Alert:** If VRAM usage is `> 90%`, show a pulsating red border.
*   **Tooltip Advice:** "VRAM nearly full. Optimization may slow down or switch to CPU."
*   **Refresh Rate:** 2 seconds during idle, 500ms during active inference.

## 4. Inference Feedback (TPS Counter)
During the SSE log stream or a direct chat interface, provide real-time performance metrics.
*   **Metric:** Tokens Per Second (TPS).
*   **Calculation:** Total Tokens / Total Inference Time (from Ollama metadata).
*   **Visual:** A small "Performance Chip" at the bottom of the AI output.
*   **Historical Average:** Store the average TPS in the `jobs` table to identify if performance is degrading.

## 5. Implementation Strategy
1.  **Poll Thread:** A background thread in `bridge/main.py` that updates a global `HardwareStats` object.
2.  **Webhooks:** Frontend uses a `useInterval` hook to poll `/api/system/stats`.
3.  **Optimization Pause:** If `cpu_usage` is `> 95%` for more than 10 seconds, the UI suggests pausing non-critical tasks.
