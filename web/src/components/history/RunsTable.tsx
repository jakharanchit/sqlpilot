import { useState, useEffect, useCallback } from 'react';

import { historyApi } from '../../api/history';
import type { RunRecord } from '../../types';

const PAGE_SIZE = 50;

interface Filters {
  query:       string;
  table:       string;
  type:        string;
  top:         boolean;
  regressions: boolean;
}

interface Props {
  /** Called when user clicks a row — passes the run for comparison */
  onSelectRun?: (run: RunRecord) => void;
}

export default function RunsTable({ onSelectRun }: Props) {
  

  const [runs,    setRuns]    = useState<RunRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [offset,  setOffset]  = useState(0);
  const [hasMore, setHasMore] = useState(true);

  const [filters, setFilters] = useState<Filters>({
    query:       '',
    table:       '',
    type:        '',
    top:         false,
    regressions: false,
  });

  // Debounced search value
  const [searchInput, setSearchInput] = useState('');
  useEffect(() => {
    const t = setTimeout(() =>
      setFilters(f => ({ ...f, query: searchInput })), 350);
    return () => clearTimeout(t);
  }, [searchInput]);

  const fetchRuns = useCallback(
    async (reset: boolean) => {
      setLoading(true);
      try {
        const nextOffset = reset ? 0 : offset;
        const data = await historyApi.list({
          query:       filters.query       || undefined,
          table:       filters.table       || undefined,
          type:        filters.type        || undefined,
          top:         filters.top         || undefined,
          regressions: filters.regressions || undefined,
          limit:       PAGE_SIZE,
          offset:      nextOffset,
        });
        if (reset) {
          setRuns(data);
          setOffset(PAGE_SIZE);
        } else {
          setRuns(prev => [...prev, ...data]);
          setOffset(o => o + PAGE_SIZE);
        }
        setHasMore(data.length === PAGE_SIZE);
      } finally {
        setLoading(false);
      }
    },
    [filters, offset],
  );

  // Re-fetch whenever filters change
  useEffect(() => {
    fetchRuns(true);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filters]);

  function handleRowClick(run: RunRecord) {
    if (onSelectRun) {
      onSelectRun(run);
    }
  }

  function impColor(pct: number | null) {
    if (pct == null) return undefined;
    return pct > 0 ? 'var(--success)' : 'var(--danger)';
  }

  function fmtMs(ms: number | null) {
    if (ms == null) return '—';
    return `${ms}ms`;
  }

  return (
    <div className="runs-table-wrap">
      {/* Filter bar */}
      <div className="rt-filters">
        <input
          className="rt-search"
          placeholder="Search label or query…"
          value={searchInput}
          onChange={e => setSearchInput(e.target.value)}
        />

        <input
          className="rt-search rt-search--sm"
          placeholder="Filter by table…"
          value={filters.table}
          onChange={e => setFilters(f => ({ ...f, table: e.target.value }))}
        />

        <select
          className="rt-select"
          value={filters.type}
          onChange={e => setFilters(f => ({ ...f, type: e.target.value }))}
        >
          <option value="">All types</option>
          <option value="query">query</option>
          <option value="view">view</option>
          <option value="batch">batch</option>
          <option value="workload">workload</option>
        </select>

        <button
          className={`rt-toggle${filters.top ? ' rt-toggle--on' : ''}`}
          onClick={() => setFilters(f => ({ ...f, top: !f.top, regressions: false }))}
        >
          ★ Top
        </button>

        <button
          className={`rt-toggle${filters.regressions ? ' rt-toggle--on rt-toggle--danger' : ''}`}
          onClick={() => setFilters(f => ({ ...f, regressions: !f.regressions, top: false }))}
        >
          ⚠ Regressions
        </button>
      </div>

      {/* Table */}
      <div className="rt-scroll">
        <table className="rt-table">
          <thead>
            <tr>
              <th>ID</th>
              <th>Date</th>
              <th>Label / Query</th>
              <th>Tables</th>
              <th>Before</th>
              <th>After</th>
              <th>Impr.</th>
              <th>Mig.</th>
              <th>✓</th>
            </tr>
          </thead>
          <tbody>
            {runs.map(run => (
              <tr
                key={run.id}
                className="rt-row"
                onClick={() => handleRowClick(run)}
                title="Click to select for comparison"
              >
                <td className="rt-id">{run.id}</td>
                <td className="rt-date">{run.timestamp.slice(0, 16)}</td>
                <td className="rt-label">
                  {(run.label || run.query_preview || '—').slice(0, 45)}
                </td>
                <td className="rt-tables">
                  {(run.tables_involved || '—').slice(0, 22)}
                </td>
                <td className="rt-ms rt-ms--before">{fmtMs(run.before_ms)}</td>
                <td className="rt-ms rt-ms--after">{fmtMs(run.after_ms)}</td>
                <td>
                  {run.improvement_pct != null ? (
                    <span
                      className="badge"
                      style={{
                        background:
                          run.improvement_pct > 0
                            ? 'var(--success-light)'
                            : 'var(--danger-light)',
                        color: impColor(run.improvement_pct),
                        fontWeight: 600,
                      }}
                    >
                      {run.improvement_pct > 0 ? '+' : ''}
                      {run.improvement_pct.toFixed(1)}%
                    </span>
                  ) : (
                    <span className="rt-muted">—</span>
                  )}
                </td>
                <td className="rt-muted">
                  {run.migration_number ?? '—'}
                </td>
                <td>
                  <span
                    className="status-dot"
                    style={{
                      background:
                        run.success === 1 ? 'var(--success)' : 'var(--danger)',
                    }}
                  />
                </td>
              </tr>
            ))}
          </tbody>
        </table>

        {loading && (
          <div className="rt-loading">Loading…</div>
        )}

        {!loading && runs.length === 0 && (
          <div className="rt-empty">
            <div style={{ fontSize: 32, marginBottom: 8 }}>📭</div>
            <div>No runs found</div>
            <div style={{ color: 'var(--text-muted)', fontSize: 13, marginTop: 4 }}>
              Try clearing the filters or run an optimization first
            </div>
          </div>
        )}
      </div>

      {hasMore && !loading && (
        <div className="rt-loadmore">
          <button className="rt-loadmore-btn" onClick={() => fetchRuns(false)}>
            Load more
          </button>
        </div>
      )}
    </div>
  );
}

/* ── Styles ─────────────────────────────────────────────── */
const _styles = `
.runs-table-wrap {
  display: flex;
  flex-direction: column;
  gap: 0;
}

.rt-filters {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 0 12px;
  flex-wrap: wrap;
}

.rt-search {
  height: 34px;
  padding: 0 10px;
  border: 1px solid var(--border);
  border-radius: 6px;
  font-size: 13px;
  outline: none;
  background: var(--bg-surface);
  width: 220px;
}
.rt-search--sm { width: 160px; }
.rt-search:focus { border-color: var(--accent); }

.rt-select {
  height: 34px;
  padding: 0 8px;
  border: 1px solid var(--border);
  border-radius: 6px;
  font-size: 13px;
  background: var(--bg-surface);
  outline: none;
  cursor: pointer;
}

.rt-toggle {
  height: 34px;
  padding: 0 12px;
  border: 1px solid var(--border);
  border-radius: 6px;
  font-size: 12px;
  font-weight: 600;
  background: var(--bg-surface);
  cursor: pointer;
  white-space: nowrap;
  transition: all 0.15s;
}
.rt-toggle--on {
  background: var(--accent-light);
  border-color: var(--accent);
  color: var(--accent);
}
.rt-toggle--danger.rt-toggle--on {
  background: var(--danger-light);
  border-color: var(--danger);
  color: var(--danger);
}

.rt-scroll {
  overflow-x: auto;
  border: 0.5px solid var(--border);
  border-radius: 10px;
  background: var(--bg-surface);
}

.rt-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}
.rt-table th {
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
.rt-row {
  border-bottom: 1px solid var(--border);
  cursor: pointer;
  transition: background 0.1s;
}
.rt-row:hover { background: var(--bg-elevated); }
.rt-row:last-child { border-bottom: none; }
.rt-row td { padding: 9px 12px; vertical-align: middle; }

.rt-id   { color: var(--text-muted); font-size: 12px; font-family: var(--font-mono, monospace); }
.rt-date { color: var(--text-muted); font-size: 12px; white-space: nowrap; }
.rt-label { max-width: 220px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.rt-tables { color: var(--text-secondary); font-size: 12px; }
.rt-ms { font-family: var(--font-mono, monospace); font-size: 12px; white-space: nowrap; }
.rt-ms--before { color: #EF4444; }
.rt-ms--after  { color: var(--success); }
.rt-muted { color: var(--text-muted); font-size: 12px; }

.rt-loading {
  text-align: center;
  padding: 20px;
  color: var(--text-muted);
  font-size: 13px;
}
.rt-empty {
  text-align: center;
  padding: 48px 20px;
  color: var(--text-secondary);
}

.rt-loadmore {
  display: flex;
  justify-content: center;
  padding: 12px;
}
.rt-loadmore-btn {
  padding: 7px 20px;
  border: 1px solid var(--border);
  border-radius: 6px;
  font-size: 13px;
  background: var(--bg-surface);
  cursor: pointer;
  font-weight: 500;
  transition: border-color 0.15s;
}
.rt-loadmore-btn:hover { border-color: var(--accent); color: var(--accent); }
`;

if (typeof document !== 'undefined') {
  const id = 'runs-table-styles';
  if (!document.getElementById(id)) {
    const el = document.createElement('style');
    el.id = id;
    el.textContent = _styles;
    document.head.appendChild(el);
  }
}
