// web/src/pages/PlanVisualizer.tsx
import { useRef, useState } from 'react';
import Editor from '@monaco-editor/react';
import { planApi } from '../api/plan';
import PlanTree, { type PlanTreeHandle } from '../components/visualizer/PlanTree';
import PlanSidebar from '../components/visualizer/PlanSidebar';
import PlanControls from '../components/visualizer/PlanControls';
import type {
  MissingIndexHint,
  PlanOperator,
  PlanWarning,
  StructuredPlan,
} from '../types';

// ── Styles ─────────────────────────────────────────────────────────────────────
const _styles = `
/* Page container */
.pv-page {
  display: flex;
  flex-direction: column;
  gap: 20px;
  padding: 24px;
  max-width: 1280px;
  margin: 0 auto;
  font-family: 'DM Sans', system-ui, sans-serif;
}

/* Page header */
.pv-header {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.pv-header-title {
  font-size: 22px;
  font-weight: 700;
  color: var(--text-primary);
}

.pv-header-sub {
  font-size: 14px;
  color: var(--text-muted);
}

/* Query input panel */
.pv-input-card {
  background: var(--bg-surface);
  border: 0.5px solid var(--border);
  border-radius: 10px;
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.pv-editor-label {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.pv-editor-wrap {
  border: 1px solid var(--border);
  border-radius: 6px;
  overflow: hidden;
}

.pv-input-row {
  display: flex;
  align-items: center;
  gap: 16px;
  flex-wrap: wrap;
}

.pv-plan-type-group {
  display: flex;
  gap: 6px;
}

.pv-plan-type-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 14px;
  border: 1px solid var(--border);
  border-radius: 6px;
  background: var(--bg-surface);
  cursor: pointer;
  font-size: 13px;
  font-family: 'DM Sans', system-ui, sans-serif;
  color: var(--text-secondary);
  transition: all 0.15s;
}

.pv-plan-type-btn.active {
  border-color: var(--accent);
  background: var(--accent-light);
  color: var(--accent);
  font-weight: 600;
}

.pv-plan-type-btn:hover:not(.active) {
  background: var(--bg-elevated);
}

.pv-analyze-btn {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 20px;
  background: var(--accent);
  color: #fff;
  border: none;
  border-radius: 6px;
  font-size: 14px;
  font-weight: 600;
  font-family: 'DM Sans', system-ui, sans-serif;
  cursor: pointer;
  transition: background 0.15s;
  margin-left: auto;
}

.pv-analyze-btn:hover:not(:disabled) {
  background: var(--accent-hover);
}

.pv-analyze-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.pv-spinner {
  width: 14px;
  height: 14px;
  border: 2px solid rgba(255,255,255,0.4);
  border-top-color: #fff;
  border-radius: 50%;
  animation: pv-spin 0.7s linear infinite;
}

@keyframes pv-spin {
  to { transform: rotate(360deg); }
}

/* Error banner */
.pv-error {
  background: var(--danger-light);
  border: 0.5px solid var(--danger);
  border-radius: 8px;
  padding: 12px 16px;
  color: #7F1D1D;
  font-size: 14px;
  display: flex;
  gap: 10px;
  align-items: flex-start;
}

/* Main two-column layout */
.pv-main {
  display: flex;
  gap: 16px;
  align-items: flex-start;
}

.pv-tree-container {
  flex: 1;
  min-width: 0;
  position: relative;
  background: var(--bg-surface);
  border: 0.5px solid var(--border);
  border-radius: 10px;
  overflow: hidden;
}

/* Warning and index panels */
.pv-panel {
  background: var(--bg-surface);
  border-radius: 10px;
  padding: 16px 20px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.pv-panel.warning {
  border: 0.5px solid #D97706;
  border-left: 4px solid #D97706;
}

.pv-panel.missing {
  border: 0.5px solid var(--accent);
  border-left: 4px solid var(--accent);
}

.pv-panel-title {
  font-size: 13px;
  font-weight: 700;
  color: var(--text-primary);
  display: flex;
  align-items: center;
  gap: 6px;
}

.pv-panel-row {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding-bottom: 10px;
  border-bottom: 0.5px solid var(--border);
}

.pv-panel-row:last-child {
  border-bottom: none;
  padding-bottom: 0;
}

.pv-panel-row-label {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-primary);
}

.pv-panel-row-detail {
  font-size: 12px;
  color: var(--text-secondary);
  line-height: 1.5;
}

.pv-code-block {
  background: var(--bg-elevated);
  border-radius: 4px;
  padding: 8px 10px;
  font-family: 'JetBrains Mono', monospace;
  font-size: 11px;
  color: var(--text-primary);
  white-space: pre;
  overflow-x: auto;
  border: 0.5px solid var(--border);
  margin-top: 4px;
}

/* Empty state */
.pv-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  padding: 56px 24px;
  text-align: center;
  background: var(--bg-surface);
  border: 0.5px solid var(--border);
  border-radius: 10px;
}

.pv-empty-icon {
  font-size: 40px;
}

.pv-empty-title {
  font-size: 18px;
  font-weight: 600;
  color: var(--text-primary);
}

.pv-empty-desc {
  font-size: 14px;
  color: var(--text-muted);
  max-width: 400px;
  line-height: 1.6;
}
`;

if (typeof document !== 'undefined') {
  const id = 'pv-styles';
  if (!document.getElementById(id)) {
    const el = document.createElement('style');
    el.id = id;
    el.textContent = _styles;
    document.head.appendChild(el);
  }
}

// ── Inline sub-components ──────────────────────────────────────────────────────

function PageHeader() {
  return (
    <div className="pv-header">
      <div className="pv-header-title">Plan Visualizer</div>
      <div className="pv-header-sub">Inspect SQL Server execution plans</div>
    </div>
  );
}

interface QueryInputPanelProps {
  query:               string;
  onQueryChange:       (q: string) => void;
  actualPlan:          boolean;
  onActualPlanChange:  (v: boolean) => void;
  onAnalyze:           () => void;
  loading:             boolean;
}

function QueryInputPanel({
  query,
  onQueryChange,
  actualPlan,
  onActualPlanChange,
  onAnalyze,
  loading,
}: QueryInputPanelProps) {
  return (
    <div className="pv-input-card">
      <div className="pv-editor-label">SQL Query</div>

      <div className="pv-editor-wrap">
        <Editor
          height="120px"
          defaultLanguage="sql"
          value={query}
          onChange={v => onQueryChange(v ?? '')}
          theme="light"
          options={{
            minimap:         { enabled: false },
            lineNumbers:     'off',
            scrollBeyondLastLine: false,
            fontFamily:      'JetBrains Mono, monospace',
            fontSize:        13,
            padding:         { top: 8, bottom: 8 },
            wordWrap:        'on',
            renderLineHighlight: 'none',
            overviewRulerLanes: 0,
          }}
        />
      </div>

      <div className="pv-input-row">
        <div className="pv-plan-type-group">
          <button
            className={`pv-plan-type-btn ${actualPlan ? 'active' : ''}`}
            onClick={() => onActualPlanChange(true)}
          >
            <span>●</span>
            Actual plan
          </button>
          <button
            className={`pv-plan-type-btn ${!actualPlan ? 'active' : ''}`}
            onClick={() => onActualPlanChange(false)}
          >
            <span>○</span>
            Estimated only
          </button>
        </div>

        <button
          className="pv-analyze-btn"
          onClick={onAnalyze}
          disabled={loading || !query.trim()}
        >
          {loading ? (
            <>
              <div className="pv-spinner" />
              Analyzing…
            </>
          ) : (
            <>
              ▶ Analyze Plan
            </>
          )}
        </button>
      </div>
    </div>
  );
}

function ErrorBanner({ message }: { message: string }) {
  return (
    <div className="pv-error">
      <span>⚠</span>
      <div>
        <strong>Plan analysis failed</strong>
        <div style={{ marginTop: '4px', fontFamily: 'JetBrains Mono, monospace', fontSize: '12px' }}>
          {message}
        </div>
      </div>
    </div>
  );
}

function EmptyState() {
  return (
    <div className="pv-empty">
      <div className="pv-empty-icon">🔍</div>
      <div className="pv-empty-title">No plan loaded</div>
      <div className="pv-empty-desc">
        Paste a SQL query above and click <strong>Analyze Plan</strong> to visualize its
        execution plan as an interactive operator tree.
      </div>
    </div>
  );
}

function WarningsPanel({ warnings }: { warnings: PlanWarning[] }) {
  const LABELS: Record<string, string> = {
    ImplicitConversion: 'Implicit type conversion',
    NoJoinPredicate:    'Missing JOIN predicate',
    TempDbSpill:        'TempDB spill',
  };

  return (
    <div className="pv-panel warning">
      <div className="pv-panel-title">
        ⚠ Warnings ({warnings.length})
      </div>
      {warnings.map((w, i) => (
        <div className="pv-panel-row" key={i}>
          <div className="pv-panel-row-label">{LABELS[w.type] ?? w.type}</div>
          <div className="pv-panel-row-detail">{w.detail}</div>
        </div>
      ))}
    </div>
  );
}

function buildIndexSuggestion(hint: MissingIndexHint): string {
  const equality: string[] = [];
  const includes: string[] = [];

  for (const col of hint.columns) {
    const eqMatch  = col.match(/EQUALITY\((.+)\)/);
    const incMatch = col.match(/INCLUDE\((.+)\)/);
    if (eqMatch)  equality.push(...eqMatch[1].split(',').map(s => s.trim()));
    if (incMatch) includes.push(...incMatch[1].split(',').map(s => s.trim()));
  }

  const keyPart = equality.join(', ') || '/* key columns */';
  const incPart = includes.length > 0 ? `\nINCLUDE (${includes.join(', ')})` : '';
  const idxName = `IX_table_${equality[0] ?? 'col'}`.replace(/[^a-zA-Z0-9_]/g, '_');

  return `CREATE NONCLUSTERED INDEX ${idxName}\n  ON [table] (${keyPart})${incPart};`;
}

function MissingIndexPanel({ hints }: { hints: MissingIndexHint[] }) {
  return (
    <div className="pv-panel missing">
      <div className="pv-panel-title">
        💡 Missing Index Hints ({hints.length})
      </div>
      {hints.map((hint, i) => (
        <div className="pv-panel-row" key={i}>
          <div className="pv-panel-row-label">
            Impact {hint.impact}%
          </div>
          <div className="pv-panel-row-detail">
            {hint.columns.join(' · ')}
          </div>
          <pre className="pv-code-block">{buildIndexSuggestion(hint)}</pre>
        </div>
      ))}
    </div>
  );
}

// ── Main page ──────────────────────────────────────────────────────────────────
export default function PlanVisualizer() {
  const [query,      setQuery]      = useState('');
  const [actualPlan, setActualPlan] = useState(true);
  const [plan,       setPlan]       = useState<StructuredPlan | null>(null);
  const [loading,    setLoading]    = useState(false);
  const [error,      setError]      = useState('');
  const [selectedOp, setSelectedOp] = useState<PlanOperator | null>(null);

  const treeRef = useRef<PlanTreeHandle>(null);

  async function handleAnalyze() {
    if (!query.trim()) return;
    setLoading(true);
    setError('');
    setPlan(null);
    setSelectedOp(null);
    try {
      const result = await planApi.fromQuery({ query: query.trim(), actual: actualPlan });
      setPlan(result);
    } catch (err: any) {
      setError(err?.message ?? 'Plan analysis failed.');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="pv-page">
      <PageHeader />

      <QueryInputPanel
        query={query}
        onQueryChange={setQuery}
        actualPlan={actualPlan}
        onActualPlanChange={setActualPlan}
        onAnalyze={handleAnalyze}
        loading={loading}
      />

      {error && <ErrorBanner message={error} />}

      {/* Main two-column layout: tree + sidebar */}
      {plan && (
        <div className="pv-main">
          <div className="pv-tree-container">
            <PlanControls
              onZoomIn={()    => treeRef.current?.zoomIn()}
              onZoomOut={()   => treeRef.current?.zoomOut()}
              onFitScreen={()  => treeRef.current?.fitScreen()}
            />
            <PlanTree
              ref={treeRef}
              plan={plan}
              selectedId={selectedOp?.id ?? null}
              onSelectOperator={setSelectedOp}
            />
          </div>

          <PlanSidebar
            operator={selectedOp}
            plan={plan}
            onDeselect={() => setSelectedOp(null)}
          />
        </div>
      )}

      {/* Warnings panel */}
      {plan && plan.warnings.length > 0 && (
        <WarningsPanel warnings={plan.warnings} />
      )}

      {/* Missing index hints panel */}
      {plan && plan.missing_indexes.length > 0 && (
        <MissingIndexPanel hints={plan.missing_indexes} />
      )}

      {/* Idle state */}
      {!plan && !loading && !error && <EmptyState />}
    </div>
  );
}
