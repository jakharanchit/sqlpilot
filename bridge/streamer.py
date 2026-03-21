# ============================================================
# bridge/streamer.py
# SSE Log Streamer — tails logs/agent.log for the Web UI.
# ============================================================

import time
import os
from pathlib import Path
from datetime import date

def tail_logs(log_path: str = None, start_from_end: bool = True):
    \"\"\"
    Generator that tails the log file and yields new lines.
    \"\"\"
    if log_path is None:
        from tools.app_logger import _get_log_dir, LOG_NAME
        today = date.today().strftime("%Y_%m_%d")
        log_path = _get_log_dir() / f"{LOG_NAME}_{today}.log"
    
    path = Path(log_path)
    
    # Wait for file to exist
    while not path.exists():
        time.sleep(0.5)
        yield \"data: Waiting for log file...\\n\\n\"

    with open(path, 'r', encoding='utf-8', errors='ignore') as f:
        if start_from_end:
            f.seek(0, os.SEEK_END)
        
        while True:
            line = f.readline()
            if not line:
                time.sleep(0.1)  # small sleep to avoid CPU spinning
                continue
            
            # Format for SSE
            yield f\"data: {line.strip()}\\n\\n\"
