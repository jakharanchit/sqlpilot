// web/src/components/deployment/PendingMigrationsPanel.tsx
import { useEffect, useState } from 'react';
import { apiFetch } from '../../api/client';
import type { Migration } from '../../types';

export default function PendingMigrationsPanel() {
  const [migrations, setMigrations] = useState<Migration[]>([]);
  const [loading,    setLoading]    = useState(true);
  const [error,      setError]      = useState<string | null>(null);

  useEffect(() => {
    apiFetch<Migration[]>('/api/migrations?status=pending')
      .then(data => setMigrations(data))
      .catch(e  => setError(String(e)))
      .finally(() => setLoading(false));
  }, []);

  const formatMs = (before: number | null, after: number | null) => {
    if (!before && !after) return '—';
    if (before && after)   return `${before}ms → ${after}ms`;
    if (before)            return `${before}ms`;
    return `${after}ms`;
  };

  const formatPct = (pct: number | null) => {
    if (pct == null) return null;
    return pct > 0
      ? <span className="badge badge-success">+{pct}%</span>
      : <span className="badge badge-danger">{pct}%</span>;
  };

  return (
    <div className="pmp-card card">
      <div className="pmp-header">
        <div className="pmp-title">
          <span className="pmp-icon">📋</span>
          <h3>Pending Migrations</h3>
          {!loading && (
            <span className={`badge ${migrations.length > 0 ? 'badge-warning' : 'badge-neutral'}`}>
              {migrations.length} pending
            </span>
          )}
        </div>
        <p className="pmp-subtitle">Migrations queued for this deployment package</p>
      </div>

      <div className="pmp-body">
        {loading && (
          <div className="pmp-loading">
            <div className="spinner-sm" />
            <span>Loading migrations…</span>
          </div>
        )}

        {error && (
          <div className="pmp-error">
            <span>⚠</span> {error}
          </div>
        )}

        {!loading && !error && migrations.length === 0 && (
          <div className="pmp-empty">
            <div className="pmp-empty-icon">✓</div>
            <div className="pmp-empty-text">No pending migrations</div>
            <div className="pmp-empty-hint">
              Run an optimization first, then return here to generate a deployment package.
            </div>
          </div>
        )}

        {!loading && !error && migrations.length > 0 && (
          <table className="pmp-table">
            <thead>
              <tr>
                <th>#</th>
                <th>Description</th>
                <th>Tables</th>
                <th>Timing</th>
                <th>Improvement</th>
                <th>Date</th>
              </tr>
            </thead>
            <tbody>
              {migrations.map(m => (
                <tr key={m.number}>
                  <td className="pmp-num font-mono">
                    <span className="badge badge-neutral">{String(m.number).padStart(3, '0')}</span>
                  </td>
                  <td className="pmp-desc">{m.description}</td>
                  <td className="pmp-tables">
                    {(m.tables_affected || []).slice(0, 3).map(t => (
                      <span key={t} className="pmp-table-chip">{t}</span>
                    ))}
                    {(m.tables_affected || []).length > 3 && (
                      <span className="pmp-table-chip pmp-more">
                        +{m.tables_affected.length - 3}
                      </span>
                    )}
                  </td>
                  <td className="pmp-timing font-mono">
                    {formatMs(m.before_ms, m.after_ms)}
                  </td>
                  <td className="pmp-pct">
                    {formatPct(m.improvement_pct)}
                  </td>
                  <td className="pmp-date">{m.date.slice(0, 10)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}

// ── Styles ────────────────────────────────────────────────────
const _styles = `
.pmp-card {
  margin-bottom: 20px;
}

.pmp-header {
  padding: 18px 20px 12px;
  border-bottom: 1px solid var(--border);
}

.pmp-title {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 4px;
}

.pmp-title h3 {
  font-size: 15px;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0;
}

.pmp-icon {
  font-size: 16px;
}

.pmp-subtitle {
  font-size: 12px;
  color: var(--text-muted);
  margin: 0;
}

.pmp-body {
  padding: 0;
}

.pmp-loading {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 20px;
  color: var(--text-muted);
  font-size: 13px;
}

.pmp-error {
  padding: 16px 20px;
  color: var(--danger);
  font-size: 13px;
  background: var(--danger-light);
  border-radius: 0 0 10px 10px;
}

.pmp-empty {
  padding: 32px 20px;
  text-align: center;
}

.pmp-empty-icon {
  font-size: 28px;
  color: var(--success);
  margin-bottom: 8px;
}

.pmp-empty-text {
  font-size: 14px;
  font-weight: 500;
  color: var(--text-primary);
  margin-bottom: 6px;
}

.pmp-empty-hint {
  font-size: 12px;
  color: var(--text-muted);
  max-width: 380px;
  margin: 0 auto;
  line-height: 1.5;
}

.pmp-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}

.pmp-table th {
  text-align: left;
  padding: 10px 16px;
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: var(--text-muted);
  background: var(--bg-elevated);
  border-bottom: 1px solid var(--border);
}

.pmp-table td {
  padding: 10px 16px;
  vertical-align: middle;
  border-bottom: 1px solid var(--border);
  color: var(--text-primary);
}

.pmp-table tbody tr:last-child td {
  border-bottom: none;
}

.pmp-table tbody tr:hover {
  background: var(--bg-elevated);
}

.pmp-num {
  width: 64px;
}

.pmp-desc {
  max-width: 260px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.pmp-tables {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  max-width: 200px;
}

.pmp-table-chip {
  display: inline-block;
  padding: 2px 7px;
  background: var(--bg-elevated);
  border: 1px solid var(--border);
  border-radius: 4px;
  font-size: 11px;
  color: var(--text-secondary);
  white-space: nowrap;
}

.pmp-more {
  color: var(--text-muted);
}

.pmp-timing {
  font-size: 12px;
  color: var(--text-secondary);
  white-space: nowrap;
}

.pmp-date {
  font-size: 12px;
  color: var(--text-muted);
  white-space: nowrap;
}

.spinner-sm {
  width: 14px;
  height: 14px;
  border: 2px solid var(--border);
  border-top-color: var(--accent);
  border-radius: 50%;
  animation: spin 0.7s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
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
