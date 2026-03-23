// web/src/components/models/PullModelPanel.tsx
// Pull a new Ollama model with live SSE download progress.

import { useState, useRef, useEffect } from 'react';
import { modelsApi } from '../../api/models';
import type { SSEEvent } from '../../types';

interface Props {
  onPulled: () => void;
}

type Phase = 'idle' | 'pulling' | 'complete' | 'failed';

const SUGGESTED = [
  'qwen2.5-coder:14b',
  'deepseek-r1:14b',
  'llama3.2:3b',
  'phi4:14b',
  'codellama:13b',
];

const _styles = `
.pmp-card {
  background: var(--bg-surface);
  border: 0.5px solid var(--border);
  border-radius: 10px;
  padding: 20px 24px;
  margin-bottom: 20px;
}
.pmp-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.06em;
  margin-bottom: 16px;
}
.pmp-row {
  display: flex;
  gap: 8px;
  align-items: center;
  margin-bottom: 12px;
}
.pmp-input {
  flex: 1;
  padding: 8px 12px;
  border: 0.5px solid var(--border-strong);
  border-radius: 6px;
  font-family: 'JetBrains Mono', monospace;
  font-size: 13px;
  color: var(--text-primary);
  background: var(--bg-base);
  outline: none;
  transition: border-color 0.15s;
}
.pmp-input:focus {
  border-color: var(--accent);
}
.pmp-input:disabled {
  opacity: 0.6;
}
.pmp-pull-btn {
  padding: 8px 18px;
  background: var(--accent);
  color: #fff;
  border: none;
  border-radius: 6px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.15s;
  white-space: nowrap;
}
.pmp-pull-btn:hover:not(:disabled) {
  background: var(--accent-hover);
}
.pmp-pull-btn:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}
.pmp-suggestions {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-bottom: 16px;
}
.pmp-chip {
  font-family: 'JetBrains Mono', monospace;
  font-size: 11px;
  padding: 3px 10px;
  border-radius: 99px;
  border: 0.5px solid var(--border-strong);
  background: var(--bg-elevated);
  color: var(--text-secondary);
  cursor: pointer;
  transition: background 0.12s, border-color 0.12s;
}
.pmp-chip:hover {
  background: var(--accent-light);
  border-color: var(--accent);
  color: var(--accent);
}
.pmp-progress-wrap {
  margin-top: 12px;
}
.pmp-progress-label {
  font-size: 12px;
  color: var(--text-secondary);
  margin-bottom: 6px;
  display: flex;
  justify-content: space-between;
}
.pmp-bar-track {
  height: 8px;
  background: var(--bg-elevated);
  border-radius: 99px;
  overflow: hidden;
  margin-bottom: 10px;
}
.pmp-bar-fill {
  height: 100%;
  background: var(--accent);
  border-radius: 99px;
  transition: width 0.3s ease;
}
.pmp-log {
  background: var(--bg-elevated);
  border-radius: 6px;
  padding: 10px 12px;
  max-height: 120px;
  overflow-y: auto;
  font-family: 'JetBrains Mono', monospace;
  font-size: 11px;
  color: var(--text-secondary);
  line-height: 1.7;
}
.pmp-success {
  margin-top: 12px;
  padding: 10px 14px;
  background: var(--success-light);
  border-radius: 6px;
  font-size: 13px;
  color: var(--success);
  font-weight: 600;
}
.pmp-error {
  margin-top: 12px;
  padding: 10px 14px;
  background: var(--danger-light);
  border-radius: 6px;
  font-size: 13px;
  color: var(--danger);
}
.pmp-retry-btn {
  margin-top: 8px;
  padding: 6px 14px;
  border: 0.5px solid var(--danger);
  background: transparent;
  color: var(--danger);
  border-radius: 6px;
  font-size: 12px;
  cursor: pointer;
}
`;

if (typeof document !== 'undefined') {
  const id = 'pmp-styles';
  if (!document.getElementById(id)) {
    const el = document.createElement('style');
    el.id = id;
    el.textContent = _styles;
    document.head.appendChild(el);
  }
}

export default function PullModelPanel({ onPulled }: Props) {
  const [modelName, setModelName] = useState('');
  const [phase,     setPhase]     = useState<Phase>('idle');
  const [pct,       setPct]       = useState(0);
  const [logs,      setLogs]      = useState<string[]>([]);
  const [error,     setError]     = useState('');
  const logEndRef = useRef<HTMLDivElement>(null);
  const esRef     = useRef<EventSource | null>(null);

  useEffect(() => {
    logEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [logs]);

  // Cleanup EventSource on unmount
  useEffect(() => () => { esRef.current?.close(); }, []);

  async function handlePull() {
    const name = modelName.trim();
    if (!name) return;
    setPhase('pulling');
    setPct(0);
    setLogs([]);
    setError('');

    try {
      const job = await modelsApi.pull(name);

      // Stream progress via SSE
      const es = new EventSource(`/api/jobs/${job.job_id}/stream`);
      esRef.current = es;

      es.onmessage = (ev) => {
        try {
          const event: SSEEvent = JSON.parse(ev.data);

          if (event.type === 'step') {
            const s = event.payload.step ?? 0;
            const t = event.payload.total ?? 100;
            setPct(Math.min(100, Math.round((s / t) * 100)));
          }
          if (event.type === 'log' && event.payload.line) {
            setLogs(prev => [...prev.slice(-60), event.payload.line!]);
          }
          if (event.type === 'complete') {
            setPct(100);
            setPhase('complete');
            es.close();
            onPulled();
          }
          if (event.type === 'error') {
            setError(event.payload.message ?? 'Pull failed');
            setPhase('failed');
            es.close();
          }
        } catch { /* ignore parse errors */ }
      };

      es.onerror = () => {
        setError('Connection to server lost during pull.');
        setPhase('failed');
        es.close();
      };

    } catch (err: any) {
      setError(err?.message ?? 'Failed to start pull job');
      setPhase('failed');
    }
  }

  function handleRetry() {
    setPhase('idle');
    setError('');
    setPct(0);
    setLogs([]);
  }

  const isPulling = phase === 'pulling';

  return (
    <div className="pmp-card">
      <div className="pmp-title">Pull New Model</div>

      <div className="pmp-suggestions">
        {SUGGESTED.map(s => (
          <button
            key={s}
            className="pmp-chip"
            onClick={() => setModelName(s)}
            disabled={isPulling}
          >
            {s}
          </button>
        ))}
      </div>

      <div className="pmp-row">
        <input
          className="pmp-input"
          type="text"
          placeholder="e.g. llama3.2:3b"
          value={modelName}
          onChange={e => setModelName(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && !isPulling && handlePull()}
          disabled={isPulling}
        />
        <button
          className="pmp-pull-btn"
          onClick={handlePull}
          disabled={isPulling || !modelName.trim()}
        >
          {isPulling ? 'Pulling…' : '▶ Pull'}
        </button>
      </div>

      {isPulling && (
        <div className="pmp-progress-wrap">
          <div className="pmp-progress-label">
            <span>Downloading {modelName}</span>
            <span>{pct}%</span>
          </div>
          <div className="pmp-bar-track">
            <div className="pmp-bar-fill" style={{ width: `${pct}%` }} />
          </div>
          {logs.length > 0 && (
            <div className="pmp-log">
              {logs.map((line, i) => <div key={i}>{line}</div>)}
              <div ref={logEndRef} />
            </div>
          )}
        </div>
      )}

      {phase === 'complete' && (
        <div className="pmp-success">✓ Model pulled successfully — {modelName}</div>
      )}

      {phase === 'failed' && (
        <div>
          <div className="pmp-error">✗ {error}</div>
          <button className="pmp-retry-btn" onClick={handleRetry}>Retry</button>
        </div>
      )}
    </div>
  );
}
