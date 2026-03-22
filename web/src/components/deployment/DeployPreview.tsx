// web/src/components/deployment/DeployPreview.tsx
import { useEffect, useState } from 'react';
import Editor from '@monaco-editor/react';
import { deployApi } from '../../api/deploy';
import type { DeployPreview as DeployPreviewType } from '../../types';

type Tab = 'deploy' | 'rollback';

export default function DeployPreview() {
  const [data,     setData]    = useState<DeployPreviewType | null>(null);
  const [loading,  setLoading] = useState(true);
  const [error,    setError]   = useState<string | null>(null);
  const [tab,      setTab]     = useState<Tab>('deploy');

  useEffect(() => {
    deployApi.preview()
      .then(d => setData(d))
      .catch(e => setError(String(e)))
      .finally(() => setLoading(false));
  }, []);

  const activeContent = tab === 'deploy'
    ? (data?.deploy_sql ?? '')
    : (data?.rollback_sql ?? '');

  const lineCount = activeContent.split('\n').length;

  return (
    <div className="dp-card card">
      {/* Header */}
      <div className="dp-header">
        <div className="dp-title">
          <span>📄</span>
          <h3>Deploy Preview</h3>
          {data && data.migration_count > 0 && (
            <span className="badge badge-info">{data.migration_count} migration{data.migration_count !== 1 ? 's' : ''}</span>
          )}
          {data?.has_schema_changes && (
            <span className="badge badge-warning">schema changes</span>
          )}
        </div>
        <p className="dp-subtitle">
          Review the exact SQL that will be applied before generating the package.
        </p>
      </div>

      {/* Tabs */}
      <div className="dp-tabs">
        <button
          className={`dp-tab ${tab === 'deploy' ? 'dp-tab-active' : ''}`}
          onClick={() => setTab('deploy')}
        >
          deploy.sql
        </button>
        <button
          className={`dp-tab ${tab === 'rollback' ? 'dp-tab-active' : ''}`}
          onClick={() => setTab('rollback')}
        >
          rollback.sql
        </button>

        {data && (
          <span className="dp-meta font-mono">
            {data.client} · {lineCount} lines
          </span>
        )}
      </div>

      {/* Editor area */}
      <div className="dp-editor-wrap">
        {loading && (
          <div className="dp-loading">
            <div className="spinner-sm" />
            <span>Loading preview…</span>
          </div>
        )}

        {error && (
          <div className="dp-error">⚠ {error}</div>
        )}

        {!loading && !error && data && (
          <Editor
            height="360px"
            language="sql"
            value={activeContent}
            options={{
              readOnly:             true,
              minimap:              { enabled: false },
              scrollBeyondLastLine: false,
              fontSize:             12,
              lineNumbers:          'on',
              wordWrap:             'on',
              theme:                'vs',
              renderLineHighlight:  'none',
              scrollbar:            { verticalScrollbarSize: 6 },
            }}
          />
        )}
      </div>
    </div>
  );
}

// ── Styles ────────────────────────────────────────────────────
const _styles = `
.dp-card { margin-bottom: 20px; }

.dp-header {
  padding: 18px 20px 12px;
  border-bottom: 1px solid var(--border);
}

.dp-title {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 4px;
}

.dp-title h3 {
  font-size: 15px;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0;
  flex: 1;
}

.dp-subtitle {
  font-size: 12px;
  color: var(--text-muted);
  margin: 0;
}

.dp-tabs {
  display: flex;
  align-items: center;
  gap: 0;
  padding: 0 20px;
  border-bottom: 1px solid var(--border);
  background: var(--bg-elevated);
}

.dp-tab {
  padding: 9px 16px;
  font-size: 13px;
  font-weight: 500;
  color: var(--text-secondary);
  background: transparent;
  border: none;
  border-bottom: 2px solid transparent;
  cursor: pointer;
  margin-bottom: -1px;
  font-family: 'JetBrains Mono', monospace;
  transition: color 0.15s, border-color 0.15s;
}

.dp-tab:hover { color: var(--text-primary); }

.dp-tab-active {
  color: var(--accent);
  border-bottom-color: var(--accent);
}

.dp-meta {
  margin-left: auto;
  font-size: 11px;
  color: var(--text-muted);
  padding: 0 4px;
}

.dp-editor-wrap {
  position: relative;
  min-height: 100px;
}

.dp-loading {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 24px 20px;
  color: var(--text-muted);
  font-size: 13px;
}

.dp-error {
  padding: 16px 20px;
  color: var(--danger);
  font-size: 13px;
  background: var(--danger-light);
}
`;

if (typeof document !== 'undefined') {
  const id = 'dp-styles';
  if (!document.getElementById(id)) {
    const el = document.createElement('style');
    el.id = id;
    el.textContent = _styles;
    document.head.appendChild(el);
  }
}
