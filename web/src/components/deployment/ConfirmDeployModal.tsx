// web/src/components/deployment/ConfirmDeployModal.tsx
import { useState, useEffect } from 'react';
import type { Migration } from '../../types';

interface Props {
  isOpen:     boolean;
  onCancel:   () => void;
  onConfirm:  () => void;
  loading:    boolean;
  migrations: Migration[];
}

const CHECKLIST = [
  'A full database backup has been taken today',
  'I am connected to the correct server and database',
  'The application (LabVIEW) is closed on all machines',
  'I have reviewed the rollback.sql plan',
] as const;

export default function ConfirmDeployModal({
  isOpen, onCancel, onConfirm, loading, migrations,
}: Props) {
  const [checked, setChecked] = useState<boolean[]>(CHECKLIST.map(() => false));

  // Reset checkboxes whenever modal opens
  useEffect(() => {
    if (isOpen) setChecked(CHECKLIST.map(() => false));
  }, [isOpen]);

  if (!isOpen) return null;

  const allChecked = checked.every(Boolean);

  function toggle(i: number) {
    setChecked(prev => {
      const next = [...prev];
      next[i] = !next[i];
      return next;
    });
  }

  return (
    <div className="cdm-overlay" onClick={(e) => e.target === e.currentTarget && onCancel()}>
      <div className="cdm-dialog card" role="dialog" aria-modal="true">
        {/* Header */}
        <div className="cdm-header">
          <h2 className="cdm-title">Generate Deployment Package?</h2>
          <button className="cdm-close" onClick={onCancel} aria-label="Close">✕</button>
        </div>

        {/* Migrations to be packaged */}
        {migrations.length > 0 && (
          <div className="cdm-migrations">
            <div className="cdm-section-label">Migrations included:</div>
            {migrations.map(m => (
              <div key={m.number} className="cdm-mig-row">
                <span className="badge badge-neutral font-mono">
                  {String(m.number).padStart(3, '0')}
                </span>
                <span className="cdm-mig-desc">{m.description}</span>
                {m.improvement_pct != null && (
                  <span className="badge badge-success cdm-mig-pct">
                    {m.improvement_pct}%
                  </span>
                )}
              </div>
            ))}
          </div>
        )}

        {/* Pre-flight checklist */}
        <div className="cdm-checklist">
          <div className="cdm-section-label">Pre-flight checklist — tick all before proceeding:</div>
          {CHECKLIST.map((label, i) => (
            <label key={i} className="cdm-check-row">
              <input
                type="checkbox"
                className="cdm-checkbox"
                checked={checked[i]}
                onChange={() => toggle(i)}
                disabled={loading}
              />
              <span className={`cdm-check-label ${checked[i] ? 'cdm-check-done' : ''}`}>
                {label}
              </span>
            </label>
          ))}
        </div>

        {/* Warning */}
        <div className="cdm-warning">
          ⚠ This action writes files to disk. The package cannot be automatically reverted —
          you must run <code>rollback.sql</code> manually if needed.
        </div>

        {/* Actions */}
        <div className="cdm-actions">
          <button
            className="cdm-btn cdm-btn-cancel"
            onClick={onCancel}
            disabled={loading}
          >
            Cancel
          </button>
          <button
            className="cdm-btn cdm-btn-confirm"
            onClick={onConfirm}
            disabled={!allChecked || loading}
          >
            {loading ? (
              <>
                <span className="spinner-sm-inline" />
                Generating…
              </>
            ) : (
              'Confirm & Generate'
            )}
          </button>
        </div>
      </div>
    </div>
  );
}

// ── Styles ────────────────────────────────────────────────────
const _styles = `
.cdm-overlay {
  position: fixed;
  inset: 0;
  background: rgba(15, 23, 42, 0.45);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 9999;
  backdrop-filter: blur(2px);
}

.cdm-dialog {
  width: 480px;
  max-width: calc(100vw - 32px);
  max-height: calc(100vh - 60px);
  overflow-y: auto;
  box-shadow: 0 20px 60px rgba(0,0,0,0.18);
  animation: cdm-in 0.18s ease;
}

@keyframes cdm-in {
  from { transform: translateY(-10px); opacity: 0; }
  to   { transform: translateY(0);     opacity: 1; }
}

.cdm-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 20px 20px 14px;
  border-bottom: 1px solid var(--border);
}

.cdm-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0;
}

.cdm-close {
  background: none;
  border: none;
  font-size: 14px;
  color: var(--text-muted);
  cursor: pointer;
  padding: 4px 6px;
  border-radius: 5px;
}
.cdm-close:hover { background: var(--bg-elevated); color: var(--text-primary); }

.cdm-section-label {
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--text-muted);
  margin-bottom: 10px;
}

.cdm-migrations {
  padding: 16px 20px;
  border-bottom: 1px solid var(--border);
  background: var(--bg-elevated);
}

.cdm-mig-row {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 5px 0;
}

.cdm-mig-desc {
  font-size: 13px;
  color: var(--text-primary);
  flex: 1;
}

.cdm-mig-pct {
  flex-shrink: 0;
}

.cdm-checklist {
  padding: 16px 20px;
  border-bottom: 1px solid var(--border);
}

.cdm-check-row {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 6px 0;
  cursor: pointer;
}

.cdm-checkbox {
  width: 16px;
  height: 16px;
  margin-top: 1px;
  accent-color: var(--accent);
  flex-shrink: 0;
  cursor: pointer;
}

.cdm-check-label {
  font-size: 13px;
  color: var(--text-secondary);
  line-height: 1.4;
  transition: color 0.15s;
}

.cdm-check-done {
  color: var(--text-muted);
  text-decoration: line-through;
}

.cdm-warning {
  margin: 0;
  padding: 12px 20px;
  font-size: 12px;
  color: var(--warning);
  background: var(--warning-light);
  border-top: 1px solid #fbbf24;
}

.cdm-warning code {
  font-family: 'JetBrains Mono', monospace;
  font-size: 11px;
  background: rgba(0,0,0,0.07);
  padding: 1px 4px;
  border-radius: 3px;
}

.cdm-actions {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 10px;
  padding: 14px 20px;
}

.cdm-btn {
  padding: 9px 18px;
  font-size: 13px;
  font-weight: 500;
  border-radius: 7px;
  border: none;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: 8px;
  transition: background 0.15s, opacity 0.15s;
}

.cdm-btn-cancel {
  background: var(--bg-elevated);
  color: var(--text-secondary);
  border: 1px solid var(--border);
}
.cdm-btn-cancel:hover:not(:disabled) { background: var(--border); }
.cdm-btn-cancel:disabled { opacity: 0.5; cursor: default; }

.cdm-btn-confirm {
  background: var(--accent);
  color: white;
  min-width: 160px;
  justify-content: center;
}
.cdm-btn-confirm:hover:not(:disabled) { background: var(--accent-hover); }
.cdm-btn-confirm:disabled { opacity: 0.5; cursor: default; }
`;

if (typeof document !== 'undefined') {
  const id = 'cdm-styles';
  if (!document.getElementById(id)) {
    const el = document.createElement('style');
    el.id = id;
    el.textContent = _styles;
    document.head.appendChild(el);
  }
}
