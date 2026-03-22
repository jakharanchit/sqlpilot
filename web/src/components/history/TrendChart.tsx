import { useState } from 'react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';
import { historyApi } from '../../api/history';
import type { TrendPoint } from '../../types';

interface ChartPoint {
  date:   string;
  before: number | null;
  after:  number | null;
  pct:    number | null;
  label:  string | null;
}

function CustomTooltip({ active, payload, label }: any) {
  if (!active || !payload?.length) return null;
  return (
    <div className="trend-tooltip">
      <div className="trend-tooltip__date">{label}</div>
      {payload.map((entry: any) => (
        <div key={entry.dataKey} className="trend-tooltip__row">
          <span style={{ color: entry.color }}>{entry.name}:</span>{' '}
          <strong>
            {entry.value != null
              ? entry.dataKey === 'pct'
                ? `+${entry.value.toFixed(1)}%`
                : `${entry.value}ms`
              : '—'}
          </strong>
        </div>
      ))}
    </div>
  );
}

export default function TrendChart() {
  const [tableInput, setTableInput]   = useState('');
  const [submitted,  setSubmitted]    = useState('');
  const [points,     setPoints]       = useState<TrendPoint[]>([]);
  const [loading,    setLoading]      = useState(false);
  const [error,      setError]        = useState<string | null>(null);

  async function load(table: string) {
    if (!table.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const data = await historyApi.trend({ table: table.trim() });
      setPoints(data);
    } catch (e: any) {
      setError(e.message ?? 'Failed to load trend data');
    } finally {
      setLoading(false);
    }
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSubmitted(tableInput);
    load(tableInput);
  }

  const chartData: ChartPoint[] = points.map(p => ({
    date:   p.timestamp.slice(0, 10),
    before: p.before_ms,
    after:  p.after_ms,
    pct:    p.improvement_pct,
    label:  p.label,
  }));

  const hasData = chartData.length > 0;

  return (
    <div className="trend-wrap">
      {/* Selector */}
      <form className="trend-selector" onSubmit={handleSubmit}>
        <input
          className="trend-input"
          placeholder="Enter table or view name (e.g. vw_dashboard)"
          value={tableInput}
          onChange={e => setTableInput(e.target.value)}
        />
        <button type="submit" className="trend-btn" disabled={loading}>
          {loading ? 'Loading…' : 'View Trend'}
        </button>
      </form>

      {error && (
        <div className="trend-error">{error}</div>
      )}

      {!submitted && !loading && (
        <div className="trend-empty">
          <div style={{ fontSize: 40, marginBottom: 8 }}>📈</div>
          <div>Enter a table or view name to view its trend</div>
          <div style={{ color: 'var(--text-muted)', fontSize: 13, marginTop: 4 }}>
            Shows how before/after performance changed over multiple optimization runs
          </div>
        </div>
      )}

      {submitted && !loading && !error && !hasData && (
        <div className="trend-empty">
          <div style={{ fontSize: 40, marginBottom: 8 }}>📭</div>
          <div>No trend data found for <strong>{submitted}</strong></div>
          <div style={{ color: 'var(--text-muted)', fontSize: 13, marginTop: 4 }}>
            Run an optimization on this table first
          </div>
        </div>
      )}

      {hasData && (
        <div className="trend-chart-wrap">
          <div className="trend-chart-title">
            Trend: <strong>{submitted}</strong>
            <span className="trend-chart-sub"> · {points.length} run(s)</span>
          </div>

          <ResponsiveContainer width="100%" height={320}>
            <LineChart data={chartData} margin={{ top: 10, right: 40, left: 0, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#E2E8F0" />
              <XAxis
                dataKey="date"
                tick={{ fontSize: 11, fill: 'var(--text-muted)' }}
              />
              <YAxis
                yAxisId="ms"
                tick={{ fontSize: 11, fill: 'var(--text-muted)' }}
                unit="ms"
                width={55}
              />
              <YAxis
                yAxisId="pct"
                orientation="right"
                tick={{ fontSize: 11, fill: 'var(--text-muted)' }}
                unit="%"
                width={45}
              />
              <Tooltip content={<CustomTooltip />} />
              <Legend
                iconType="circle"
                wrapperStyle={{ fontSize: 12 }}
              />
              <Line
                yAxisId="ms"
                type="monotone"
                dataKey="before"
                name="Before"
                stroke="#EF4444"
                strokeWidth={2}
                dot={{ r: 4, fill: '#EF4444' }}
                connectNulls
              />
              <Line
                yAxisId="ms"
                type="monotone"
                dataKey="after"
                name="After"
                stroke="#16A34A"
                strokeWidth={2}
                dot={{ r: 4, fill: '#16A34A' }}
                connectNulls
              />
              <Line
                yAxisId="pct"
                type="monotone"
                dataKey="pct"
                name="Improvement %"
                stroke="#2563EB"
                strokeWidth={1.5}
                strokeDasharray="5 5"
                dot={false}
                connectNulls
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  );
}

/* ── Styles ─────────────────────────────────────────────── */
const _styles = `
.trend-wrap {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.trend-selector {
  display: flex;
  gap: 8px;
}

.trend-input {
  flex: 1;
  height: 36px;
  padding: 0 12px;
  border: 1px solid var(--border);
  border-radius: 6px;
  font-size: 13px;
  outline: none;
  background: var(--bg-surface);
}
.trend-input:focus { border-color: var(--accent); }

.trend-btn {
  height: 36px;
  padding: 0 16px;
  background: var(--accent);
  color: #fff;
  border: none;
  border-radius: 6px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  white-space: nowrap;
  transition: background 0.15s;
}
.trend-btn:hover:not(:disabled) { background: var(--accent-hover); }
.trend-btn:disabled { opacity: 0.6; cursor: not-allowed; }

.trend-error {
  padding: 10px 14px;
  background: var(--danger-light);
  color: var(--danger);
  border-radius: 6px;
  font-size: 13px;
}

.trend-empty {
  text-align: center;
  padding: 60px 20px;
  color: var(--text-secondary);
  background: var(--bg-surface);
  border: 0.5px solid var(--border);
  border-radius: 10px;
}

.trend-chart-wrap {
  background: var(--bg-surface);
  border: 0.5px solid var(--border);
  border-radius: 10px;
  padding: 20px;
}

.trend-chart-title {
  font-size: 14px;
  font-weight: 600;
  margin-bottom: 16px;
  color: var(--text-primary);
}

.trend-chart-sub {
  font-weight: 400;
  color: var(--text-muted);
}

.trend-tooltip {
  background: var(--bg-surface);
  border: 1px solid var(--border);
  border-radius: 6px;
  padding: 10px 14px;
  font-size: 12px;
  box-shadow: 0 4px 12px rgba(0,0,0,0.08);
}
.trend-tooltip__date {
  font-weight: 600;
  margin-bottom: 4px;
  color: var(--text-secondary);
}
.trend-tooltip__row {
  margin-top: 2px;
  color: var(--text-primary);
}
`;

if (typeof document !== 'undefined') {
  const id = 'trend-chart-styles';
  if (!document.getElementById(id)) {
    const el = document.createElement('style');
    el.id = id;
    el.textContent = _styles;
    document.head.appendChild(el);
  }
}
