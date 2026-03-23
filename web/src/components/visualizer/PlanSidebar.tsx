// web/src/components/visualizer/PlanSidebar.tsx
import type { PlanOperator, StructuredPlan } from '../../types';

interface Props {
  operator:   PlanOperator | null;
  plan:       StructuredPlan;
  onDeselect: () => void;
}

const _styles = `
.plan-sidebar {
  width: 280px;
  flex-shrink: 0;
  background: var(--bg-surface);
  border: 0.5px solid var(--border);
  border-radius: 10px;
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 16px;
  font-family: 'DM Sans', system-ui, sans-serif;
  align-self: flex-start;
  position: sticky;
  top: 80px;
}

.ps-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.ps-op-name {
  font-family: 'JetBrains Mono', monospace;
  font-size: 16px;
  font-weight: 600;
  color: var(--text-primary);
  word-break: break-word;
}

.ps-field-row {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.ps-field-label {
  font-size: 11px;
  font-weight: 600;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.ps-field-value {
  font-size: 13px;
  color: var(--text-primary);
  font-family: 'JetBrains Mono', monospace;
}

.ps-reason-box {
  background: var(--warning-light);
  border-left: 3px solid var(--warning);
  border-radius: 4px;
  padding: 8px 10px;
  font-size: 12px;
  color: #92400E;
  line-height: 1.5;
}

.ps-reason-box.HIGH {
  background: var(--danger-light);
  border-color: var(--danger);
  color: #7F1D1D;
}

.ps-reason-box.INFO {
  background: var(--accent-light);
  border-color: var(--accent);
  color: #1E40AF;
}

.ps-back-link {
  font-size: 12px;
  color: var(--accent);
  cursor: pointer;
  background: none;
  border: none;
  padding: 0;
  text-align: left;
  font-family: inherit;
}

.ps-back-link:hover {
  text-decoration: underline;
}

.ps-divider {
  border: none;
  border-top: 0.5px solid var(--border);
  margin: 0;
}

.ps-legend-row {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.ps-legend-item {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 11px;
  color: var(--text-secondary);
}

.ps-legend-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
}

.ps-summary-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}

.ps-summary-card {
  background: var(--bg-elevated);
  border-radius: 6px;
  padding: 8px 10px;
}

.ps-summary-card-label {
  font-size: 10px;
  font-weight: 600;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.04em;
  margin-bottom: 2px;
}

.ps-summary-card-value {
  font-size: 14px;
  font-weight: 700;
  color: var(--text-primary);
  font-family: 'JetBrains Mono', monospace;
}

.ps-click-hint {
  font-size: 12px;
  color: var(--text-muted);
  text-align: center;
  padding: 8px 0;
  font-style: italic;
}
`;

if (typeof document !== 'undefined') {
  const id = 'plan-sidebar-styles';
  if (!document.getElementById(id)) {
    const el = document.createElement('style');
    el.id = id;
    el.textContent = _styles;
    document.head.appendChild(el);
  }
}

function SummaryView({ plan }: { plan: StructuredPlan }) {
  return (
    <>
      <div>
        <div className="ps-title">Plan Summary</div>
      </div>

      <div className="ps-summary-grid">
        <div className="ps-summary-card">
          <div className="ps-summary-card-label">Type</div>
          <div className="ps-summary-card-value" style={{ fontSize: '12px', textTransform: 'uppercase' }}>
            {plan.plan_type}
          </div>
        </div>
        <div className="ps-summary-card">
          <div className="ps-summary-card-label">Operators</div>
          <div className="ps-summary-card-value">{plan.operator_count}</div>
        </div>
        {plan.elapsed_ms != null && (
          <div className="ps-summary-card">
            <div className="ps-summary-card-label">Elapsed</div>
            <div className="ps-summary-card-value">{plan.elapsed_ms}ms</div>
          </div>
        )}
        {plan.row_count != null && (
          <div className="ps-summary-card">
            <div className="ps-summary-card-label">Rows</div>
            <div className="ps-summary-card-value">{plan.row_count.toLocaleString()}</div>
          </div>
        )}
        <div className="ps-summary-card" style={{ gridColumn: '1 / -1' }}>
          <div className="ps-summary-card-label">Total Cost</div>
          <div className="ps-summary-card-value">{plan.total_cost.toFixed(4)}</div>
        </div>
      </div>

      <hr className="ps-divider" />

      <div>
        <div className="ps-title" style={{ marginBottom: '8px' }}>Legend</div>
        <div className="ps-legend-row">
          <div className="ps-legend-item">
            <div className="ps-legend-dot" style={{ background: '#DC2626' }} />
            <span>HIGH</span>
          </div>
          <div className="ps-legend-item">
            <div className="ps-legend-dot" style={{ background: '#D97706' }} />
            <span>MEDIUM</span>
          </div>
          <div className="ps-legend-item">
            <div className="ps-legend-dot" style={{ background: '#2563EB' }} />
            <span>INFO</span>
          </div>
          <div className="ps-legend-item">
            <div className="ps-legend-dot" style={{ background: '#CBD5E1' }} />
            <span>Normal</span>
          </div>
        </div>
      </div>

      <hr className="ps-divider" />
      <p className="ps-click-hint">Click any node to inspect it</p>
    </>
  );
}

function OperatorDetailView({ operator, onDeselect }: { operator: PlanOperator; onDeselect: () => void }) {
  const reasonClass = operator.severity === 'HIGH' ? 'HIGH' : operator.severity === 'INFO' ? 'INFO' : '';

  return (
    <>
      <div>
        <div className="ps-title">Operator Detail</div>
      </div>

      <div>
        <div className="ps-op-name">{operator.name}</div>
        {operator.severity && (
          <span
            className={`badge badge-${operator.severity === 'HIGH' ? 'danger' : operator.severity === 'MEDIUM' ? 'warning' : 'info'}`}
            style={{ marginTop: '6px', display: 'inline-block' }}
          >
            {operator.severity}
          </span>
        )}
      </div>

      <hr className="ps-divider" />

      <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
        <div className="ps-field-row">
          <div className="ps-field-label">Cost</div>
          <div className="ps-field-value">{operator.cost.toFixed(6)}</div>
          <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>{operator.cost_pct}% of total</div>
        </div>

        <div className="ps-field-row">
          <div className="ps-field-label">Estimated Rows</div>
          <div className="ps-field-value">{operator.est_rows.toLocaleString()}</div>
        </div>

        <div className="ps-field-row">
          <div className="ps-field-label">Actual Rows</div>
          <div className="ps-field-value">
            {operator.act_rows != null ? operator.act_rows.toLocaleString() : '—'}
          </div>
        </div>

        {operator.object && (
          <div className="ps-field-row">
            <div className="ps-field-label">Object</div>
            <div className="ps-field-value" style={{ fontSize: '12px', wordBreak: 'break-all' }}>
              {operator.object}
            </div>
          </div>
        )}

        {operator.seek_pred && (
          <div className="ps-field-row">
            <div className="ps-field-label">Seek Predicates</div>
            <div className="ps-field-value" style={{ fontSize: '11px', wordBreak: 'break-all' }}>
              {operator.seek_pred}
            </div>
          </div>
        )}
      </div>

      {operator.reason && (
        <>
          <hr className="ps-divider" />
          <div className={`ps-reason-box ${reasonClass}`}>
            ⚠ {operator.reason}
          </div>
        </>
      )}

      <hr className="ps-divider" />
      <button className="ps-back-link" onClick={onDeselect}>
        ← Back to plan summary
      </button>
    </>
  );
}

export default function PlanSidebar({ operator, plan, onDeselect }: Props) {
  return (
    <div className="plan-sidebar">
      {operator
        ? <OperatorDetailView operator={operator} onDeselect={onDeselect} />
        : <SummaryView plan={plan} />
      }
    </div>
  );
}
