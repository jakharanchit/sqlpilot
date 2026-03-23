// web/src/components/clients/ClientTable.tsx
// Full-width table of all client workspaces.


import type { ClientRecord } from '../../types';

interface Props {
  clients:      ClientRecord[];
  selectedName: string | null;
  onSelect:     (name: string) => void;
  onSwitch:     (name: string) => void;
  loading:      boolean;
}

const _styles = `
.ct-card {
  background: var(--bg-surface);
  border: 0.5px solid var(--border);
  border-radius: 10px;
  overflow: hidden;
  margin-bottom: 20px;
}
.ct-table {
  width: 100%;
  border-collapse: collapse;
}
.ct-table th {
  text-align: left;
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: var(--text-muted);
  padding: 10px 16px;
  border-bottom: 0.5px solid var(--border);
  background: var(--bg-elevated);
}
.ct-row {
  border-bottom: 0.5px solid var(--border);
  cursor: pointer;
  transition: background 0.12s;
}
.ct-row:last-child {
  border-bottom: none;
}
.ct-row:hover {
  background: var(--bg-elevated);
}
.ct-row.ct-selected {
  background: var(--accent-light);
}
.ct-row.ct-active-row {
  border-left: 3px solid var(--accent);
}
.ct-td {
  padding: 12px 16px;
  font-size: 13px;
  color: var(--text-primary);
  vertical-align: middle;
}
.ct-td-muted {
  color: var(--text-muted);
  font-size: 12px;
}
.ct-star {
  font-size: 14px;
  color: var(--accent);
}
.ct-name-mono {
  font-family: 'JetBrains Mono', monospace;
  font-size: 12px;
}
.ct-switch-btn {
  font-size: 11px;
  padding: 4px 10px;
  border-radius: 5px;
  border: 0.5px solid var(--border-strong);
  background: var(--bg-surface);
  color: var(--text-secondary);
  cursor: pointer;
  transition: background 0.12s;
  white-space: nowrap;
}
.ct-switch-btn:hover:not(:disabled) {
  background: var(--accent-light);
  color: var(--accent);
  border-color: var(--accent);
}
.ct-switch-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
.ct-loading {
  padding: 32px 16px;
  text-align: center;
  color: var(--text-muted);
  font-size: 13px;
}
.ct-empty {
  padding: 32px 16px;
  text-align: center;
  color: var(--text-muted);
  font-size: 13px;
}
`;

if (typeof document !== 'undefined') {
  const id = 'ct-styles';
  if (!document.getElementById(id)) {
    const el = document.createElement('style');
    el.id = id;
    el.textContent = _styles;
    document.head.appendChild(el);
  }
}

export default function ClientTable({ clients, selectedName, onSelect, onSwitch, loading }: Props) {
  if (loading) {
    return (
      <div className="ct-card">
        <div className="ct-loading">Loading clients…</div>
      </div>
    );
  }

  if (clients.length === 0) {
    return (
      <div className="ct-card">
        <div className="ct-empty">No client workspaces yet. Create one with + New Client.</div>
      </div>
    );
  }

  return (
    <div className="ct-card">
      <table className="ct-table">
        <thead>
          <tr>
            <th style={{ width: 32 }}></th>
            <th>Name</th>
            <th>Display Name</th>
            <th>Database</th>
            <th>Migrations</th>
            <th>Runs</th>
            <th>Created</th>
            <th style={{ width: 80 }}></th>
          </tr>
        </thead>
        <tbody>
          {clients.map(c => (
            <tr
              key={c.name}
              className={[
                'ct-row',
                c.active         ? 'ct-active-row'  : '',
                selectedName === c.name ? 'ct-selected' : '',
              ].join(' ')}
              onClick={() => onSelect(c.name)}
            >
              <td className="ct-td" style={{ textAlign: 'center' }}>
                {c.active && <span className="ct-star">★</span>}
              </td>
              <td className="ct-td">
                <span className="ct-name-mono">{c.name}</span>
              </td>
              <td className="ct-td">{c.display_name}</td>
              <td className="ct-td ct-name-mono">{c.database || '—'}</td>
              <td className="ct-td ct-td-muted">{c.migrations}</td>
              <td className="ct-td ct-td-muted">{c.runs}</td>
              <td className="ct-td ct-td-muted">{c.created}</td>
              <td className="ct-td" onClick={e => e.stopPropagation()}>
                <button
                  className="ct-switch-btn"
                  disabled={c.active}
                  onClick={() => onSwitch(c.name)}
                >
                  {c.active ? 'Active' : 'Switch'}
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
