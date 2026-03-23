// web/src/components/models/RunningModelsPanel.tsx
// Shows models currently loaded in Ollama memory, polled every 30s.

import { useState, useEffect } from 'react';
import { modelsApi } from '../../api/models';
import { useInterval } from '../../hooks/useInterval';
import type { RunningModel } from '../../types';

const _styles = `
.rmp-card {
  background: var(--bg-surface);
  border: 0.5px solid var(--border);
  border-radius: 10px;
  padding: 16px 24px;
  margin-bottom: 20px;
}
.rmp-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.06em;
  margin-bottom: 12px;
}
.rmp-empty {
  font-size: 13px;
  color: var(--text-muted);
  font-style: italic;
}
.rmp-item {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 8px 0;
  border-bottom: 0.5px solid var(--border);
}
.rmp-item:last-child {
  border-bottom: none;
}
.rmp-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--success);
  flex-shrink: 0;
}
.rmp-name {
  font-family: 'JetBrains Mono', monospace;
  font-size: 13px;
  color: var(--text-primary);
  flex: 1;
}
.rmp-meta {
  font-size: 12px;
  color: var(--text-muted);
  text-align: right;
  line-height: 1.5;
}
`;

if (typeof document !== 'undefined') {
  const id = 'rmp-styles';
  if (!document.getElementById(id)) {
    const el = document.createElement('style');
    el.id = id;
    el.textContent = _styles;
    document.head.appendChild(el);
  }
}

function formatExpiry(iso: string): string {
  if (!iso) return '';
  try {
    const diff = Math.floor((new Date(iso).getTime() - Date.now()) / 1000);
    if (diff <= 0) return 'expiring';
    if (diff < 60) return `expires in ${diff}s`;
    return `expires in ${Math.floor(diff / 60)}m`;
  } catch {
    return '';
  }
}

export default function RunningModelsPanel({ running: initialRunning }: { running: RunningModel[] }) {
  const [running, setRunning] = useState<RunningModel[]>(initialRunning);

  useEffect(() => {
    setRunning(initialRunning);
  }, [initialRunning]);

  useInterval(async () => {
    try {
      const data = await modelsApi.running();
      setRunning(data);
    } catch { /* ignore */ }
  }, 30_000);

  return (
    <div className="rmp-card">
      <div className="rmp-title">Currently Loaded (in Ollama memory)</div>

      {running.length === 0 ? (
        <div className="rmp-empty">
          No models currently loaded — models load automatically when a job runs.
        </div>
      ) : (
        running.map(m => (
          <div key={m.name} className="rmp-item">
            <div className="rmp-dot" />
            <div className="rmp-name">{m.name}</div>
            <div className="rmp-meta">
              <div>{m.size_vram_gb} VRAM</div>
              <div>{formatExpiry(m.expires_at)}</div>
            </div>
          </div>
        ))
      )}
    </div>
  );
}
