// web/src/components/clients/NewClientModal.tsx
// Modal form to create a new client workspace.

import { useState, useEffect } from 'react';
import { clientsApi } from '../../api/clients';
import type { NewClientRequest } from '../../types';

interface Props {
  isOpen:    boolean;
  onCancel:  () => void;
  onCreated: (name: string) => void;
}

const SLUG_RE = /^[a-zA-Z0-9_-]+$/;

const _styles = `
.ncm-overlay {
  position: fixed;
  inset: 0;
  background: rgba(15, 23, 42, 0.45);
  z-index: 1000;
  display: flex;
  align-items: center;
  justify-content: center;
}
.ncm-box {
  background: var(--bg-surface);
  border-radius: 12px;
  border: 0.5px solid var(--border);
  width: 480px;
  max-width: calc(100vw - 32px);
  padding: 28px 32px;
  box-shadow: 0 20px 60px rgba(0,0,0,0.15);
}
.ncm-title {
  font-size: 16px;
  font-weight: 700;
  color: var(--text-primary);
  margin-bottom: 20px;
}
.ncm-field {
  margin-bottom: 14px;
}
.ncm-label {
  display: block;
  font-size: 12px;
  font-weight: 600;
  color: var(--text-secondary);
  margin-bottom: 5px;
}
.ncm-required {
  color: var(--danger);
}
.ncm-input {
  width: 100%;
  padding: 8px 12px;
  border: 0.5px solid var(--border-strong);
  border-radius: 6px;
  font-size: 13px;
  font-family: inherit;
  color: var(--text-primary);
  background: var(--bg-base);
  outline: none;
  box-sizing: border-box;
  transition: border-color 0.15s;
}
.ncm-input:focus {
  border-color: var(--accent);
}
.ncm-input.ncm-input-error {
  border-color: var(--danger);
}
.ncm-input-hint {
  font-size: 11px;
  color: var(--text-muted);
  margin-top: 3px;
}
.ncm-input-error-msg {
  font-size: 11px;
  color: var(--danger);
  margin-top: 3px;
}
.ncm-api-error {
  padding: 10px 14px;
  background: var(--danger-light);
  border-radius: 6px;
  font-size: 13px;
  color: var(--danger);
  margin-bottom: 14px;
}
.ncm-footer {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  margin-top: 22px;
}
.ncm-cancel-btn {
  padding: 8px 18px;
  border: 0.5px solid var(--border-strong);
  border-radius: 6px;
  background: var(--bg-surface);
  color: var(--text-secondary);
  font-size: 13px;
  cursor: pointer;
}
.ncm-cancel-btn:hover {
  background: var(--bg-elevated);
}
.ncm-create-btn {
  padding: 8px 20px;
  border: none;
  border-radius: 6px;
  background: var(--accent);
  color: #fff;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.15s;
}
.ncm-create-btn:hover:not(:disabled) {
  background: var(--accent-hover);
}
.ncm-create-btn:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}
`;

if (typeof document !== 'undefined') {
  const id = 'ncm-styles';
  if (!document.getElementById(id)) {
    const el = document.createElement('style');
    el.id = id;
    el.textContent = _styles;
    document.head.appendChild(el);
  }
}

const BLANK: NewClientRequest = {
  name: '', display_name: '', server: '', database: '', bak_path: '', notes: '',
};

export default function NewClientModal({ isOpen, onCancel, onCreated }: Props) {
  const [form,     setForm]     = useState<NewClientRequest>(BLANK);
  const [submitting, setSubmitting] = useState(false);
  const [apiError, setApiError] = useState('');
  const [nameError, setNameError] = useState('');

  // Reset form when modal opens
  useEffect(() => {
    if (isOpen) {
      setForm(BLANK);
      setApiError('');
      setNameError('');
    }
  }, [isOpen]);

  if (!isOpen) return null;

  function set(key: keyof NewClientRequest, value: string) {
    setForm(prev => ({ ...prev, [key]: value }));
    if (key === 'name') {
      if (value && !SLUG_RE.test(value)) {
        setNameError('Only letters, numbers, _ and - are allowed.');
      } else {
        setNameError('');
      }
    }
  }

  async function handleSubmit() {
    if (!form.name.trim() || nameError) return;
    setSubmitting(true);
    setApiError('');
    try {
      const result = await clientsApi.create(form);
      onCreated(result.name);
    } catch (err: any) {
      setApiError(err?.message ?? 'Failed to create client workspace.');
    } finally {
      setSubmitting(false);
    }
  }

  const canSubmit = !!form.name.trim() && !nameError && !submitting;

  return (
    <div className="ncm-overlay" onClick={e => { if (e.target === e.currentTarget) onCancel(); }}>
      <div className="ncm-box">
        <div className="ncm-title">New Client Workspace</div>

        {apiError && <div className="ncm-api-error">✗ {apiError}</div>}

        <div className="ncm-field">
          <label className="ncm-label">
            Folder name <span className="ncm-required">*</span>
          </label>
          <input
            className={`ncm-input ${nameError ? 'ncm-input-error' : ''}`}
            placeholder="client_xyz"
            value={form.name}
            onChange={e => set('name', e.target.value)}
            disabled={submitting}
            autoFocus
          />
          {nameError
            ? <div className="ncm-input-error-msg">{nameError}</div>
            : <div className="ncm-input-hint">Used as folder name. e.g. client_xyz</div>
          }
        </div>

        <div className="ncm-field">
          <label className="ncm-label">Display name</label>
          <input
            className="ncm-input"
            placeholder="XYZ Corp"
            value={form.display_name}
            onChange={e => set('display_name', e.target.value)}
            disabled={submitting}
          />
        </div>

        <div className="ncm-field">
          <label className="ncm-label">SQL Server</label>
          <input
            className="ncm-input"
            placeholder="localhost or localhost\SQLEXPRESS"
            value={form.server}
            onChange={e => set('server', e.target.value)}
            disabled={submitting}
          />
        </div>

        <div className="ncm-field">
          <label className="ncm-label">Database</label>
          <input
            className="ncm-input"
            placeholder="XYZDev"
            value={form.database}
            onChange={e => set('database', e.target.value)}
            disabled={submitting}
          />
        </div>

        <div className="ncm-field">
          <label className="ncm-label">BAK path</label>
          <input
            className="ncm-input"
            placeholder="C:\Backups\XYZ.bak"
            value={form.bak_path}
            onChange={e => set('bak_path', e.target.value)}
            disabled={submitting}
          />
        </div>

        <div className="ncm-field">
          <label className="ncm-label">Notes</label>
          <input
            className="ncm-input"
            placeholder="Optional notes…"
            value={form.notes}
            onChange={e => set('notes', e.target.value)}
            disabled={submitting}
          />
        </div>

        <div className="ncm-footer">
          <button className="ncm-cancel-btn" onClick={onCancel} disabled={submitting}>
            Cancel
          </button>
          <button
            className="ncm-create-btn"
            onClick={handleSubmit}
            disabled={!canSubmit}
          >
            {submitting ? 'Creating…' : 'Create Workspace'}
          </button>
        </div>
      </div>
    </div>
  );
}
