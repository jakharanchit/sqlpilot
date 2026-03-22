// web/src/pages/DeploymentGate.tsx
import { useState } from 'react';
import Editor from '@monaco-editor/react';
import PendingMigrationsPanel from '../components/deployment/PendingMigrationsPanel';
import SandboxRunner          from '../components/deployment/SandboxRunner';
import DeployPreview          from '../components/deployment/DeployPreview';
import ConfirmDeployModal     from '../components/deployment/ConfirmDeployModal';
import PackageReadyPanel      from '../components/deployment/PackageReadyPanel';
import { deployApi }          from '../api/deploy';
import type { DeployPackage, Migration } from '../types';

// ── File viewer modal ─────────────────────────────────────────
function FileViewerModal({
  filename,
  content,
  onClose,
}: {
  filename: string;
  content:  string;
  onClose:  () => void;
}) {
  const isSql = filename.endsWith('.sql');
  const lang  = isSql ? 'sql' : filename.endsWith('.md') ? 'markdown' : 'plaintext';

  return (
    <div className="fvm-overlay" onClick={(e) => e.target === e.currentTarget && onClose()}>
      <div className="fvm-dialog card">
        <div className="fvm-header">
          <span className="fvm-filename font-mono">{filename}</span>
          <button className="fvm-close" onClick={onClose}>✕</button>
        </div>
        <div className="fvm-body">
          <Editor
            height="520px"
            language={lang}
            value={content}
            options={{
              readOnly:             true,
              minimap:              { enabled: false },
              scrollBeyondLastLine: false,
              fontSize:             12,
              lineNumbers:          'on',
              wordWrap:             'on',
              theme:                'vs',
            }}
          />
        </div>
      </div>
    </div>
  );
}

// ── Generate button ───────────────────────────────────────────
function GenerateButton({
  sandboxPassed,
  sandboxRan,
  onClick,
}: {
  sandboxPassed: boolean;
  sandboxRan:    boolean;
  onClick:       () => void;
}) {
  const isDisabled = sandboxRan && !sandboxPassed;

  return (
    <div className="dg-generate-wrap">
      <button
        className={`dg-generate-btn ${sandboxPassed ? 'dg-generate-passed' : ''}`}
        disabled={isDisabled}
        onClick={onClick}
      >
        {sandboxPassed
          ? '📦 Generate Deployment Package ✓'
          : '📦 Generate Deployment Package'}
      </button>
      {!sandboxRan && (
        <span className="dg-generate-note">Sandbox not tested — you can still generate</span>
      )}
      {sandboxRan && !sandboxPassed && (
        <span className="dg-generate-note dg-note-danger">Fix sandbox failures first</span>
      )}
      {sandboxPassed && (
        <span className="dg-generate-note dg-note-success">Sandbox passed ✓</span>
      )}
    </div>
  );
}

// ── Main page ─────────────────────────────────────────────────
export default function DeploymentGate() {
  const [sandboxPassed, setSandboxPassed] = useState(false);
  const [sandboxRan,    setSandboxRan]    = useState(false);
  const [showModal,     setShowModal]     = useState(false);
  const [generating,    setGenerating]    = useState(false);
  const [package_,      setPackage]       = useState<DeployPackage | null>(null);
  const [genError,      setGenError]      = useState<string | null>(null);
  const [viewingFile,   setViewingFile]   = useState<{ name: string; content: string } | null>(null);

  function handleSandboxPassed() {
    setSandboxPassed(true);
    setSandboxRan(true);
  }

  function handleSandboxFailed() {
    setSandboxPassed(false);
    setSandboxRan(true);
  }

  async function handleGenerate() {
    setGenerating(true);
    setGenError(null);
    try {
      const pkg = await deployApi.generate();
      setPackage(pkg);
      setShowModal(false);
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : String(e);
      setGenError(msg);
    } finally {
      setGenerating(false);
    }
  }

  async function handleViewFile(folderName: string, filename: string) {
    try {
      const content = await deployApi.getFile(folderName, filename);
      setViewingFile({ name: filename, content });
    } catch (e) {
      alert(`Could not load file: ${e}`);
    }
  }

  return (
    <div className="dg-page">
      {/* Page header */}
      <div className="dg-page-header">
        <div className="dg-page-header-left">
          <h1 className="dg-page-title">Deployment Gate</h1>
          <p className="dg-page-subtitle">
            Review pending migrations, run sandbox testing, and generate a client deployment package.
          </p>
        </div>
      </div>

      <div className="dg-content">
        {/* Step 1 — Pending migrations */}
        <div className="dg-step">
          <div className="dg-step-badge">1</div>
          <div className="dg-step-body">
            <PendingMigrationsPanel />
          </div>
        </div>

        {/* Step 2 — Sandbox test */}
        <div className="dg-step">
          <div className="dg-step-badge">2</div>
          <div className="dg-step-body">
            <SandboxRunner
              onPassed={() => handleSandboxPassed()}
              onFailed={() => handleSandboxFailed()}
            />
          </div>
        </div>

        {/* Step 3 — SQL preview */}
        <div className="dg-step">
          <div className="dg-step-badge">3</div>
          <div className="dg-step-body">
            <DeployPreview />
          </div>
        </div>

        {/* Step 4 — Generate */}
        <div className="dg-step dg-step-last">
          <div className="dg-step-badge">4</div>
          <div className="dg-step-body">
            <GenerateButton
              sandboxPassed={sandboxPassed}
              sandboxRan={sandboxRan}
              onClick={() => setShowModal(true)}
            />
            {genError && (
              <div className="dg-gen-error">⚠ {genError}</div>
            )}
          </div>
        </div>

        {/* Package ready */}
        {package_ && (
          <div className="dg-step dg-step-last">
            <div className="dg-step-badge dg-step-badge-success">✓</div>
            <div className="dg-step-body">
              <PackageReadyPanel
                package={package_}
                onViewFile={(fn) => handleViewFile(package_.folder_name, fn)}
              />
            </div>
          </div>
        )}
      </div>

      {/* Confirm modal */}
      <ConfirmDeployModal
        isOpen={showModal}
        onCancel={() => setShowModal(false)}
        onConfirm={handleGenerate}
        loading={generating}
        migrations={(package_?.migrations ?? []) as Migration[]}
      />

      {/* File viewer modal */}
      {viewingFile && (
        <FileViewerModal
          filename={viewingFile.name}
          content={viewingFile.content}
          onClose={() => setViewingFile(null)}
        />
      )}
    </div>
  );
}

// ── Styles ────────────────────────────────────────────────────
const _styles = `
.dg-page {
  padding: 0;
  min-height: 100%;
}

.dg-page-header {
  padding: 28px 32px 20px;
  border-bottom: 1px solid var(--border);
  background: var(--bg-surface);
}

.dg-page-title {
  font-size: 22px;
  font-weight: 700;
  color: var(--text-primary);
  margin: 0 0 6px;
}

.dg-page-subtitle {
  font-size: 13px;
  color: var(--text-muted);
  margin: 0;
}

.dg-content {
  padding: 28px 32px;
  display: flex;
  flex-direction: column;
  gap: 0;
  max-width: 920px;
}

.dg-step {
  display: flex;
  gap: 18px;
  padding-bottom: 0;
  position: relative;
}

.dg-step:not(.dg-step-last)::before {
  content: '';
  position: absolute;
  left: 15px;
  top: 40px;
  bottom: -10px;
  width: 2px;
  background: var(--border);
}

.dg-step-badge {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: var(--accent);
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 13px;
  font-weight: 600;
  flex-shrink: 0;
  margin-top: 14px;
  z-index: 1;
}

.dg-step-badge-success {
  background: var(--success);
}

.dg-step-body {
  flex: 1;
  padding-bottom: 24px;
  min-width: 0;
}

.dg-step-last .dg-step-body {
  padding-bottom: 0;
}

.dg-generate-wrap {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 20px;
  background: var(--bg-surface);
  border: 1px solid var(--border);
  border-radius: 10px;
}

.dg-generate-btn {
  padding: 11px 24px;
  font-size: 14px;
  font-weight: 600;
  border-radius: 8px;
  border: none;
  background: var(--accent);
  color: white;
  cursor: pointer;
  transition: background 0.15s;
  white-space: nowrap;
}
.dg-generate-btn:hover:not(:disabled) { background: var(--accent-hover); }
.dg-generate-btn:disabled { opacity: 0.5; cursor: default; }
.dg-generate-passed { background: var(--success); }
.dg-generate-passed:hover:not(:disabled) { background: #15803d; }

.dg-generate-note {
  font-size: 12px;
  color: var(--text-muted);
}

.dg-note-danger { color: var(--danger); }
.dg-note-success { color: var(--success); }

.dg-gen-error {
  margin-top: 10px;
  padding: 10px 14px;
  background: var(--danger-light);
  border: 1px solid var(--danger);
  border-radius: 6px;
  font-size: 12px;
  color: var(--danger);
}

/* File viewer modal */
.fvm-overlay {
  position: fixed;
  inset: 0;
  background: rgba(15, 23, 42, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 9998;
  backdrop-filter: blur(2px);
}

.fvm-dialog {
  width: min(780px, calc(100vw - 32px));
  height: min(640px, calc(100vh - 60px));
  display: flex;
  flex-direction: column;
  box-shadow: 0 20px 60px rgba(0,0,0,0.2);
}

.fvm-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 18px;
  border-bottom: 1px solid var(--border);
  background: var(--bg-elevated);
  border-radius: 10px 10px 0 0;
}

.fvm-filename {
  font-size: 13px;
  color: var(--text-primary);
}

.fvm-close {
  background: none;
  border: none;
  font-size: 14px;
  color: var(--text-muted);
  cursor: pointer;
  padding: 4px 6px;
  border-radius: 5px;
}
.fvm-close:hover { background: var(--border); color: var(--text-primary); }

.fvm-body {
  flex: 1;
  overflow: hidden;
  border-radius: 0 0 10px 10px;
}
`;

if (typeof document !== 'undefined') {
  const id = 'dg-styles';
  if (!document.getElementById(id)) {
    const el = document.createElement('style');
    el.id = id;
    el.textContent = _styles;
    document.head.appendChild(el);
  }
}
