// web/src/components/models/ActiveModelsPanel.tsx
// Shows which Ollama models are configured as optimizer / reasoner.


import type { ActiveModels } from '../../types';

interface Props {
  active: ActiveModels;
}

const _styles = `
.amp-card {
  background: var(--bg-surface);
  border: 0.5px solid var(--border);
  border-radius: 10px;
  padding: 20px 24px;
  margin-bottom: 20px;
}
.amp-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.06em;
  margin-bottom: 16px;
}
.amp-row {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 0;
  border-bottom: 0.5px solid var(--border);
}
.amp-row:last-of-type {
  border-bottom: none;
}
.amp-role {
  width: 80px;
  font-size: 12px;
  font-weight: 600;
  color: var(--text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  flex-shrink: 0;
}
.amp-model-name {
  font-family: 'JetBrains Mono', monospace;
  font-size: 13px;
  color: var(--text-primary);
  flex: 1;
}
.amp-badge-ok {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  background: var(--success-light);
  color: var(--success);
  font-size: 11px;
  font-weight: 600;
  padding: 3px 9px;
  border-radius: 99px;
}
.amp-badge-missing {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  background: var(--danger-light);
  color: var(--danger);
  font-size: 11px;
  font-weight: 600;
  padding: 3px 9px;
  border-radius: 99px;
}
.amp-warn {
  margin-top: 12px;
  padding: 10px 14px;
  background: var(--warning-light);
  border-radius: 6px;
  font-size: 12px;
  color: var(--warning);
}
.amp-warn code {
  font-family: 'JetBrains Mono', monospace;
  font-size: 11px;
}
.amp-note {
  margin-top: 14px;
  font-size: 12px;
  color: var(--text-muted);
  display: flex;
  align-items: center;
  gap: 6px;
}
`;

if (typeof document !== 'undefined') {
  const id = 'amp-styles';
  if (!document.getElementById(id)) {
    const el = document.createElement('style');
    el.id = id;
    el.textContent = _styles;
    document.head.appendChild(el);
  }
}

export default function ActiveModelsPanel({ active }: Props) {
  const missingModels = [
    !active.optimizer_available && active.optimizer,
    !active.reasoner_available  && active.reasoner,
  ].filter(Boolean) as string[];

  return (
    <div className="amp-card">
      <div className="amp-title">Active Models (from config.py)</div>

      <div className="amp-row">
        <span className="amp-role">Optimizer</span>
        <span className="amp-model-name">{active.optimizer || '—'}</span>
        {active.optimizer && (
          active.optimizer_available
            ? <span className="amp-badge-ok">● available</span>
            : <span className="amp-badge-missing">✗ not pulled</span>
        )}
      </div>

      <div className="amp-row">
        <span className="amp-role">Reasoner</span>
        <span className="amp-model-name">{active.reasoner || '—'}</span>
        {active.reasoner && (
          active.reasoner_available
            ? <span className="amp-badge-ok">● available</span>
            : <span className="amp-badge-missing">✗ not pulled</span>
        )}
      </div>

      {missingModels.length > 0 && (
        <div className="amp-warn">
          ⚠ Missing model{missingModels.length > 1 ? 's' : ''}: pull{' '}
          {missingModels.map((m, i) => (
            <span key={m}>
              {i > 0 && ' and '}
              <code>{m}</code>
            </span>
          ))}{' '}
          below to enable the optimization pipeline.
        </div>
      )}

      <div className="amp-note">
        ⓘ Edit <code style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 11 }}>MODELS</code> in{' '}
        <code style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 11 }}>config.py</code>{' '}
        to change which models are used.
      </div>
    </div>
  );
}
