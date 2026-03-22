// web/src/components/deployment/SandboxRunner.tsx
import { useEffect, useState, useRef } from 'react';
import { sandboxApi } from '../../api/sandbox';
import type { Job, ShadowDB, SandboxStep, SandboxResult } from '../../types';

interface Props {
  onPassed: () => void;
  onFailed?: () => void;
}

type Phase = 'idle' | 'running' | 'passed' | 'failed';

const STEP_LABELS = [
  'Creating shadow database from .bak',
  'Applying migrations to shadow',
  'Benchmarking queries in shadow',
  'Regression check',
  'Destroying shadow database',
];

const initialSteps = (): SandboxStep[] =>
  STEP_LABELS.map((label, i) => ({
    number: i + 1,
    label,
    status: 'pending',
  }));

export default function SandboxRunner({ onPassed, onFailed }: Props) {
  const [phase,    setPhase]    = useState<Phase>('idle');
  const [job,      setJob]      = useState<Job | null>(null);
  const [steps,    setSteps]    = useState<SandboxStep[]>(initialSteps());
  const [logs,     setLogs]     = useState<string[]>([]);
  const [result,   setResult]   = useState<SandboxResult | null>(null);
  const [shadows,  setShadows]  = useState<ShadowDB[]>([]);
  const [config,   setConfig]   = useState<{
    configured: boolean; bak_path: string; bak_exists: boolean; shadow_name: string;
  } | null>(null);
  const [destroying, setDestroying] = useState<string | null>(null);

  const esRef  = useRef<EventSource | null>(null);
  const logsEl = useRef<HTMLDivElement>(null);

  // On mount: fetch config and orphan shadows
  useEffect(() => {
    sandboxApi.config().then(setConfig).catch(() => null);
    sandboxApi.listShadows().then(setShadows).catch(() => null);
    return () => esRef.current?.close();
  }, []);

  // Auto-scroll log
  useEffect(() => {
    if (logsEl.current) {
      logsEl.current.scrollTop = logsEl.current.scrollHeight;
    }
  }, [logs]);

  async function handleRun() {
    setPhase('running');
    setSteps(initialSteps());
    setLogs([]);
    setResult(null);

    let newJob: Job;
    try {
      newJob = await sandboxApi.runTest();
      setJob(newJob);
    } catch (e) {
      setPhase('failed');
      setLogs([`Error starting sandbox test: ${e}`]);
      return;
    }

    // Stream SSE
    const es = new EventSource(`/api/jobs/${newJob.job_id}/stream`);
    esRef.current = es;

    es.onmessage = (evt) => {
      try {
        const msg = JSON.parse(evt.data);
        if (msg.type === 'step') {
          const { step } = msg.payload as { step: number; total: number; label?: string };
          setSteps(prev => prev.map(s => {
            if (s.number < step)  return { ...s, status: 'passed' };
            if (s.number === step) return { ...s, status: 'running' };
            return s;
          }));
        } else if (msg.type === 'log') {
          setLogs(prev => [...prev, msg.payload.line ?? '']);
        } else if (msg.type === 'complete') {
          const r = msg.payload.result as SandboxResult;
          setResult(r);
          setSteps(prev => prev.map(s => ({
            ...s,
            status: r.passed ? 'passed' : (s.status === 'running' ? 'failed' : s.status),
          })));
          if (r.passed) {
            setPhase('passed');
            onPassed();
          } else {
            setPhase('failed');
            onFailed?.();
          }
          es.close();
          // Refresh shadows list
          sandboxApi.listShadows().then(setShadows).catch(() => null);
        } else if (msg.type === 'error') {
          setLogs(prev => [...prev, `Error: ${msg.payload.message}`]);
          setPhase('failed');
          onFailed?.();
          setSteps(prev => prev.map(s =>
            s.status === 'running' ? { ...s, status: 'failed' } : s,
          ));
          es.close();
        }
      } catch {}
    };

    es.onerror = () => {
      if (phase === 'running') {
        setLogs(prev => [...prev, 'SSE connection lost — check if the job is still running.']);
      }
    };
  }

  function handleReset() {
    esRef.current?.close();
    setPhase('idle');
    setSteps(initialSteps());
    setLogs([]);
    setResult(null);
    setJob(null);
  }

  async function handleDestroyShadow(name: string) {
    setDestroying(name);
    try {
      await sandboxApi.destroyShadow(name);
      setShadows(prev => prev.filter(s => s.name !== name));
    } finally {
      setDestroying(null);
    }
  }

  const stepIcon = (s: SandboxStep) => {
    if (s.status === 'passed')  return <span className="step-icon step-passed">✓</span>;
    if (s.status === 'failed')  return <span className="step-icon step-failed">✗</span>;
    if (s.status === 'running') return <span className="step-icon step-running"><span className="spin-dot" /></span>;
    return <span className="step-icon step-pending">○</span>;
  };

  return (
    <div className="sr-card card">
      {/* Header */}
      <div className="sr-header">
        <div className="sr-title">
          <span>🧪</span>
          <h3>Shadow DB Sandbox Test</h3>
          {phase === 'passed' && <span className="badge badge-success">PASSED</span>}
          {phase === 'failed' && <span className="badge badge-danger">FAILED</span>}
        </div>
        <p className="sr-subtitle">
          Restores a .bak to a shadow database, applies migrations, runs regression checks — without touching the real database.
        </p>
      </div>

      {/* Sandbox not configured warning */}
      {config && !config.configured && (
        <div className="sr-warning">
          <strong>⚠ SANDBOX_BAK_PATH not set in config.py</strong><br />
          Shadow DB testing requires a .bak backup file. You can still generate a deployment
          package without sandbox testing.
        </div>
      )}

      {/* Orphan shadows */}
      {shadows.filter(s => s.is_orphaned || phase === 'idle').length > 0 && phase === 'idle' && (
        <div className="sr-shadows">
          <div className="sr-shadows-title">Existing shadow databases:</div>
          {shadows.map(s => (
            <div key={s.name} className="sr-shadow-row">
              <span className="sr-shadow-name font-mono">{s.name}</span>
              <span className={`badge ${s.state === 'ONLINE' ? 'badge-info' : 'badge-neutral'}`}>
                {s.state}
              </span>
              {s.is_orphaned && <span className="badge badge-warning">orphaned</span>}
              <button
                className="sr-destroy-btn"
                disabled={destroying === s.name}
                onClick={() => handleDestroyShadow(s.name)}
              >
                {destroying === s.name ? 'Destroying…' : 'Destroy'}
              </button>
            </div>
          ))}
        </div>
      )}

      {/* Steps */}
      <div className="sr-steps">
        {steps.map(s => (
          <div key={s.number} className={`sr-step sr-step-${s.status}`}>
            {stepIcon(s)}
            <span className="sr-step-label">
              Step {s.number}/5 — {s.label}
            </span>
          </div>
        ))}
      </div>

      {/* Live log */}
      {logs.length > 0 && (
        <div className="sr-logs" ref={logsEl}>
          {logs.map((line, i) => (
            <div key={i} className="sr-log-line font-mono">{line}</div>
          ))}
        </div>
      )}

      {/* Result details */}
      {phase === 'failed' && result && (
        <div className="sr-result-fail">
          {(result.errors?.length ?? 0) > 0 && (
            <div className="sr-errors">
              <strong>Errors:</strong>
              {result.errors?.map((e, i) => <div key={i} className="sr-error-line">• {e}</div>)}
            </div>
          )}
          {(result.regression_result?.regressions?.length ?? 0) > 0 && (
            <div className="sr-regressions">
              <strong>Regressions detected:</strong>
              <table className="sr-reg-table">
                <thead>
                  <tr><th>Query</th><th>Baseline</th><th>Shadow</th><th>Slowdown</th></tr>
                </thead>
                <tbody>
                  {result.regression_result?.regressions?.map((r, i) => (
                    <tr key={i}>
                      <td>{r.label}</td>
                      <td className="font-mono">{r.baseline_ms ?? '—'}ms</td>
                      <td className="font-mono">{r.shadow_ms ?? '—'}ms</td>
                      <td><span className="badge badge-danger">{r.slowdown_pct ?? '?'}%</span></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {phase === 'passed' && (
        <div className="sr-result-pass">
          ✓ All changes applied cleanly · No regressions detected · Safe to generate deployment package
        </div>
      )}

      {/* Action buttons */}
      <div className="sr-actions">
        {phase === 'idle' && (
          <button
            className="sr-run-btn btn-primary"
            disabled={config ? !config.configured : false}
            onClick={handleRun}
          >
            ▶ Run Sandbox Test
          </button>
        )}
        {phase === 'running' && (
          <button className="sr-run-btn btn-primary" disabled>
            <span className="spinner-sm-inline" /> Running…
          </button>
        )}
        {(phase === 'passed' || phase === 'failed') && (
          <button className="sr-run-btn btn-secondary" onClick={handleReset}>
            ↺ Run Again
          </button>
        )}
        {job && (
          <span className="sr-job-id font-mono">job {job.job_id.slice(0, 8)}</span>
        )}
      </div>
    </div>
  );
}

// ── Styles ────────────────────────────────────────────────────
const _styles = `
.sr-card { margin-bottom: 20px; }

.sr-header {
  padding: 18px 20px 14px;
  border-bottom: 1px solid var(--border);
}

.sr-title {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 4px;
}

.sr-title h3 {
  font-size: 15px;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0;
  flex: 1;
}

.sr-subtitle {
  font-size: 12px;
  color: var(--text-muted);
  margin: 0;
}

.sr-warning {
  margin: 0 20px 0;
  padding: 12px 14px;
  background: var(--warning-light);
  border: 1px solid #fbbf24;
  border-radius: 8px;
  font-size: 12px;
  color: var(--warning);
  line-height: 1.6;
  margin-top: 14px;
}

.sr-shadows {
  padding: 12px 20px;
  border-bottom: 1px solid var(--border);
  background: var(--bg-elevated);
}

.sr-shadows-title {
  font-size: 11px;
  font-weight: 600;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  margin-bottom: 8px;
}

.sr-shadow-row {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 4px 0;
}

.sr-shadow-name {
  font-size: 12px;
  flex: 1;
}

.sr-destroy-btn {
  padding: 3px 10px;
  font-size: 11px;
  background: transparent;
  border: 1px solid var(--danger);
  color: var(--danger);
  border-radius: 5px;
  cursor: pointer;
}
.sr-destroy-btn:hover { background: var(--danger-light); }
.sr-destroy-btn:disabled { opacity: 0.5; cursor: default; }

.sr-steps {
  padding: 16px 20px;
  display: flex;
  flex-direction: column;
  gap: 8px;
  border-bottom: 1px solid var(--border);
}

.sr-step {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 13px;
}

.sr-step-pending .sr-step-label  { color: var(--text-muted); }
.sr-step-running .sr-step-label  { color: var(--text-primary); font-weight: 500; }
.sr-step-passed  .sr-step-label  { color: var(--success); }
.sr-step-failed  .sr-step-label  { color: var(--danger); }

.step-icon {
  width: 20px;
  height: 20px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  flex-shrink: 0;
}

.step-passed { color: var(--success); }
.step-failed { color: var(--danger); }
.step-pending { color: var(--text-muted); }
.step-running { display: flex; align-items: center; justify-content: center; }

.spin-dot {
  width: 14px;
  height: 14px;
  border: 2px solid var(--border);
  border-top-color: var(--accent);
  border-radius: 50%;
  animation: spin 0.7s linear infinite;
  display: block;
}

.sr-logs {
  margin: 0 20px 14px;
  max-height: 180px;
  overflow-y: auto;
  background: #1e1e1e;
  border-radius: 6px;
  padding: 10px 12px;
}

.sr-log-line {
  font-size: 11px;
  color: #d4d4d4;
  line-height: 1.6;
  white-space: pre-wrap;
  word-break: break-word;
}

.sr-result-pass {
  margin: 0 20px 14px;
  padding: 12px 14px;
  background: var(--success-light);
  border: 1px solid var(--success);
  border-radius: 8px;
  font-size: 13px;
  color: var(--success);
}

.sr-result-fail {
  margin: 0 20px 14px;
}

.sr-errors {
  background: var(--danger-light);
  border: 1px solid var(--danger);
  border-radius: 8px;
  padding: 12px 14px;
  font-size: 12px;
  color: var(--danger);
  margin-bottom: 10px;
}

.sr-error-line {
  margin-top: 4px;
  line-height: 1.5;
}

.sr-regressions {
  font-size: 13px;
  color: var(--text-primary);
}

.sr-reg-table {
  width: 100%;
  border-collapse: collapse;
  margin-top: 8px;
  font-size: 12px;
}

.sr-reg-table th {
  text-align: left;
  padding: 6px 10px;
  background: var(--bg-elevated);
  border: 1px solid var(--border);
  font-size: 11px;
  color: var(--text-muted);
}

.sr-reg-table td {
  padding: 6px 10px;
  border: 1px solid var(--border);
  color: var(--text-primary);
}

.sr-actions {
  padding: 14px 20px;
  display: flex;
  align-items: center;
  gap: 12px;
  border-top: 1px solid var(--border);
}

.sr-run-btn {
  padding: 8px 20px;
  font-size: 13px;
  font-weight: 500;
  border-radius: 7px;
  border: none;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 8px;
}

.btn-primary {
  background: var(--accent);
  color: white;
}
.btn-primary:hover:not(:disabled) { background: var(--accent-hover); }
.btn-primary:disabled { opacity: 0.5; cursor: default; }

.btn-secondary {
  background: var(--bg-elevated);
  color: var(--text-primary);
  border: 1px solid var(--border);
}
.btn-secondary:hover { background: var(--border); }

.sr-job-id {
  font-size: 11px;
  color: var(--text-muted);
  margin-left: auto;
}

.spinner-sm-inline {
  width: 12px;
  height: 12px;
  border: 2px solid rgba(255,255,255,0.4);
  border-top-color: white;
  border-radius: 50%;
  animation: spin 0.7s linear infinite;
  display: inline-block;
}
`;

if (typeof document !== 'undefined') {
  const id = 'sr-styles';
  if (!document.getElementById(id)) {
    const el = document.createElement('style');
    el.id = id;
    el.textContent = _styles;
    document.head.appendChild(el);
  }
}
