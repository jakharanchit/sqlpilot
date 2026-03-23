// web/src/components/clients/ClientDetailPanel.tsx
// Shows full config for a selected client; supports editing and deletion.

import { useState, useEffect } from 'react';
import { clientsApi } from '../../api/clients';
import type { ClientConfig, UpdateClientRequest } from '../../types';

interface Props {
  name:      string;
  isActive:  boolean;
  onSwitch:  (name: string) => void;
  onDeleted: (name: string) => void;
  onUpdated: () => void;
}

type Mode = 'viewing' | 'editing';

const _styles = `
.cdp-card {
  background: var(--bg-surface);
  border: 0.5px solid var(--border);
  border-radius: 10px;
  padding: 22px 26px;
  margin-bottom: 20px;
}
.cdp-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 18px;
}
.cdp-title {
  font-family: 'JetBrains Mono', monospace;
  font-size: 15px;
  font-weight: 700;
  color: var(--text-primary);
  flex: 1;
}
.cdp-active-badge {
  font-size: 11px;
  font-weight: 700;
  padding: 3px 10px;
  border-radius: 99px;
  background: var(--accent-light);
  color: var(--accent);
}
.cdp-grid {
  display: grid;
  grid-template-columns: 160px 1fr;
  gap: 8px 16px;
  margin-bottom: 20px;
}
.cdp-label {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-muted);
  padding-top: 2px;
}
.cdp-value {
  font-size: 13px;
  color: var(--text-primary);
  word-break: break-all;
}
.cdp-value-mono {
  font-family: 'JetBrains Mono', monospace;
  font-size: 12px;
}
.cdp-value-muted {
  color: var(--text-muted);
}
.cdp-actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  padding-top: 14px;
  border-top: 0.5px solid var(--border);
}
.cdp-btn {
  padding: 7px 16px;
  border-radius: 6px;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  border: 0.5px solid var(--border-strong);
  background: var(--bg-surface);
  color: var(--text-secondary);
  transition: background 0.12s;
}
.cdp-btn:hover:not(:disabled) {
  background: var(--bg-elevated);
}
.cdp-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
.cdp-btn-primary {
  background: var(--accent);
  color: #fff;
  border-color: var(--accent);
}
.cdp-btn-primary:hover:not(:disabled) {
  background: var(--accent-hover);
}
.cdp-btn-danger {
  color: var(--danger);
  border-color: var(--danger);
}
.cdp-btn-danger:hover:not(:disabled) {
  background: var(--danger-light);
}
.cdp-btn-danger-confirm {
  background: var(--danger-light);
  color: var(--danger);
  border-color: var(--danger);
}
/* Edit form */
.cdp-edit-field {
  margin-bottom: 12px;
}
.cdp-edit-label {
  display: block;
  font-size: 12px;
  font-weight: 600;
  color: var(--text-secondary);
  margin-bottom: 4px;
}
.cdp-edit-input {
  width: 100%;
  padding: 7px 11px;
  border: 0.5px solid var(--border-strong);
  border-radius: 6px;
  font-size: 13px;
  font-family: inherit;
  color: var(--text-primary);
  background: var(--bg-base);
  box-sizing: border-box;
  outline: none;
  transition: border-color 0.15s;
}
.cdp-edit-input:focus {
  border-color: var(--accent);
}
.cdp-api-error {
  padding: 10px 14px;
  background: var(--danger-light);
  border-radius: 6px;
  font-size: 13px;
  color: var(--danger);
  margin-bottom: 12px;
}
.cdp-loading {
  padding: 32px;
  text-align: center;
  color: var(--text-muted);
  font-size: 13px;
}
`;

if (typeof document !== 'undefined') {
  const id = 'cdp-styles';
  if (!document.getElementById(id)) {
    const el = document.createElement('style');
    el.id = id;
    el.textContent = _styles;
    document.head.appendChild(el);
  }
}

export default function ClientDetailPanel({ name, isActive, onSwitch, onDeleted, onUpdated }: Props) {
  const [config,       setConfig]       = useState<ClientConfig | null>(null);
  const [mode,         setMode]         = useState<Mode>('viewing');
  const [editForm,     setEditForm]     = useState<UpdateClientRequest>({});
  const [saving,       setSaving]       = useState(false);
  const [delConfirm,   setDelConfirm]   = useState(false);
  const [deleting,     setDeleting]     = useState(false);
  const [apiError,     setApiError]     = useState('');
  const [loading,      setLoading]      = useState(true);

  useEffect(() => {
    setLoading(true);
    setMode('viewing');
    setApiError('');
    setDelConfirm(false);
    clientsApi.get(name)
      .then(d => setConfig(d.config))
      .catch(() => setApiError('Failed to load client details.'))
      .finally(() => setLoading(false));
  }, [name]);

  function startEditing() {
    if (!config) return;
    setEditForm({
      display_name: config.display_name,
      server:       config.db_config.server,
      database:     config.db_config.database,
      bak_path:     config.bak_path,
      notes:        config.notes,
    });
    setMode('editing');
    setApiError('');
  }

  async function handleSave() {
    setSaving(true);
    setApiError('');
    try {
      const updated = await clientsApi.update(name, editForm);
      setConfig(updated);
      setMode('viewing');
      onUpdated();
    } catch (err: any) {
      setApiError(err?.message ?? 'Save failed.');
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete() {
    if (!delConfirm) { setDelConfirm(true); setTimeout(() => setDelConfirm(false), 3000); return; }
    setDeleting(true);
    try {
      await clientsApi.delete(name);
      onDeleted(name);
    } catch (err: any) {
      setApiError(err?.message ?? 'Delete failed.');
      setDeleting(false);
    }
  }

  if (loading) return <div className="cdp-card"><div className="cdp-loading">Loading…</div></div>;
  if (!config) return null;

  const db = config.db_config;
  const authType = db.trusted_connection === 'yes' ? 'Windows' : 'SQL Login';

  // ── View mode ─────────────────────────────────────────────────────────────
  if (mode === 'viewing') {
    return (
      <div className="cdp-card">
        <div className="cdp-header">
          <div className="cdp-title">{name}</div>
          {isActive && <span className="cdp-active-badge">★ Active</span>}
        </div>

        <div className="cdp-grid">
          <span className="cdp-label">Display name</span>
          <span className="cdp-value">{config.display_name || <em className="cdp-value-muted">—</em>}</span>

          <span className="cdp-label">Server</span>
          <span className={`cdp-value cdp-value-mono`}>{db.server || <em className="cdp-value-muted">—</em>}</span>

          <span className="cdp-label">Database</span>
          <span className={`cdp-value cdp-value-mono`}>{db.database || <em className="cdp-value-muted">—</em>}</span>

          <span className="cdp-label">BAK path</span>
          <span className="cdp-value cdp-value-mono" style={{ fontSize: 11 }}>
            {config.bak_path || <em className="cdp-value-muted">not set</em>}
          </span>

          <span className="cdp-label">Auth</span>
          <span className="cdp-value">{authType}</span>

          <span className="cdp-label">Notes</span>
          <span className="cdp-value">{config.notes || <em className="cdp-value-muted">—</em>}</span>

          <span className="cdp-label">Migrations dir</span>
          <span className="cdp-value cdp-value-mono" style={{ fontSize: 11 }}>migrations/</span>

          <span className="cdp-label">History DB</span>
          <span className="cdp-value cdp-value-mono" style={{ fontSize: 11 }}>history.db</span>

          <span className="cdp-label">Created</span>
          <span className="cdp-value cdp-value-muted">{config.created?.slice(0, 10) || '—'}</span>
        </div>

        {apiError && <div className="cdp-api-error">✗ {apiError}</div>}

        <div className="cdp-actions">
          <button className="cdp-btn" onClick={startEditing}>Edit Settings</button>

          <button
            className="cdp-btn cdp-btn-primary"
            disabled={isActive}
            onClick={() => onSwitch(name)}
            title={isActive ? 'Already active' : `Switch to ${name}`}
          >
            {isActive ? 'Currently Active' : 'Switch to This Client'}
          </button>

          <button
            className={`cdp-btn cdp-btn-danger ${delConfirm ? 'cdp-btn-danger-confirm' : ''}`}
            disabled={isActive || deleting}
            onClick={handleDelete}
            title={isActive ? 'Cannot delete the active client' : 'Delete client workspace'}
          >
            {deleting ? 'Deleting…' : delConfirm ? 'Confirm Delete?' : 'Delete Client'}
          </button>
        </div>
      </div>
    );
  }

  // ── Edit mode ─────────────────────────────────────────────────────────────
  return (
    <div className="cdp-card">
      <div className="cdp-header">
        <div className="cdp-title">Edit — {name}</div>
      </div>

      {apiError && <div className="cdp-api-error">✗ {apiError}</div>}

      {(['display_name', 'server', 'database', 'bak_path', 'notes'] as const).map(key => (
        <div key={key} className="cdp-edit-field">
          <label className="cdp-edit-label">
            {key === 'display_name' ? 'Display name'
           : key === 'bak_path'    ? 'BAK path'
           : key.charAt(0).toUpperCase() + key.slice(1)}
          </label>
          <input
            className="cdp-edit-input"
            value={(editForm as any)[key] ?? ''}
            onChange={e => setEditForm(prev => ({ ...prev, [key]: e.target.value }))}
            disabled={saving}
          />
        </div>
      ))}

      <div className="cdp-actions">
        <button
          className="cdp-btn cdp-btn-primary"
          onClick={handleSave}
          disabled={saving}
        >
          {saving ? 'Saving…' : 'Save'}
        </button>
        <button
          className="cdp-btn"
          onClick={() => { setMode('viewing'); setApiError(''); }}
          disabled={saving}
        >
          Cancel
        </button>
      </div>
    </div>
  );
}
