import { useState, useCallback } from 'react';
import Editor from '@monaco-editor/react';
import type { JobResult, JobStatus } from '../../types';

interface Props {
  result:  JobResult | null;
  status:  JobStatus | null;
  error:   string | null;
}

type Tab = 'query' | 'indexes' | 'diagnosis';

function ImprovementBadge({ pct, speedup }: { pct: number; speedup: number }) {
  const isGood = pct > 0;
  return (
    <div className={`rp-improvement ${isGood ? 'good' : 'bad'}`}>
      <span className="rp-imp-pct">{isGood ? '+' : ''}{pct}%</span>
      <span className="rp-imp-sub">{speedup}x faster</span>
    </div>
  );
}

function StatRow({ label, before, after }: { label: string; before: string; after: string }) {
  return (
    <div className="rp-stat-row">
      <span className="rp-stat-label">{label}</span>
      <span className="rp-stat-before">{before}</span>
      <span className="rp-stat-arrow">→</span>
      <span className="rp-stat-after">{after}</span>
    </div>
  );
}

export function ResultPanel({ result, status, error }: Props) {
  const [tab,    setTab]    = useState<Tab>('query');
  const [copied, setCopied] = useState(false);

  const opt   = result?.optimization;
  const bench = result?.benchmark;
  const mig   = result?.migration ?? opt?.migration;

  const copyOptimized = useCallback(() => {
    const q = opt?.optimized_query;
    if (!q) return;
    navigator.clipboard.writeText(q).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  }, [opt]);

  // ── Empty state ───────────────────────────────────────────────────────────
  if (!status) {
    return (
      <div className="result-panel rp-empty-outer">
        <div className="rp-empty">
          <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.2">
            <path d="M9 3H5a2 2 0 00-2 2v4m6-6h10a2 2 0 012 2v4M9 3v18m0 0h10a2 2 0 002-2V9M9 21H5a2 2 0 01-2-2V9m0 0h18"/>
          </svg>
          <span>Results will appear here</span>
        </div>
      </div>
    );
  }

  if (status === 'running' || status === 'queued') {
    return (
      <div className="result-panel rp-empty-outer">
        <div className="rp-empty">
          <div className="rp-running-ring" />
          <span>Pipeline running…</span>
        </div>
      </div>
    );
  }

  if (status === 'failed' || error) {
    return (
      <div className="result-panel rp-empty-outer">
        <div className="rp-error-box">
          <div className="rp-error-icon">✗</div>
          <div className="rp-error-title">Pipeline failed</div>
          <div className="rp-error-msg">{error ?? 'Unknown error — check the output log'}</div>
        </div>
      </div>
    );
  }

  if (status === 'cancelled') {
    return (
      <div className="result-panel rp-empty-outer">
        <div className="rp-empty"><span>Cancelled</span></div>
      </div>
    );
  }

  // ── Results ───────────────────────────────────────────────────────────────
  return (
    <div className="result-panel">
      {/* Header: improvement badge */}
      <div className="rp-header">
        <span className="rp-header-title">Results</span>
        {bench && (
          <ImprovementBadge pct={bench.improvement_pct} speedup={bench.speedup} />
        )}
      </div>

      {/* Benchmark stats row */}
      {bench && (
        <div className="rp-bench-stats">
          <StatRow
            label="Avg"
            before={`${bench.before.avg_ms}ms`}
            after={`${bench.after.avg_ms}ms`}
          />
          <StatRow
            label="Rows"
            before={String(bench.before.row_count)}
            after={`${bench.after.row_count}${bench.row_mismatch ? ' ⚠' : ''}`}
          />
          {bench.row_mismatch && (
            <div className="rp-mismatch-warn">
              ⚠ Row count mismatch — verify before applying
            </div>
          )}
        </div>
      )}

      {/* Migration badge */}
      {mig && (
        <div className="rp-migration-badge">
          📋 Migration <strong>{String(mig.number).padStart(3, '0')}</strong> generated — {mig.filename}
        </div>
      )}

      {/* Tabs */}
      <div className="rp-tabs">
        {(['query', 'indexes', 'diagnosis'] as Tab[]).map((t) => {
          const count = t === 'indexes' ? opt?.index_scripts?.length ?? 0 : 0;
          if (t === 'diagnosis' && !opt?.diagnosis) return null;
          return (
            <button
              key={t}
              className={`rp-tab${tab === t ? ' active' : ''}`}
              onClick={() => setTab(t)}
            >
              {t === 'query'     ? 'Optimized SQL'
               : t === 'indexes' ? `Indexes ${count > 0 ? `(${count})` : ''}`
               :                   'Diagnosis'}
            </button>
          );
        })}
      </div>

      {/* Tab content */}
      <div className="rp-content">
        {tab === 'query' && opt?.optimized_query && (
          <div className="rp-editor-wrap">
            <Editor
              language="sql"
              value={opt.optimized_query}
              theme="light"
              options={{
                readOnly: true,
                minimap: { enabled: false },
                lineNumbers: 'on',
                scrollBeyondLastLine: false,
                wordWrap: 'on',
                fontSize: 12,
                fontFamily: 'JetBrains Mono, monospace',
                padding: { top: 10, bottom: 10 },
              }}
            />
          </div>
        )}
        {tab === 'query' && !opt?.optimized_query && (
          <div className="rp-no-content">No optimized query was produced</div>
        )}

        {tab === 'indexes' && (
          <div className="rp-index-list">
            {(opt?.index_scripts ?? []).length === 0 ? (
              <div className="rp-no-content">No CREATE INDEX scripts in this result</div>
            ) : (
              opt!.index_scripts.map((script: any, i: number) => (
                <div key={i} className="rp-index-item">
                  <div className="rp-index-header">
                    <span>Index {i + 1}</span>
                    <button
                      className="rp-copy-tiny"
                      onClick={() => navigator.clipboard.writeText(script)}
                    >
                      Copy
                    </button>
                  </div>
                  <pre className="rp-code">{script}</pre>
                </div>
              ))
            )}
          </div>
        )}

        {tab === 'diagnosis' && (
          <div className="rp-diagnosis">
            {opt?.diagnosis ?? 'No diagnosis recorded.'}
          </div>
        )}
      </div>

      {/* Action buttons */}
      <div className="rp-actions">
        <button className="rp-action-btn primary" onClick={copyOptimized}>
          {copied ? '✓ Copied!' : '⎘ Copy SQL'}
        </button>
        {mig && (
          <button
            className="rp-action-btn secondary"
            onClick={() => window.location.href = '/deploy'}
          >
            → Deploy
          </button>
        )}
      </div>

      <style>{`
        .result-panel {
          display: flex;
          flex-direction: column;
          height: 100%;
          padding: 14px;
          gap: 10px;
          overflow: hidden;
        }
        .rp-empty-outer {
          display: flex;
          align-items: center;
          justify-content: center;
        }
        .rp-empty {
          display: flex;
          flex-direction: column;
          align-items: center;
          gap: 10px;
          color: var(--text-muted);
          font-size: 12px;
        }
        .rp-running-ring {
          width: 32px; height: 32px;
          border: 3px solid var(--accent-light);
          border-top-color: var(--accent);
          border-radius: 50%;
          animation: spin 0.8s linear infinite;
        }
        @keyframes spin { to { transform: rotate(360deg); } }
        .rp-error-box {
          display: flex;
          flex-direction: column;
          align-items: center;
          gap: 8px;
          text-align: center;
          padding: 24px;
        }
        .rp-error-icon { font-size: 24px; color: var(--danger); }
        .rp-error-title { font-weight: 600; color: var(--text-primary); }
        .rp-error-msg { font-size: 12px; color: var(--text-secondary); max-width: 280px; }
        .rp-header {
          display: flex;
          align-items: center;
          justify-content: space-between;
          flex-shrink: 0;
        }
        .rp-header-title {
          font-size: 11px;
          font-weight: 700;
          color: var(--text-secondary);
          letter-spacing: 0.06em;
          text-transform: uppercase;
        }
        .rp-improvement {
          display: flex;
          flex-direction: column;
          align-items: flex-end;
          gap: 0;
        }
        .rp-improvement.good .rp-imp-pct { color: var(--success); font-size: 20px; font-weight: 800; line-height: 1; }
        .rp-improvement.bad  .rp-imp-pct { color: var(--danger);  font-size: 20px; font-weight: 800; line-height: 1; }
        .rp-imp-sub { font-size: 10px; color: var(--text-muted); }
        .rp-bench-stats {
          background: var(--bg-elevated);
          border-radius: 8px;
          padding: 10px 12px;
          display: flex;
          flex-direction: column;
          gap: 4px;
          flex-shrink: 0;
        }
        .rp-stat-row {
          display: flex;
          align-items: center;
          gap: 8px;
          font-size: 12px;
        }
        .rp-stat-label  { color: var(--text-muted); width: 32px; font-size: 11px; }
        .rp-stat-before { color: var(--danger);  font-family: 'JetBrains Mono', monospace; }
        .rp-stat-arrow  { color: var(--text-muted); font-size: 10px; }
        .rp-stat-after  { color: var(--success); font-family: 'JetBrains Mono', monospace; font-weight: 600; }
        .rp-mismatch-warn {
          font-size: 11px;
          color: var(--warning);
          background: var(--warning-light);
          padding: 4px 8px;
          border-radius: 5px;
          margin-top: 4px;
        }
        .rp-migration-badge {
          font-size: 11px;
          color: var(--accent);
          background: var(--accent-light);
          padding: 5px 10px;
          border-radius: 6px;
          flex-shrink: 0;
        }
        .rp-tabs {
          display: flex;
          gap: 2px;
          flex-shrink: 0;
        }
        .rp-tab {
          border: none;
          background: transparent;
          padding: 5px 12px;
          font-size: 11px;
          font-weight: 500;
          color: var(--text-muted);
          cursor: pointer;
          border-bottom: 2px solid transparent;
          transition: all 0.15s;
        }
        .rp-tab:hover { color: var(--text-primary); }
        .rp-tab.active { color: var(--accent); border-bottom-color: var(--accent); font-weight: 600; }
        .rp-content {
          flex: 1;
          min-height: 0;
          overflow: hidden;
        }
        .rp-editor-wrap { height: 100%; }
        .rp-no-content {
          display: flex;
          align-items: center;
          justify-content: center;
          height: 100%;
          font-size: 12px;
          color: var(--text-muted);
        }
        .rp-index-list {
          height: 100%;
          overflow-y: auto;
          display: flex;
          flex-direction: column;
          gap: 10px;
        }
        .rp-index-item {
          border: 1px solid var(--border);
          border-radius: 8px;
          overflow: hidden;
        }
        .rp-index-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          padding: 6px 10px;
          background: var(--bg-elevated);
          font-size: 11px;
          font-weight: 600;
          color: var(--text-secondary);
        }
        .rp-copy-tiny {
          background: none;
          border: 1px solid var(--border);
          border-radius: 4px;
          font-size: 10px;
          padding: 2px 7px;
          cursor: pointer;
          color: var(--text-muted);
        }
        .rp-copy-tiny:hover { background: var(--bg-surface); }
        .rp-code {
          font-family: 'JetBrains Mono', monospace;
          font-size: 11px;
          padding: 10px 12px;
          margin: 0;
          white-space: pre-wrap;
          word-break: break-all;
          color: var(--text-primary);
          background: var(--bg-surface);
        }
        .rp-diagnosis {
          height: 100%;
          overflow-y: auto;
          font-size: 12px;
          line-height: 1.7;
          color: var(--text-secondary);
          white-space: pre-wrap;
          padding: 4px 0;
        }
        .rp-actions {
          display: flex;
          gap: 8px;
          flex-shrink: 0;
        }
        .rp-action-btn {
          flex: 1;
          padding: 8px 14px;
          border-radius: 7px;
          font-size: 12px;
          font-weight: 600;
          cursor: pointer;
          border: none;
          transition: all 0.15s;
        }
        .rp-action-btn.primary {
          background: var(--accent);
          color: #fff;
        }
        .rp-action-btn.primary:hover { background: var(--accent-hover); }
        .rp-action-btn.secondary {
          background: var(--bg-elevated);
          color: var(--text-secondary);
          border: 1px solid var(--border);
        }
        .rp-action-btn.secondary:hover { background: var(--border); }
      `}</style>
    </div>
  );
}
