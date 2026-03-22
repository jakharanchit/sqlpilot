import type { JobStatus } from '../../types';

const STEPS = [
  'Detect tables',
  'Pull schema',
  'Execution plan',
  'Parse plan',
  'Diagnose (R1)',
  'Rewrite (Qwen)',
  'Extract SQL',
  'Migrate & log',
  'Complete',
];

interface Props {
  currentStep: number;   // 0 = not started, 1–9 = in progress
  totalSteps:  number;
  stepLabel:   string;
  status:      JobStatus | null;
}

export function StepProgress({ currentStep, totalSteps, stepLabel, status }: Props) {
  const total = totalSteps || STEPS.length;

  const getStepState = (idx: number): 'done' | 'active' | 'pending' => {
    const stepNum = idx + 1;
    if (currentStep >= stepNum)  return 'done';
    if (currentStep === stepNum - 1 && status === 'running') return 'active';
    return 'pending';
  };

  if (!status) {
    return (
      <div className="step-empty">
        <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
          <circle cx="12" cy="12" r="10"/>
          <path d="M12 6v6l4 2"/>
        </svg>
        <span>Submit a query to start</span>
      </div>
    );
  }

  return (
    <div className="step-progress">
      <div className="step-track">
        {STEPS.slice(0, total).map((name, idx) => {
          const state = getStepState(idx);
          return (
            <div key={idx} className={`step-item step-${state}`}>
              <div className="step-node">
                {state === 'done' ? (
                  <svg width="10" height="10" viewBox="0 0 12 12" fill="none">
                    <path d="M2 6l3 3 5-5" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                  </svg>
                ) : state === 'active' ? (
                  <span className="step-pulse" />
                ) : (
                  <span className="step-num">{idx + 1}</span>
                )}
              </div>
              {idx < total - 1 && (
                <div className={`step-line ${state === 'done' ? 'done' : ''}`} />
              )}
              <span className="step-name">{name}</span>
            </div>
          );
        })}
      </div>

      {/* Current step label */}
      {status === 'running' && stepLabel && (
        <div className="step-current-label">
          <span className="step-running-dot" />
          {stepLabel}
        </div>
      )}

      {/* Progress bar */}
      <div className="step-bar-wrap">
        <div
          className={`step-bar-fill ${status === 'failed' ? 'failed' : status === 'completed' ? 'done' : ''}`}
          style={{ width: `${Math.round((currentStep / total) * 100)}%` }}
        />
      </div>

      {/* Status summary */}
      {(status === 'completed' || status === 'failed' || status === 'cancelled') && (
        <div className={`step-done-badge ${status}`}>
          {status === 'completed' && '✓ Pipeline complete'}
          {status === 'failed'    && '✗ Pipeline failed'}
          {status === 'cancelled' && '○ Cancelled'}
        </div>
      )}

      <style>{`
        .step-empty {
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          gap: 8px;
          height: 100%;
          color: var(--text-muted);
          font-size: 12px;
        }
        .step-progress {
          display: flex;
          flex-direction: column;
          gap: 10px;
          padding: 4px 0;
        }
        .step-track {
          display: flex;
          flex-direction: column;
          gap: 0;
        }
        .step-item {
          display: grid;
          grid-template-columns: 20px 1fr;
          grid-template-rows: auto 1fr;
          column-gap: 8px;
          position: relative;
        }
        .step-node {
          grid-row: 1;
          width: 20px; height: 20px;
          border-radius: 50%;
          display: flex;
          align-items: center;
          justify-content: center;
          font-size: 9px;
          font-weight: 700;
          flex-shrink: 0;
          position: relative;
          z-index: 1;
          transition: all 0.2s;
        }
        .step-done   .step-node { background: var(--success); color: #fff; }
        .step-active .step-node { background: var(--accent); color: #fff; }
        .step-pending .step-node { background: var(--bg-elevated); color: var(--text-muted); border: 1px solid var(--border); }
        .step-num { font-size: 8px; font-weight: 700; }
        .step-pulse {
          width: 8px; height: 8px;
          border-radius: 50%;
          background: #fff;
          animation: pulse-node 1s ease-in-out infinite;
        }
        @keyframes pulse-node {
          0%, 100% { transform: scale(1); opacity: 1; }
          50% { transform: scale(1.3); opacity: 0.7; }
        }
        .step-line {
          grid-column: 1;
          grid-row: 2;
          width: 2px;
          height: 12px;
          background: var(--border);
          margin: 0 auto;
          transition: background 0.2s;
        }
        .step-line.done { background: var(--success); }
        .step-name {
          grid-column: 2;
          grid-row: 1;
          font-size: 11px;
          line-height: 20px;
          transition: color 0.15s;
        }
        .step-done    .step-name { color: var(--text-primary); }
        .step-active  .step-name { color: var(--accent); font-weight: 600; }
        .step-pending .step-name { color: var(--text-muted); }
        .step-current-label {
          display: flex;
          align-items: center;
          gap: 6px;
          font-size: 11px;
          color: var(--accent);
          font-weight: 500;
          padding: 4px 8px;
          background: var(--accent-light);
          border-radius: 6px;
        }
        .step-running-dot {
          width: 6px; height: 6px;
          border-radius: 50%;
          background: var(--accent);
          animation: blink 1s ease-in-out infinite;
        }
        @keyframes blink { 0%,100%{opacity:1} 50%{opacity:0.3} }
        .step-bar-wrap {
          height: 4px;
          background: var(--bg-elevated);
          border-radius: 2px;
          overflow: hidden;
        }
        .step-bar-fill {
          height: 100%;
          background: var(--accent);
          border-radius: 2px;
          transition: width 0.4s ease;
        }
        .step-bar-fill.done   { background: var(--success); }
        .step-bar-fill.failed { background: var(--danger); }
        .step-done-badge {
          text-align: center;
          font-size: 11px;
          font-weight: 600;
          padding: 5px 10px;
          border-radius: 6px;
        }
        .step-done-badge.completed { background: var(--success-light); color: #166534; }
        .step-done-badge.failed    { background: var(--danger-light);  color: #991B1B; }
        .step-done-badge.cancelled { background: var(--bg-elevated);   color: var(--text-muted); }
      `}</style>
    </div>
  );
}
