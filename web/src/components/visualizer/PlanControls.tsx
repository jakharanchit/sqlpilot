// web/src/components/visualizer/PlanControls.tsx

interface Props {
  onZoomIn:    () => void;
  onZoomOut:   () => void;
  onFitScreen: () => void;
}

const _styles = `
.plan-controls {
  display: flex;
  flex-direction: column;
  gap: 4px;
  position: absolute;
  top: 12px;
  right: 12px;
  z-index: 10;
}

.plan-ctrl-btn {
  width: 32px;
  height: 32px;
  border: 1px solid var(--border);
  background: var(--bg-surface);
  border-radius: 6px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 16px;
  line-height: 1;
  color: var(--text-secondary);
  transition: background 0.15s, color 0.15s, border-color 0.15s;
  box-shadow: 0 1px 3px rgba(0,0,0,0.08);
  font-family: 'DM Sans', system-ui, sans-serif;
}

.plan-ctrl-btn:hover {
  background: var(--bg-elevated);
  color: var(--accent);
  border-color: var(--accent);
}

.plan-ctrl-btn:active {
  background: var(--accent-light);
}
`;

if (typeof document !== 'undefined') {
  const id = 'plan-controls-styles';
  if (!document.getElementById(id)) {
    const el = document.createElement('style');
    el.id = id;
    el.textContent = _styles;
    document.head.appendChild(el);
  }
}

export default function PlanControls({ onZoomIn, onZoomOut, onFitScreen }: Props) {
  return (
    <div className="plan-controls">
      <button
        className="plan-ctrl-btn"
        onClick={onZoomIn}
        title="Zoom in"
        aria-label="Zoom in"
      >
        +
      </button>
      <button
        className="plan-ctrl-btn"
        onClick={onZoomOut}
        title="Zoom out"
        aria-label="Zoom out"
      >
        −
      </button>
      <button
        className="plan-ctrl-btn"
        onClick={onFitScreen}
        title="Fit to screen"
        aria-label="Fit to screen"
        style={{ fontSize: '14px' }}
      >
        ⊡
      </button>
    </div>
  );
}
