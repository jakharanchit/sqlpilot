import { useNavigate } from 'react-router-dom';
import type { Migration } from '../../types';

interface Props {
  migration: Migration;
}

export default function MigrationDetail({ migration: m }: Props) {
  const navigate = useNavigate();

  return (
    <div className="mig-detail">
      <div className="mig-detail__grid">
        <div className="mig-detail__field">
          <span className="mig-detail__key">Filename</span>
          <span className="mig-detail__val font-mono">{m.filename}</span>
        </div>
        <div className="mig-detail__field">
          <span className="mig-detail__key">Tables affected</span>
          <span className="mig-detail__val">
            {m.tables_affected.length > 0
              ? m.tables_affected.join(', ')
              : <em style={{ color: 'var(--text-muted)' }}>none recorded</em>}
          </span>
        </div>
        <div className="mig-detail__field">
          <span className="mig-detail__key">Reason</span>
          <span className="mig-detail__val" style={{ maxWidth: 480, wordBreak: 'break-word' }}>
            {m.reason || <em style={{ color: 'var(--text-muted)' }}>—</em>}
          </span>
        </div>
        <div className="mig-detail__field">
          <span className="mig-detail__key">Created</span>
          <span className="mig-detail__val">{m.date.slice(0, 16)}</span>
        </div>
        {m.applied_to.length > 0 && (
          <div className="mig-detail__field">
            <span className="mig-detail__key">Applied to</span>
            <span className="mig-detail__val">{m.applied_to.join(', ')}</span>
          </div>
        )}
        {m.applied_date && (
          <div className="mig-detail__field">
            <span className="mig-detail__key">Applied date</span>
            <span className="mig-detail__val">{m.applied_date.slice(0, 16)}</span>
          </div>
        )}
        {m.rollback_date && (
          <div className="mig-detail__field">
            <span className="mig-detail__key">Rolled back</span>
            <span className="mig-detail__val">{m.rollback_date.slice(0, 16)}</span>
          </div>
        )}
      </div>

      <div className="mig-detail__actions">
        <button
          className="mig-detail__open-btn"
          onClick={() => navigate('/optimizer')}
        >
          Open in Optimizer →
        </button>
      </div>
    </div>
  );
}

/* ── Styles ─────────────────────────────────────────────── */
const _styles = `
.mig-detail {
  padding: 14px 16px 14px 52px;
  background: var(--bg-elevated);
  border-top: 1px solid var(--border);
  animation: mig-detail-in 0.15s ease;
}

@keyframes mig-detail-in {
  from { opacity: 0; transform: translateY(-4px); }
  to   { opacity: 1; transform: translateY(0); }
}

.mig-detail__grid {
  display: flex;
  flex-wrap: wrap;
  gap: 12px 32px;
  margin-bottom: 12px;
}

.mig-detail__field {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.mig-detail__key {
  font-size: 10px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.07em;
  color: var(--text-muted);
}

.mig-detail__val {
  font-size: 13px;
  color: var(--text-primary);
}

.mig-detail__actions {
  margin-top: 4px;
}

.mig-detail__open-btn {
  padding: 6px 12px;
  background: none;
  border: 1px solid var(--border);
  border-radius: 6px;
  font-size: 12px;
  font-weight: 600;
  color: var(--accent);
  cursor: pointer;
  transition: background 0.15s, border-color 0.15s;
}
.mig-detail__open-btn:hover {
  background: var(--accent-light);
  border-color: var(--accent);
}
`;

if (typeof document !== 'undefined') {
  const id = 'mig-detail-styles';
  if (!document.getElementById(id)) {
    const el = document.createElement('style');
    el.id = id;
    el.textContent = _styles;
    document.head.appendChild(el);
  }
}
