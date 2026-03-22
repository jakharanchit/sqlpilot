import { useJobStore } from '../../store/jobStore';

const STEP_NAMES = [
  'Detect tables', 'Pull schema', 'Execution plan', 'Parse plan',
  'Diagnose (R1)', 'Rewrite (Qwen)', 'Extract SQL', 'Migrate & log', 'Complete',
];

export function ActiveJobCard() {
  const { status, currentStep, totalSteps, stepLabel } = useJobStore();

  const isActive = status === 'running' || status === 'queued';

  if (!isActive && !status) {
    return (
      <div className="card ajc-card ajc-idle">
        <div className="ajc-idle-inner">
          <div className="ajc-idle-icon">⚡</div>
          <div>
            <div className="ajc-idle-title">No active job</div>
            <div className="ajc-idle-sub">Go to Optimizer to run a pipeline</div>
          </div>
        </div>
      </div>
    );
  }

  const pct   = totalSteps > 0 ? Math.round((currentStep / totalSteps) * 100) : 0;
  const steps = STEP_NAMES.slice(0, totalSteps);

  return (
    <div className="card ajc-card">
      {/* Header */}
      <div className="ajc-header">
        <div className="ajc-title-row">
          {isActive && <span className="ajc-dot" />}
          <span className="ajc-title">
            {isActive ? 'Pipeline running' : status === 'completed' ? '✓ Pipeline complete' : `Pipeline ${status}`}
          </span>
        </div>
        <span className="ajc-pct">{pct}%</span>
      </div>

      {/* Progress bar */}
      <div className="ajc-bar">
        <div
          className={`ajc-fill ${status === 'completed' ? 'done' : status === 'failed' ? 'fail' : ''}`}
          style={{ width: `${pct}%` }}
        />
      </div>

      {/* Current label */}
      {stepLabel && (
        <div className="ajc-label">
          {isActive ? `Step ${currentStep}/${totalSteps} — ` : ''}{stepLabel}
        </div>
      )}

      {/* Step bubbles */}
      <div className="ajc-bubbles">
        {steps.map((name, i) => {
          const n = i + 1;
          const done   = currentStep >= n;
          const active = isActive && currentStep === n - 1;
          return (
            <div
              key={i}
              className={`ajc-bubble ${done ? 'done' : active ? 'active' : 'pending'}`}
              title={name}
            >
              {done ? '✓' : <span>{n}</span>}
            </div>
          );
        })}
      </div>

      <style>{`
        .ajc-card { padding: 14px; }
        .ajc-idle { display: flex; align-items: center; }
        .ajc-idle-inner { display: flex; align-items: center; gap: 12px; }
        .ajc-idle-icon { font-size: 20px; opacity: 0.4; }
        .ajc-idle-title { font-size: 13px; font-weight: 600; color: var(--text-primary); }
        .ajc-idle-sub { font-size: 11px; color: var(--text-muted); }
        .ajc-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }
        .ajc-title-row { display: flex; align-items: center; gap: 7px; }
        .ajc-dot {
          width: 7px; height: 7px;
          border-radius: 50%;
          background: var(--accent);
          animation: blink 1s ease-in-out infinite;
          flex-shrink: 0;
        }
        @keyframes blink { 0%,100%{opacity:1} 50%{opacity:0.3} }
        .ajc-title { font-size: 13px; font-weight: 600; color: var(--text-primary); }
        .ajc-pct { font-size: 13px; font-weight: 700; color: var(--accent); }
        .ajc-bar {
          height: 5px;
          background: var(--bg-elevated);
          border-radius: 3px;
          overflow: hidden;
          margin-bottom: 8px;
        }
        .ajc-fill {
          height: 100%;
          background: var(--accent);
          border-radius: 3px;
          transition: width 0.4s ease;
        }
        .ajc-fill.done { background: var(--success); }
        .ajc-fill.fail { background: var(--danger); }
        .ajc-label { font-size: 11px; color: var(--text-muted); margin-bottom: 10px; }
        .ajc-bubbles { display: flex; gap: 5px; flex-wrap: wrap; }
        .ajc-bubble {
          width: 22px; height: 22px;
          border-radius: 50%;
          display: flex;
          align-items: center;
          justify-content: center;
          font-size: 8px;
          font-weight: 700;
          flex-shrink: 0;
          transition: all 0.2s;
        }
        .ajc-bubble.done    { background: var(--success); color: #fff; font-size: 10px; }
        .ajc-bubble.active  { background: var(--accent);  color: #fff; animation: pulse-bubble 1s ease-in-out infinite; }
        .ajc-bubble.pending { background: var(--bg-elevated); color: var(--text-muted); border: 1px solid var(--border); }
        @keyframes pulse-bubble { 0%,100%{transform:scale(1)} 50%{transform:scale(1.15)} }
      `}</style>
    </div>
  );
}
