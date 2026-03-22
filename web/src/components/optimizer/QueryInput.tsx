import React, { useState, useCallback } from 'react';
import Editor from '@monaco-editor/react';

const PLACEHOLDER = `-- Paste or type your SQL query here
-- Example:
SELECT *
FROM vw_dashboard
WHERE machine_id = 1
  AND sensor_date >= '2026-01-01'`;

type RunMode = 'full_run' | 'analyze' | 'benchmark';

interface Props {
  onFullRun:   (query: string, label: string, benchmarkRuns: number | null, safe: boolean, noDeploy: boolean) => void;
  onAnalyze:   (query: string, label: string) => void;
  onBenchmark: (before: string, after: string, label: string, runs: number | null) => void;
  isRunning:   boolean;
  onCancel:    () => void;
}

export function QueryInput({ onFullRun, onAnalyze, onBenchmark, isRunning, onCancel }: Props) {
  const [query,         setQuery]         = useState('');
  const [beforeQuery,   setBeforeQuery]   = useState('');
  const [label,         setLabel]         = useState('');
  const [benchmarkRuns, setBenchmarkRuns] = useState<string>('');
  const [safe,          setSafe]          = useState(false);
  const [noDeploy,      setNoDeploy]      = useState(false);
  const [mode,          setMode]          = useState<RunMode>('full_run');

  const handleSubmit = useCallback(() => {
    if (isRunning) return;
    const runs = benchmarkRuns ? parseInt(benchmarkRuns, 10) || null : null;

    if (mode === 'full_run') {
      if (!query.trim()) return;
      onFullRun(query.trim(), label, runs, safe, noDeploy);
    } else if (mode === 'analyze') {
      if (!query.trim()) return;
      onAnalyze(query.trim(), label);
    } else {
      if (!query.trim() || !beforeQuery.trim()) return;
      // benchmark: query = after, beforeQuery = before
      onBenchmark(beforeQuery.trim(), query.trim(), label, runs);
    }
  }, [mode, query, beforeQuery, label, benchmarkRuns, safe, noDeploy, isRunning,
      onFullRun, onAnalyze, onBenchmark]);

  const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
    if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
      e.preventDefault();
      handleSubmit();
    }
  }, [handleSubmit]);

  return (
    <div className="query-input-panel" onKeyDown={handleKeyDown}>
      {/* Mode tabs */}
      <div className="qi-tabs">
        {(['full_run', 'analyze', 'benchmark'] as RunMode[]).map((m) => (
          <button
            key={m}
            className={`qi-tab${mode === m ? ' active' : ''}`}
            onClick={() => setMode(m)}
            disabled={isRunning}
          >
            {m === 'full_run' ? '⚡ Full Pipeline' : m === 'analyze' ? '🔍 Analyze' : '⏱ Benchmark'}
          </button>
        ))}
      </div>

      {/* Before query (benchmark only) */}
      {mode === 'benchmark' && (
        <>
          <label className="qi-label">Before (original query)</label>
          <div className="qi-editor-wrap qi-editor-sm">
            <Editor
              language="sql"
              value={beforeQuery}
              onChange={(v) => setBeforeQuery(v ?? '')}
              theme="light"
              options={{
                minimap: { enabled: false },
                lineNumbers: 'off',
                scrollBeyondLastLine: false,
                wordWrap: 'on',
                fontSize: 12,
                fontFamily: 'JetBrains Mono, monospace',
                padding: { top: 8, bottom: 8 },
                scrollbar: { alwaysConsumeMouseWheel: false },
              }}
            />
          </div>
          <label className="qi-label" style={{ marginTop: 8 }}>After (optimized query)</label>
        </>
      )}

      {/* Main query editor */}
      {mode !== 'benchmark' && <label className="qi-label">SQL Query</label>}
      <div className="qi-editor-wrap">
        <Editor
          language="sql"
          value={query}
          onChange={(v) => setQuery(v ?? '')}
          theme="light"
          options={{
            minimap: { enabled: false },
            lineNumbers: 'on',
            scrollBeyondLastLine: false,
            wordWrap: 'on',
            fontSize: 13,
            fontFamily: 'JetBrains Mono, monospace',
            padding: { top: 10, bottom: 10 },
            scrollbar: { alwaysConsumeMouseWheel: false },
            placeholder: PLACEHOLDER,
          }}
        />
      </div>

      {/* Options row */}
      <div className="qi-options">
        <div className="qi-option-group">
          <label className="qi-label">Label <span className="qi-hint">(optional)</span></label>
          <input
            className="qi-input"
            type="text"
            placeholder="e.g. dashboard filter"
            value={label}
            onChange={(e) => setLabel(e.target.value)}
            disabled={isRunning}
          />
        </div>

        {(mode === 'full_run' || mode === 'benchmark') && (
          <div className="qi-option-group qi-option-narrow">
            <label className="qi-label">Runs</label>
            <input
              className="qi-input"
              type="number"
              min={1}
              max={50}
              placeholder="10"
              value={benchmarkRuns}
              onChange={(e) => setBenchmarkRuns(e.target.value)}
              disabled={isRunning}
            />
          </div>
        )}

        {mode === 'full_run' && (
          <div className="qi-toggles">
            <label className="qi-toggle">
              <input
                type="checkbox"
                checked={safe}
                onChange={(e) => setSafe(e.target.checked)}
                disabled={isRunning}
              />
              <span>Sandbox test</span>
            </label>
            <label className="qi-toggle">
              <input
                type="checkbox"
                checked={noDeploy}
                onChange={(e) => setNoDeploy(e.target.checked)}
                disabled={isRunning}
              />
              <span>Skip deploy</span>
            </label>
          </div>
        )}
      </div>

      {/* Submit / Cancel */}
      <div className="qi-actions">
        {isRunning ? (
          <button className="qi-btn qi-btn-cancel" onClick={onCancel}>
            <span className="qi-spinner" />
            Cancel
          </button>
        ) : (
          <button
            className="qi-btn qi-btn-primary"
            onClick={handleSubmit}
            disabled={!query.trim() || (mode === 'benchmark' && !beforeQuery.trim())}
          >
            {mode === 'full_run'   ? '⚡ Run Full Pipeline'
            : mode === 'analyze'  ? '🔍 Analyze Query'
            :                       '⏱ Run Benchmark'}
            <span className="qi-shortcut">Ctrl+↵</span>
          </button>
        )}
      </div>

      <style>{`
        .query-input-panel {
          display: flex;
          flex-direction: column;
          height: 100%;
          padding: 16px;
          gap: 10px;
          overflow: hidden;
        }
        .qi-tabs {
          display: flex;
          gap: 4px;
          background: var(--bg-elevated);
          border-radius: 8px;
          padding: 3px;
          flex-shrink: 0;
        }
        .qi-tab {
          flex: 1;
          border: none;
          background: transparent;
          padding: 6px 8px;
          border-radius: 6px;
          font-size: 11px;
          font-weight: 500;
          color: var(--text-secondary);
          cursor: pointer;
          transition: all 0.15s;
          white-space: nowrap;
        }
        .qi-tab:hover:not(:disabled) { background: var(--bg-surface); }
        .qi-tab.active {
          background: var(--bg-surface);
          color: var(--accent);
          box-shadow: 0 1px 3px rgba(0,0,0,0.08);
        }
        .qi-tab:disabled { opacity: 0.5; cursor: not-allowed; }
        .qi-label {
          font-size: 11px;
          font-weight: 600;
          color: var(--text-secondary);
          letter-spacing: 0.04em;
          text-transform: uppercase;
          flex-shrink: 0;
        }
        .qi-hint { font-weight: 400; text-transform: none; opacity: 0.7; }
        .qi-editor-wrap {
          flex: 1;
          min-height: 0;
          border: 1px solid var(--border);
          border-radius: 8px;
          overflow: hidden;
        }
        .qi-editor-sm { flex: 0 0 120px; }
        .qi-options {
          display: flex;
          gap: 10px;
          align-items: flex-end;
          flex-shrink: 0;
          flex-wrap: wrap;
        }
        .qi-option-group { display: flex; flex-direction: column; gap: 4px; flex: 1; min-width: 120px; }
        .qi-option-narrow { flex: 0 0 64px; min-width: 64px; }
        .qi-input {
          height: 32px;
          padding: 0 10px;
          border: 1px solid var(--border);
          border-radius: 6px;
          font-size: 13px;
          background: var(--bg-surface);
          color: var(--text-primary);
          outline: none;
          transition: border-color 0.15s;
        }
        .qi-input:focus { border-color: var(--accent); }
        .qi-toggles {
          display: flex;
          gap: 12px;
          align-items: center;
          padding-bottom: 4px;
        }
        .qi-toggle {
          display: flex;
          align-items: center;
          gap: 5px;
          font-size: 12px;
          color: var(--text-secondary);
          cursor: pointer;
          user-select: none;
        }
        .qi-toggle input { cursor: pointer; accent-color: var(--accent); }
        .qi-actions { flex-shrink: 0; }
        .qi-btn {
          display: inline-flex;
          align-items: center;
          gap: 8px;
          width: 100%;
          justify-content: center;
          padding: 10px 16px;
          border: none;
          border-radius: 8px;
          font-size: 13px;
          font-weight: 600;
          cursor: pointer;
          transition: all 0.15s;
        }
        .qi-btn-primary {
          background: var(--accent);
          color: #fff;
        }
        .qi-btn-primary:hover:not(:disabled) { background: var(--accent-hover); }
        .qi-btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }
        .qi-btn-cancel {
          background: var(--danger-light);
          color: var(--danger);
        }
        .qi-btn-cancel:hover { background: #fecaca; }
        .qi-shortcut {
          font-size: 10px;
          font-weight: 400;
          opacity: 0.65;
          background: rgba(255,255,255,0.25);
          padding: 1px 5px;
          border-radius: 4px;
        }
        .qi-spinner {
          width: 12px; height: 12px;
          border: 2px solid var(--danger);
          border-top-color: transparent;
          border-radius: 50%;
          animation: spin 0.7s linear infinite;
        }
        @keyframes spin { to { transform: rotate(360deg); } }
      `}</style>
    </div>
  );
}
