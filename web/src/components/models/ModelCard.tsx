// web/src/components/models/ModelCard.tsx
// Displays one pulled Ollama model with size, metadata, role badges, delete button.

import { useState, useEffect } from 'react';
import type { OllamaModel } from '../../types';

interface Props {
  model:       OllamaModel;
  activeRoles: string[];   // e.g. ["optimizer"] or ["optimizer","reasoner"] or []
  onDelete:    (name: string) => void;
  deleting:    boolean;
}

const _styles = `
.mc-card {
  border: 0.5px solid var(--border);
  border-radius: 8px;
  padding: 14px 18px;
  margin-bottom: 10px;
  background: var(--bg-surface);
  display: flex;
  align-items: center;
  gap: 16px;
  transition: border-color 0.15s;
}
.mc-card:hover {
  border-color: var(--border-strong);
}
.mc-main {
  flex: 1;
  min-width: 0;
}
.mc-name {
  font-family: 'JetBrains Mono', monospace;
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 4px;
}
.mc-meta {
  font-size: 12px;
  color: var(--text-muted);
}
.mc-meta span + span::before {
  content: ' · ';
}
.mc-badges {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
  margin-top: 6px;
}
.mc-role-badge {
  font-size: 11px;
  font-weight: 600;
  padding: 2px 8px;
  border-radius: 99px;
  letter-spacing: 0.03em;
}
.mc-role-optimizer {
  background: var(--accent-light);
  color: var(--accent);
}
.mc-role-reasoner {
  background: #EDE9FE;
  color: #7C3AED;
}
.mc-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}
.mc-delete-btn {
  font-size: 12px;
  padding: 5px 12px;
  border-radius: 6px;
  border: 0.5px solid var(--border-strong);
  background: var(--bg-surface);
  color: var(--text-secondary);
  cursor: pointer;
  transition: background 0.15s, color 0.15s;
}
.mc-delete-btn:hover:not(:disabled) {
  background: var(--danger-light);
  color: var(--danger);
  border-color: var(--danger);
}
.mc-delete-btn:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}
.mc-delete-confirm {
  background: var(--danger-light) !important;
  color: var(--danger) !important;
  border-color: var(--danger) !important;
}
.mc-tooltip {
  font-size: 11px;
  color: var(--text-muted);
  max-width: 180px;
}
`;

if (typeof document !== 'undefined') {
  const id = 'mc-styles';
  if (!document.getElementById(id)) {
    const el = document.createElement('style');
    el.id = id;
    el.textContent = _styles;
    document.head.appendChild(el);
  }
}

function formatDate(iso: string): string {
  if (!iso) return '';
  try {
    const d = new Date(iso);
    const diff = Math.floor((Date.now() - d.getTime()) / 86400000);
    if (diff === 0) return 'today';
    if (diff === 1) return '1d ago';
    if (diff < 30) return `${diff}d ago`;
    return d.toLocaleDateString();
  } catch {
    return '';
  }
}

export default function ModelCard({ model, activeRoles, onDelete, deleting }: Props) {
  const [confirming, setConfirming] = useState(false);
  const isActive = activeRoles.length > 0;

  // Auto-reset confirm state after 3 seconds
  useEffect(() => {
    if (!confirming) return;
    const t = setTimeout(() => setConfirming(false), 3000);
    return () => clearTimeout(t);
  }, [confirming]);

  function handleDeleteClick() {
    if (isActive) return;
    if (confirming) {
      onDelete(model.name);
      setConfirming(false);
    } else {
      setConfirming(true);
    }
  }

  return (
    <div className="mc-card">
      <div className="mc-main">
        <div className="mc-name">{model.name}</div>
        <div className="mc-meta">
          <span>{model.size_gb}</span>
          {model.quantization && <span>{model.quantization}</span>}
          {model.family      && <span>{model.family}</span>}
          {model.parameter_size && <span>{model.parameter_size}</span>}
          {model.modified_at && <span>modified {formatDate(model.modified_at)}</span>}
        </div>
        {activeRoles.length > 0 && (
          <div className="mc-badges">
            {activeRoles.map(role => (
              <span
                key={role}
                className={`mc-role-badge mc-role-${role}`}
              >
                used as {role}
              </span>
            ))}
          </div>
        )}
      </div>

      <div className="mc-actions">
        {isActive ? (
          <span className="mc-tooltip">Remove from config.py first</span>
        ) : (
          <button
            className={`mc-delete-btn ${confirming ? 'mc-delete-confirm' : ''}`}
            onClick={handleDeleteClick}
            disabled={deleting}
            title={isActive ? 'Remove from config.py first' : 'Delete model'}
          >
            {deleting ? 'Deleting…' : confirming ? 'Confirm?' : 'Delete'}
          </button>
        )}
      </div>
    </div>
  );
}
