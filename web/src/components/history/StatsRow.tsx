import type { HistoryStats } from '../../types';

interface Props {
  stats: HistoryStats | null;
}

function StatCard({
  value,
  label,
  sub,
  color,
}: {
  value: string;
  label: string;
  sub?: string;
  color?: string;
}) {
  return (
    <div className="stat-card">
      <div className="stat-value" style={{ color: color ?? 'var(--text-primary)' }}>
        {value}
      </div>
      <div className="stat-label">{label}</div>
      {sub && <div className="stat-sub">{sub}</div>}
    </div>
  );
}

export default function StatsRow({ stats }: Props) {
  if (!stats) {
    return (
      <div className="stats-row">
        {[0, 1, 2, 3].map(i => (
          <div key={i} className="stat-card stat-card--loading" />
        ))}
      </div>
    );
  }

  const successRate =
    stats.total_runs > 0
      ? Math.round((stats.successful_runs / stats.total_runs) * 100)
      : 0;

  return (
    <div className="stats-row">
      <StatCard
        value={String(stats.total_runs)}
        label="Total Runs"
        sub={`${stats.queries_tracked} unique queries`}
      />
      <StatCard
        value={`${successRate}%`}
        label="Success Rate"
        sub={`${stats.successful_runs} of ${stats.total_runs}`}
        color={successRate >= 80 ? 'var(--success)' : 'var(--warning)'}
      />
      <StatCard
        value={
          stats.avg_improvement != null
            ? `+${stats.avg_improvement.toFixed(1)}%`
            : '—'
        }
        label="Avg Improvement"
        sub={`${stats.tables_touched} tables touched`}
        color={
          stats.avg_improvement != null && stats.avg_improvement > 0
            ? 'var(--success)'
            : undefined
        }
      />
      <StatCard
        value={
          stats.best_improvement != null
            ? `+${stats.best_improvement.toFixed(1)}%`
            : '—'
        }
        label="Best Result"
        sub={`${stats.total_migrations} migrations`}
        color={
          stats.best_improvement != null ? 'var(--success)' : undefined
        }
      />
    </div>
  );
}

/* ── Styles ─────────────────────────────────────────────── */
const _styles = `
.stats-row {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
  margin-bottom: 20px;
}

.stat-card {
  background: var(--bg-surface);
  border: 0.5px solid var(--border);
  border-radius: 10px;
  padding: 16px 20px;
}

.stat-card--loading {
  height: 80px;
  background: var(--bg-elevated);
  animation: pulse 1.4s ease-in-out infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50%       { opacity: 0.5; }
}

.stat-value {
  font-size: 28px;
  font-weight: 700;
  line-height: 1;
  margin-bottom: 4px;
}

.stat-label {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-secondary);
}

.stat-sub {
  font-size: 11px;
  color: var(--text-muted);
  margin-top: 2px;
}
`;

// Inject styles once
if (typeof document !== 'undefined') {
  const id = 'stats-row-styles';
  if (!document.getElementById(id)) {
    const el = document.createElement('style');
    el.id = id;
    el.textContent = _styles;
    document.head.appendChild(el);
  }
}
