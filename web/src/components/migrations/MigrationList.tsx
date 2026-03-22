import React, { useState, useEffect, useCallback } from 'react';
import { migrationsApi } from '../../api/migrations';
import type { Migration } from '../../types';
import MigrationDetail from './MigrationDetail';

type StatusFilter = 'all' | 'pending' | 'applied' | 'rolled_back';

const STATUS_TABS: { key: StatusFilter; label: string }[] = [
  { key: 'all',          label: 'All' },
  { key: 'pending',      label: 'Pending' },
  { key: 'applied',      label: 'Applied' },
  { key: 'rolled_back',  label: 'Rolled Back' },
];

function statusBadge(status: Migration['status']) {
  switch (status) {
    case 'pending':      return <span className="badge badge-warning">pending</span>;
    case 'applied':      return <span className="badge badge-success">applied</span>;
    case 'rolled_back':  return <span className="badge badge-danger">rolled back</span>;
    default:             return <span className="badge badge-neutral">{status}</span>;
  }
}

export default function MigrationList() {
  const [migrations, setMigrations] = useState<Migration[]>([]);
  const [loading,    setLoading]    = useState(true);
  const [filter,     setFilter]     = useState<StatusFilter>('all');
  const [expanded,   setExpanded]   = useState<number | null>(null);
  const [actionMap,  setActionMap]  = useState<Record<number, 'loading' | 'done' | 'error'>>({});

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await migrationsApi.list(filter === 'all' ? undefined : filter);
      setMigrations(data);
    } finally {
      setLoading(false);
    }
  }, [filter]);

  useEffect(() => { load(); }, [load]);

  async function handleMarkApplied(m: Migration) {
    setActionMap(prev => ({ ...prev, [m.number]: 'loading' }));
    try {
      const res = await migrationsApi.markApplied(m.number);
      // Update row inline
      setMigrations(prev =>
        prev.map(mig => mig.number === m.number ? res.migration : mig),
      );
      setActionMap(prev => ({ ...prev, [m.number]: 'done' }));
    } catch {
      setActionMap(prev => ({ ...prev, [m.number]: 'error' }));
    }
  }

  async function handleRollback(m: Migration) {
    setActionMap(prev => ({ ...prev, [m.number]: 'loading' }));
    try {
      const res = await migrationsApi.rollback(m.number);
      setMigrations(prev =>
        prev.map(mig => mig.number === m.number ? res.migration : mig),
      );
      setActionMap(prev => ({ ...prev, [m.number]: 'done' }));
    } catch {
      setActionMap(prev => ({ ...prev, [m.number]: 'error' }));
    }
  }

  function toggleExpand(number: number) {
    setExpanded(prev => (prev === number ? null : number));
  }

  return (
    <div className="mig-list">
      {/* Status filter tabs */}
      <div className="mig-tabs">
        {STATUS_TABS.map(tab => (
          <button
            key={tab.key}
            className={`mig-tab${filter === tab.key ? ' mig-tab--active' : ''}`}
            onClick={() => setFilter(tab.key)}
          >
            {tab.label}
          </button>
        ))}
      </div>

      <div className="mig-table-wrap">
        <table className="mig-table">
          <thead>
            <tr>
              <th style={{ width: 36 }} />
              <th>#</th>
              <th>Description</th>
              <th>Tables</th>
              <th>Date</th>
              <th>Before → After</th>
              <th>Impr.</th>
              <th>Status</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {migrations.map(m => {
              const isExpanded = expanded === m.number;
              const actionState = actionMap[m.number];

              return (
                <React.Fragment key={m.number}>
                  <tr
                    className={`mig-row${isExpanded ? ' mig-row--expanded' : ''}`}
                  >
                    {/* Expand toggle */}
                    <td>
                      <button
                        className="mig-expand-btn"
                        onClick={() => toggleExpand(m.number)}
                        title={isExpanded ? 'Collapse' : 'Expand'}
                      >
                        {isExpanded ? '▾' : '▸'}
                      </button>
                    </td>

                    <td className="mig-number font-mono">
                      {String(m.number).padStart(3, '0')}
                    </td>

                    <td className="mig-description">
                      {m.description.slice(0, 55)}
                    </td>

                    <td className="mig-tables">
                      {m.tables_affected.slice(0, 3).join(', ') || '—'}
                    </td>

                    <td className="mig-date">{m.date.slice(0, 10)}</td>

                    <td className="mig-timing font-mono">
                      {m.before_ms != null && m.after_ms != null ? (
                        <>
                          <span style={{ color: '#EF4444' }}>{m.before_ms}ms</span>
                          {' → '}
                          <span style={{ color: 'var(--success)' }}>{m.after_ms}ms</span>
                        </>
                      ) : (
                        <span style={{ color: 'var(--text-muted)' }}>—</span>
                      )}
                    </td>

                    <td>
                      {m.improvement_pct != null ? (
                        <span
                          style={{
                            fontWeight: 600,
                            color:
                              m.improvement_pct > 0
                                ? 'var(--success)'
                                : 'var(--danger)',
                            fontSize: 13,
                          }}
                        >
                          {m.improvement_pct > 0 ? '+' : ''}
                          {m.improvement_pct.toFixed(1)}%
                        </span>
                      ) : (
                        <span style={{ color: 'var(--text-muted)' }}>—</span>
                      )}
                    </td>

                    <td>{statusBadge(m.status)}</td>

                    <td>
                      <div className="mig-actions">
                        {m.status === 'pending' && (
                          <button
                            className="mig-action-btn mig-action-btn--apply"
                            disabled={actionState === 'loading'}
                            onClick={() => handleMarkApplied(m)}
                          >
                            {actionState === 'loading' ? '…' : 'Mark Applied'}
                          </button>
                        )}
                        {m.status === 'applied' && (
                          <button
                            className="mig-action-btn mig-action-btn--rollback"
                            disabled={actionState === 'loading'}
                            onClick={() => handleRollback(m)}
                          >
                            {actionState === 'loading' ? '…' : 'Roll Back'}
                          </button>
                        )}
                        {actionState === 'error' && (
                          <span style={{ color: 'var(--danger)', fontSize: 12 }}>Error</span>
                        )}
                      </div>
                    </td>
                  </tr>

                  {isExpanded && (
                    <tr key={`detail-${m.number}`} className="mig-detail-row">
                      <td colSpan={9} style={{ padding: 0 }}>
                        <MigrationDetail migration={m} />
                      </td>
                    </tr>
                  )}
                </React.Fragment>
              );
            })}
          </tbody>
        </table>

        {loading && (
          <div className="mig-loading">Loading migrations…</div>
        )}

        {!loading && migrations.length === 0 && (
          <div className="mig-empty">
            <div style={{ fontSize: 32, marginBottom: 8 }}>📋</div>
            <div>
              {filter === 'all'
                ? 'No migrations yet — run an optimization to generate one'
                : `No ${filter.replace('_', ' ')} migrations`}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

/* ── Styles ─────────────────────────────────────────────── */
const _styles = `
.mig-list { display: flex; flex-direction: column; gap: 12px; }

.mig-tabs {
  display: flex;
  gap: 4px;
  background: var(--bg-elevated);
  padding: 4px;
  border-radius: 8px;
  align-self: flex-start;
}

.mig-tab {
  padding: 6px 14px;
  border: none;
  background: none;
  border-radius: 6px;
  font-size: 13px;
  font-weight: 500;
  color: var(--text-secondary);
  cursor: pointer;
  transition: all 0.15s;
  white-space: nowrap;
}
.mig-tab:hover { background: var(--bg-surface); }
.mig-tab--active {
  background: var(--bg-surface);
  color: var(--accent);
  font-weight: 600;
  box-shadow: 0 1px 3px rgba(0,0,0,0.08);
}

.mig-table-wrap {
  background: var(--bg-surface);
  border: 0.5px solid var(--border);
  border-radius: 10px;
  overflow: hidden;
}

.mig-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}
.mig-table th {
  padding: 10px 12px;
  text-align: left;
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--text-muted);
  background: var(--bg-elevated);
  border-bottom: 1px solid var(--border);
  white-space: nowrap;
}
.mig-row {
  border-bottom: 1px solid var(--border);
  transition: background 0.1s;
}
.mig-row:last-child { border-bottom: none; }
.mig-row:hover { background: var(--bg-elevated); }
.mig-row--expanded { background: var(--bg-elevated); }
.mig-row td { padding: 9px 12px; vertical-align: middle; }

.mig-detail-row td {
  padding: 0 !important;
  border-bottom: 1px solid var(--border);
}

.mig-expand-btn {
  width: 22px;
  height: 22px;
  background: none;
  border: none;
  color: var(--text-muted);
  cursor: pointer;
  font-size: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 4px;
  transition: background 0.1s;
}
.mig-expand-btn:hover { background: var(--border); }

.mig-number     { color: var(--text-muted); font-size: 12px; }
.mig-description { max-width: 260px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.mig-tables     { color: var(--text-secondary); font-size: 12px; max-width: 140px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.mig-date       { color: var(--text-muted); font-size: 12px; white-space: nowrap; }
.mig-timing     { font-size: 12px; white-space: nowrap; }

.mig-actions { display: flex; gap: 6px; }

.mig-action-btn {
  padding: 5px 10px;
  border-radius: 5px;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  border: none;
  transition: opacity 0.15s;
  white-space: nowrap;
}
.mig-action-btn:disabled { opacity: 0.5; cursor: not-allowed; }
.mig-action-btn--apply {
  background: var(--success-light);
  color: var(--success);
}
.mig-action-btn--apply:hover:not(:disabled) { opacity: 0.8; }
.mig-action-btn--rollback {
  background: var(--danger-light);
  color: var(--danger);
}
.mig-action-btn--rollback:hover:not(:disabled) { opacity: 0.8; }

.mig-loading, .mig-empty {
  text-align: center;
  padding: 40px 20px;
  color: var(--text-secondary);
}
`;

if (typeof document !== 'undefined') {
  const id = 'mig-list-styles';
  if (!document.getElementById(id)) {
    const el = document.createElement('style');
    el.id = id;
    el.textContent = _styles;
    document.head.appendChild(el);
  }
}
