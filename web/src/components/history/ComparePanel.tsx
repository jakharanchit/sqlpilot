import { useState, useEffect } from 'react';
import { historyApi } from '../../api/history';
import type { RunRecord, RunComparison } from '../../types';

interface Props {
  /** Pre-selected run A (from clicking a row in RunsTable) */
  preselectedA?: RunRecord | null;
}

function RunOption({ run }: { run: RunRecord }) {
  return (
    <option value={run.id}>
      #{run.id} — {(run.label || run.query_preview || 'run').slice(0, 40)} · {run.timestamp.slice(0, 10)}
    </option>
  );
}

interface MetricRowProps {
  label:  string;
  valA:   string;
  valB:   string;
  delta?: { value: number; higherIsBetter: boolean } | null;
}

function MetricRow({ label, valA, valB, delta }: MetricRowProps) {
  let arrow = null;
  if (delta) {
    const better = delta.higherIsBetter ? delta.value > 0 : delta.value < 0;
    const color  = better ? 'var(--success)' : delta.value === 0 ? 'var(--text-muted)' : 'var(--danger)';
    const sign   = delta.value > 0 ? '+' : '';
    arrow = (
      <span style={{ color, fontWeight: 600, fontSize: 12 }}>
        {sign}{delta.value.toFixed(delta.value % 1 === 0 ? 0 : 1)}
        {label.includes('ms') ? 'ms' : '%'}
      </span>
    );
  }

  return (
    <tr className="cp-metric-row">
      <td className="cp-metric-label">{label}</td>
      <td className="cp-metric-val cp-metric-val--a">{valA}</td>
      <td className="cp-metric-val cp-metric-val--b">{valB}</td>
      <td className="cp-metric-delta">{arrow}</td>
    </tr>
  );
}

export default function ComparePanel({ preselectedA }: Props) {
  const [runs,       setRuns]       = useState<RunRecord[]>([]);
  const [runAId,     setRunAId]     = useState<number | ''>('');
  const [runBId,     setRunBId]     = useState<number | ''>('');
  const [comparison, setComparison] = useState<RunComparison | null>(null);
  const [loading,    setLoading]    = useState(false);
  const [error,      setError]      = useState<string | null>(null);

  // Load all runs for the selectors
  useEffect(() => {
    historyApi.list({ limit: 200 }).then(setRuns).catch(() => {});
  }, []);

  // If a run was pre-selected from RunsTable, set it as A
  useEffect(() => {
    if (preselectedA) setRunAId(preselectedA.id);
  }, [preselectedA]);

  // Auto-compare when both selected
  useEffect(() => {
    if (runAId === '' || runBId === '') {
      setComparison(null);
      return;
    }
    if (runAId === runBId) {
      setError('Select two different runs to compare');
      return;
    }
    setError(null);
    setLoading(true);
    historyApi.compare(Number(runAId), Number(runBId))
      .then(data => { setComparison(data); })
      .catch(e  => { setError(e.message ?? 'Comparison failed'); })
      .finally(() => setLoading(false));
  }, [runAId, runBId]);

  function fmtMs(v: number | null) {
    return v != null ? `${v}ms` : '—';
  }
  function fmtPct(v: number | null) {
    if (v == null) return '—';
    return `${v > 0 ? '+' : ''}${v.toFixed(1)}%`;
  }
  function fmtX(v: number | null) {
    return v != null ? `${v}x` : '—';
  }

  // Verdict text
  let verdict: React.ReactNode = null;
  if (comparison) {
    const d = comparison.diff.improvement_pct;
    if (d) {
      if (d.delta > 0) {
        verdict = (
          <div className="cp-verdict cp-verdict--better">
            ↑ Run #{comparison.run_b.id} is {Math.abs(d.delta).toFixed(1)}% better than Run #{comparison.run_a.id}
          </div>
        );
      } else if (d.delta < 0) {
        verdict = (
          <div className="cp-verdict cp-verdict--worse">
            ↓ Run #{comparison.run_b.id} is {Math.abs(d.delta).toFixed(1)}% worse than Run #{comparison.run_a.id}
          </div>
        );
      } else {
        verdict = (
          <div className="cp-verdict cp-verdict--same">
            Both runs achieved the same improvement
          </div>
        );
      }
    }
  }

  return (
    <div className="compare-panel">
      {/* Selectors */}
      <div className="cp-selectors">
        <div className="cp-selector-group">
          <label className="cp-selector-label">Run A</label>
          <select
            className="cp-select"
            value={runAId}
            onChange={e => setRunAId(e.target.value === '' ? '' : Number(e.target.value))}
          >
            <option value="">Select a run…</option>
            {runs.map(r => <RunOption key={r.id} run={r} />)}
          </select>
        </div>

        <div className="cp-vs">vs</div>

        <div className="cp-selector-group">
          <label className="cp-selector-label">Run B</label>
          <select
            className="cp-select"
            value={runBId}
            onChange={e => setRunBId(e.target.value === '' ? '' : Number(e.target.value))}
          >
            <option value="">Select a run…</option>
            {runs.map(r => <RunOption key={r.id} run={r} />)}
          </select>
        </div>
      </div>

      {error && <div className="cp-error">{error}</div>}

      {loading && <div className="cp-loading">Loading comparison…</div>}

      {!comparison && !loading && !error && (
        <div className="cp-empty">
          <div style={{ fontSize: 36, marginBottom: 8 }}>⚖️</div>
          <div>Select two runs to compare them side by side</div>
        </div>
      )}

      {comparison && !loading && (
        <>
          <div className="cp-table-wrap">
            <table className="cp-table">
              <thead>
                <tr>
                  <th>Metric</th>
                  <th>Run #{comparison.run_a.id}</th>
                  <th>Run #{comparison.run_b.id}</th>
                  <th>Δ</th>
                </tr>
              </thead>
              <tbody>
                <MetricRow
                  label="Before (avg)"
                  valA={fmtMs(comparison.run_a.before_ms)}
                  valB={fmtMs(comparison.run_b.before_ms)}
                  delta={comparison.diff.before_ms
                    ? { value: comparison.diff.before_ms.delta, higherIsBetter: false }
                    : null}
                />
                <MetricRow
                  label="After (avg)"
                  valA={fmtMs(comparison.run_a.after_ms)}
                  valB={fmtMs(comparison.run_b.after_ms)}
                  delta={comparison.diff.after_ms
                    ? { value: comparison.diff.after_ms.delta, higherIsBetter: false }
                    : null}
                />
                <MetricRow
                  label="Improvement %"
                  valA={fmtPct(comparison.run_a.improvement_pct)}
                  valB={fmtPct(comparison.run_b.improvement_pct)}
                  delta={comparison.diff.improvement_pct
                    ? { value: comparison.diff.improvement_pct.delta, higherIsBetter: true }
                    : null}
                />
                <MetricRow
                  label="Speedup"
                  valA={fmtX(comparison.run_a.speedup)}
                  valB={fmtX(comparison.run_b.speedup)}
                  delta={comparison.diff.speedup
                    ? { value: comparison.diff.speedup.delta, higherIsBetter: true }
                    : null}
                />
                <tr className="cp-metric-row">
                  <td className="cp-metric-label">Tables</td>
                  <td className="cp-metric-val cp-metric-val--a">
                    {comparison.run_a.tables_involved || '—'}
                  </td>
                  <td className="cp-metric-val cp-metric-val--b">
                    {comparison.run_b.tables_involved || '—'}
                  </td>
                  <td />
                </tr>
                <tr className="cp-metric-row">
                  <td className="cp-metric-label">Migration</td>
                  <td className="cp-metric-val cp-metric-val--a">
                    {comparison.run_a.migration_number ?? '—'}
                  </td>
                  <td className="cp-metric-val cp-metric-val--b">
                    {comparison.run_b.migration_number ?? '—'}
                  </td>
                  <td />
                </tr>
                <tr className="cp-metric-row">
                  <td className="cp-metric-label">Date</td>
                  <td className="cp-metric-val cp-metric-val--a" style={{ color: 'var(--text-muted)', fontSize: 12 }}>
                    {comparison.run_a.timestamp.slice(0, 16)}
                  </td>
                  <td className="cp-metric-val cp-metric-val--b" style={{ color: 'var(--text-muted)', fontSize: 12 }}>
                    {comparison.run_b.timestamp.slice(0, 16)}
                  </td>
                  <td />
                </tr>
              </tbody>
            </table>
          </div>

          {verdict}
        </>
      )}
    </div>
  );
}

/* ── Styles ─────────────────────────────────────────────── */
const _styles = `
.compare-panel {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.cp-selectors {
  display: flex;
  align-items: flex-end;
  gap: 12px;
}
.cp-selector-group {
  display: flex;
  flex-direction: column;
  gap: 4px;
  flex: 1;
}
.cp-selector-label {
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--text-muted);
}
.cp-select {
  height: 36px;
  padding: 0 10px;
  border: 1px solid var(--border);
  border-radius: 6px;
  font-size: 13px;
  background: var(--bg-surface);
  outline: none;
  width: 100%;
}
.cp-select:focus { border-color: var(--accent); }
.cp-vs {
  font-size: 18px;
  font-weight: 700;
  color: var(--text-muted);
  padding-bottom: 6px;
  flex-shrink: 0;
}

.cp-error {
  padding: 10px 14px;
  background: var(--danger-light);
  color: var(--danger);
  border-radius: 6px;
  font-size: 13px;
}
.cp-loading {
  text-align: center;
  padding: 32px;
  color: var(--text-muted);
  font-size: 13px;
}
.cp-empty {
  text-align: center;
  padding: 60px 20px;
  color: var(--text-secondary);
  background: var(--bg-surface);
  border: 0.5px solid var(--border);
  border-radius: 10px;
}

.cp-table-wrap {
  background: var(--bg-surface);
  border: 0.5px solid var(--border);
  border-radius: 10px;
  overflow: hidden;
}
.cp-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}
.cp-table th {
  padding: 10px 16px;
  text-align: left;
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--text-muted);
  background: var(--bg-elevated);
  border-bottom: 1px solid var(--border);
}
.cp-metric-row {
  border-bottom: 1px solid var(--border);
}
.cp-metric-row:last-child { border-bottom: none; }
.cp-metric-row td { padding: 10px 16px; vertical-align: middle; }
.cp-metric-label {
  font-size: 12px;
  color: var(--text-muted);
  font-weight: 500;
  width: 130px;
}
.cp-metric-val {
  font-weight: 600;
  font-family: var(--font-mono, monospace);
  font-size: 13px;
}
.cp-metric-val--a { color: #EF4444; }
.cp-metric-val--b { color: var(--success); }
.cp-metric-delta {
  width: 80px;
  text-align: right;
}

.cp-verdict {
  padding: 12px 16px;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 600;
  text-align: center;
}
.cp-verdict--better { background: var(--success-light); color: var(--success); }
.cp-verdict--worse  { background: var(--danger-light);  color: var(--danger); }
.cp-verdict--same   { background: var(--bg-elevated);   color: var(--text-muted); }
`;

if (typeof document !== 'undefined') {
  const id = 'compare-panel-styles';
  if (!document.getElementById(id)) {
    const el = document.createElement('style');
    el.id = id;
    el.textContent = _styles;
    document.head.appendChild(el);
  }
}
