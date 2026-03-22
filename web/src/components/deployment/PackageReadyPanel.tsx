// web/src/components/deployment/PackageReadyPanel.tsx
import { useState } from 'react';
import { deployApi } from '../../api/deploy';
import type { DeployPackage } from '../../types';

interface Props {
  package: DeployPackage;
  onViewFile: (filename: string) => void;
}

const FILE_ICONS: Record<string, string> = {
  'deploy.sql':            '📄',
  'rollback.sql':          '↩️',
  'pre_flight.md':         '✅',
  'technical_report.md':   '📊',
  'walkthrough.md':        '📋',
  'session_log.txt':       '🗒️',
};

const FILE_DESCRIPTIONS: Record<string, string> = {
  'deploy.sql':            'Apply all changes to production',
  'rollback.sql':          'Undo all changes if needed',
  'pre_flight.md':         'Client sign-off checklist',
  'technical_report.md':   'Full DDL and diagnosis',
  'walkthrough.md':        'Plain-English step-by-step',
  'session_log.txt':       'Written during deployment',
};

const PREFERRED_ORDER = [
  'deploy.sql',
  'rollback.sql',
  'pre_flight.md',
  'walkthrough.md',
  'technical_report.md',
  'session_log.txt',
];

export default function PackageReadyPanel({ package: pkg, onViewFile }: Props) {
  const [previous,     setPrevious]    = useState<DeployPackage[]>([]);
  const [showPrevious, setShowPrevious] = useState(false);
  const [loadingPrev,  setLoadingPrev] = useState(false);

  function sortedFiles(files: string[]) {
    return [...files].sort((a, b) => {
      const ai = PREFERRED_ORDER.indexOf(a);
      const bi = PREFERRED_ORDER.indexOf(b);
      if (ai === -1 && bi === -1) return a.localeCompare(b);
      if (ai === -1) return 1;
      if (bi === -1) return -1;
      return ai - bi;
    });
  }

  async function loadPrevious() {
    if (previous.length > 0) { setShowPrevious(v => !v); return; }
    setLoadingPrev(true);
    try {
      const all = await deployApi.listPackages();
      // Exclude the current package
      setPrevious(all.filter(p => p.folder_name !== pkg.folder_name));
      setShowPrevious(true);
    } catch {
      // silently fail
    } finally {
      setLoadingPrev(false);
    }
  }

  return (
    <div className="prp-card card">
      {/* Success header */}
      <div className="prp-success-header">
        <div className="prp-success-icon">✓</div>
        <div>
          <div className="prp-success-title">Package Ready</div>
          <div className="prp-folder-name font-mono">{pkg.folder_name}/</div>
        </div>
        <div className="prp-meta">
          <span className="badge badge-success">{pkg.migrations?.length ?? 0} migration{(pkg.migrations?.length ?? 0) !== 1 ? 's' : ''}</span>
          <span className="prp-client">{pkg.client}</span>
        </div>
      </div>

      {/* File list */}
      <div className="prp-files">
        <div className="prp-section-label">Package files:</div>
        {sortedFiles(pkg.files).map(filename => (
          <div key={filename} className="prp-file-row">
            <span className="prp-file-icon">
              {FILE_ICONS[filename] ?? '📄'}
            </span>
            <div className="prp-file-info">
              <span className="prp-file-name font-mono">{filename}</span>
              {FILE_DESCRIPTIONS[filename] && (
                <span className="prp-file-desc">{FILE_DESCRIPTIONS[filename]}</span>
              )}
            </div>
            <button
              className="prp-view-btn"
              onClick={() => onViewFile(filename)}
            >
              View
            </button>
          </div>
        ))}
      </div>

      {/* Deploy instructions */}
      <div className="prp-instructions">
        <div className="prp-section-label">Next steps:</div>
        <ol className="prp-steps">
          <li>Open <code>pre_flight.md</code> — confirm checklist with client before starting</li>
          <li>Open <code>deploy.sql</code> in SSMS and press <kbd>F5</kbd> to apply all changes</li>
          <li>Verify the application works as expected</li>
          <li>If anything looks wrong — open <code>rollback.sql</code> and press <kbd>F5</kbd></li>
          <li>Run <code>python agent.py mark-applied &lt;number&gt;</code> to confirm each migration</li>
        </ol>
      </div>

      {/* Previous packages collapsible */}
      <div className="prp-prev-section">
        <button className="prp-prev-toggle" onClick={loadPrevious}>
          {loadingPrev ? 'Loading…' : showPrevious ? '▾ Previous packages' : '▸ Previous packages'}
        </button>
        {showPrevious && previous.length > 0 && (
          <div className="prp-prev-list">
            {previous.map(p => (
              <div key={p.folder_name} className="prp-prev-row">
                <span className="prp-prev-name font-mono">{p.folder_name}/</span>
                <span className="prp-prev-date">{p.created_at?.slice(0, 16)}</span>
                <span className="prp-prev-client">{p.client}</span>
                <span className="prp-prev-files">{p.files?.length ?? 0} files</span>
              </div>
            ))}
          </div>
        )}
        {showPrevious && previous.length === 0 && !loadingPrev && (
          <div className="prp-prev-empty">No previous packages found.</div>
        )}
      </div>
    </div>
  );
}

// ── Styles ────────────────────────────────────────────────────
const _styles = `
.prp-card { margin-bottom: 20px; }

.prp-success-header {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 18px 20px;
  background: var(--success-light);
  border-bottom: 1px solid var(--border);
  border-radius: 10px 10px 0 0;
}

.prp-success-icon {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  background: var(--success);
  color: white;
  font-size: 18px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.prp-success-title {
  font-size: 15px;
  font-weight: 600;
  color: var(--success);
  margin-bottom: 2px;
}

.prp-folder-name {
  font-size: 12px;
  color: var(--text-secondary);
}

.prp-meta {
  margin-left: auto;
  display: flex;
  align-items: center;
  gap: 8px;
}

.prp-client {
  font-size: 12px;
  color: var(--text-muted);
}

.prp-section-label {
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--text-muted);
  margin-bottom: 10px;
}

.prp-files {
  padding: 16px 20px;
  border-bottom: 1px solid var(--border);
}

.prp-file-row {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 0;
  border-bottom: 1px solid var(--border);
}

.prp-file-row:last-child { border-bottom: none; }

.prp-file-icon {
  font-size: 16px;
  flex-shrink: 0;
  width: 22px;
  text-align: center;
}

.prp-file-info {
  flex: 1;
  display: flex;
  align-items: center;
  gap: 10px;
}

.prp-file-name {
  font-size: 13px;
  color: var(--text-primary);
}

.prp-file-desc {
  font-size: 12px;
  color: var(--text-muted);
}

.prp-view-btn {
  padding: 4px 12px;
  font-size: 12px;
  background: var(--accent-light);
  color: var(--accent);
  border: 1px solid var(--accent);
  border-radius: 5px;
  cursor: pointer;
  font-weight: 500;
  white-space: nowrap;
}
.prp-view-btn:hover { background: var(--accent); color: white; }

.prp-instructions {
  padding: 16px 20px;
  border-bottom: 1px solid var(--border);
}

.prp-steps {
  margin: 0;
  padding-left: 20px;
  font-size: 13px;
  color: var(--text-secondary);
  line-height: 1.8;
}

.prp-steps code {
  font-family: 'JetBrains Mono', monospace;
  font-size: 11px;
  background: var(--bg-elevated);
  padding: 1px 5px;
  border-radius: 3px;
  color: var(--text-primary);
  border: 1px solid var(--border);
}

.prp-steps kbd {
  font-family: 'JetBrains Mono', monospace;
  font-size: 11px;
  background: var(--bg-elevated);
  padding: 1px 5px;
  border-radius: 3px;
  border: 1px solid var(--border-strong);
  color: var(--text-primary);
}

.prp-prev-section {
  padding: 12px 20px;
}

.prp-prev-toggle {
  background: none;
  border: none;
  font-size: 12px;
  color: var(--text-muted);
  cursor: pointer;
  padding: 0;
}
.prp-prev-toggle:hover { color: var(--text-secondary); }

.prp-prev-list {
  margin-top: 8px;
  border: 1px solid var(--border);
  border-radius: 6px;
  overflow: hidden;
}

.prp-prev-row {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 8px 12px;
  border-bottom: 1px solid var(--border);
  font-size: 12px;
}
.prp-prev-row:last-child { border-bottom: none; }

.prp-prev-name {
  flex: 1;
  color: var(--text-primary);
  font-size: 11px;
}

.prp-prev-date, .prp-prev-client, .prp-prev-files {
  color: var(--text-muted);
  white-space: nowrap;
}

.prp-prev-empty {
  margin-top: 8px;
  font-size: 12px;
  color: var(--text-muted);
}
`;

if (typeof document !== 'undefined') {
  const id = 'prp-styles';
  if (!document.getElementById(id)) {
    const el = document.createElement('style');
    el.id = id;
    el.textContent = _styles;
    document.head.appendChild(el);
  }
}
