import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { settingsApi } from '../api/settings';
import type {
  AllSettings,
  DbConfig,
  SandboxConfig,
  AgentConfig,
  ConnectivityResult,
} from '../types';
import type { SaveDbRequest, SaveOllamaRequest, SaveAgentRequest, SaveSandboxRequest } from '../api/settings';

// ── Styles ────────────────────────────────────────────────────────────────────

const _styles = `
.st-page {
  padding: 28px 32px;
  max-width: 780px;
}

.st-page-header {
  margin-bottom: 28px;
}

.st-page-title {
  font-size: 22px;
  font-weight: 700;
  color: var(--text-primary);
  margin: 0 0 4px;
}

.st-page-subtitle {
  font-size: 14px;
  color: var(--text-secondary);
  margin: 0 0 10px;
}

.st-config-chip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  background: var(--bg-elevated);
  border: 0.5px solid var(--border);
  border-radius: 6px;
  padding: 4px 10px;
  font-size: 12px;
  font-family: 'JetBrains Mono', monospace;
  color: var(--text-secondary);
}

.st-config-chip-label {
  color: var(--text-muted);
  font-family: inherit;
}

/* ── Cards ─────────────────────────── */
.st-card {
  background: var(--bg-surface);
  border: 0.5px solid var(--border);
  border-radius: 10px;
  margin-bottom: 20px;
  overflow: hidden;
}

.st-card-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 14px 20px;
  border-bottom: 0.5px solid var(--border);
  background: var(--bg-elevated);
}

.st-card-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-primary);
  flex: 1;
  letter-spacing: 0.02em;
}

.st-card-icon {
  font-size: 16px;
  line-height: 1;
}

.st-card-body {
  padding: 20px;
}

.st-card-footer {
  padding: 14px 20px;
  border-top: 0.5px solid var(--border);
  display: flex;
  justify-content: flex-end;
}

/* ── Form fields ───────────────────── */
.st-field {
  display: grid;
  grid-template-columns: 160px 1fr;
  align-items: center;
  gap: 12px;
  margin-bottom: 14px;
}

.st-field:last-child {
  margin-bottom: 0;
}

.st-label {
  font-size: 13px;
  color: var(--text-secondary);
  font-weight: 500;
}

.st-hint {
  font-size: 11px;
  color: var(--text-muted);
  margin-top: 2px;
}

.st-input {
  width: 100%;
  padding: 7px 10px;
  border: 0.5px solid var(--border-strong);
  border-radius: 6px;
  font-size: 13px;
  color: var(--text-primary);
  background: var(--bg-surface);
  outline: none;
  transition: border-color 0.15s;
  box-sizing: border-box;
  font-family: 'DM Sans', sans-serif;
}

.st-input:focus {
  border-color: var(--accent);
  box-shadow: 0 0 0 3px rgba(37,99,235,0.08);
}

.st-input-mono {
  font-family: 'JetBrains Mono', monospace;
  font-size: 12px;
}

.st-input-number {
  width: 100px;
}

/* ── Radio auth ────────────────────── */
.st-radio-group {
  display: flex;
  gap: 16px;
}

.st-radio-option {
  display: flex;
  align-items: center;
  gap: 6px;
  cursor: pointer;
  font-size: 13px;
  color: var(--text-primary);
}

.st-radio-option input[type="radio"] {
  accent-color: var(--accent);
  width: 15px;
  height: 15px;
  cursor: pointer;
}

/* ── Toggle (On/Off) ───────────────── */
.st-toggle-group {
  display: flex;
  gap: 16px;
}

.st-toggle-option {
  display: flex;
  align-items: center;
  gap: 6px;
  cursor: pointer;
  font-size: 13px;
  color: var(--text-primary);
}

.st-toggle-option input[type="radio"] {
  accent-color: var(--accent);
  width: 15px;
  height: 15px;
  cursor: pointer;
}

/* ── Buttons ───────────────────────── */
.st-save-btn {
  background: var(--accent);
  color: #fff;
  border: none;
  border-radius: 6px;
  padding: 8px 18px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.15s;
  font-family: 'DM Sans', sans-serif;
}

.st-save-btn:hover:not(:disabled) {
  background: var(--accent-hover);
}

.st-save-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.st-test-btn {
  background: var(--bg-surface);
  color: var(--text-secondary);
  border: 0.5px solid var(--border-strong);
  border-radius: 6px;
  padding: 6px 14px;
  font-size: 12px;
  font-weight: 500;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 6px;
  transition: border-color 0.15s, color 0.15s;
  font-family: 'DM Sans', sans-serif;
  white-space: nowrap;
}

.st-test-btn:hover:not(:disabled) {
  border-color: var(--accent);
  color: var(--accent);
}

.st-test-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

/* ── Connectivity result ────────────── */
.st-result-box {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  padding: 10px 14px;
  border-radius: 7px;
  margin: 14px 0 0;
  font-size: 13px;
  line-height: 1.45;
}

.st-result-box.success {
  background: var(--success-light);
  border: 0.5px solid #86efac;
  color: #15803d;
}

.st-result-box.failure {
  background: var(--danger-light);
  border: 0.5px solid #fca5a5;
  color: #b91c1c;
}

.st-result-icon {
  font-size: 14px;
  margin-top: 1px;
  flex-shrink: 0;
}

.st-result-msg {
  font-family: 'JetBrains Mono', monospace;
  font-size: 12px;
  word-break: break-word;
}

/* ── Toast / Error banner ──────────── */
.st-toast {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 14px;
  border-radius: 7px;
  margin: 12px 0 0;
  font-size: 13px;
  animation: st-fade-in 0.2s ease;
}

.st-toast.success {
  background: var(--success-light);
  border: 0.5px solid #86efac;
  color: #15803d;
}

.st-toast.error {
  background: var(--danger-light);
  border: 0.5px solid #fca5a5;
  color: #b91c1c;
}

.st-toast-dismiss {
  margin-left: auto;
  background: none;
  border: none;
  color: inherit;
  cursor: pointer;
  font-size: 16px;
  line-height: 1;
  opacity: 0.7;
  padding: 0 2px;
}

.st-toast-dismiss:hover {
  opacity: 1;
}

/* ── Spinner ───────────────────────── */
.st-spinner {
  width: 13px;
  height: 13px;
  border: 2px solid currentColor;
  border-top-color: transparent;
  border-radius: 50%;
  animation: st-spin 0.6s linear infinite;
  display: inline-block;
}

/* ── Active client card ────────────── */
.st-client-card {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 20px;
}

.st-client-name {
  font-size: 15px;
  font-weight: 600;
  color: var(--text-primary);
  font-family: 'JetBrains Mono', monospace;
  flex: 1;
}

.st-client-hint {
  font-size: 12px;
  color: var(--text-muted);
  margin-top: 3px;
}

.st-client-link {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  font-size: 12px;
  color: var(--accent);
  text-decoration: none;
  border: 0.5px solid var(--accent);
  border-radius: 6px;
  padding: 5px 12px;
  white-space: nowrap;
  transition: background 0.15s;
}

.st-client-link:hover {
  background: var(--accent-light);
}

/* ── Loading / Error states ────────── */
.st-loading {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 80px 0;
  color: var(--text-muted);
  font-size: 14px;
  gap: 10px;
}

.st-error-page {
  padding: 60px 32px;
  text-align: center;
  color: var(--danger);
  font-size: 14px;
}

.st-divider {
  border: none;
  border-top: 0.5px solid var(--border);
  margin: 14px 0;
}

@keyframes st-spin {
  to { transform: rotate(360deg); }
}

@keyframes st-fade-in {
  from { opacity: 0; transform: translateY(-4px); }
  to   { opacity: 1; transform: translateY(0); }
}
`;

if (typeof document !== 'undefined') {
  const id = 'settings-page-styles';
  if (!document.getElementById(id)) {
    const el = document.createElement('style');
    el.id = id;
    el.textContent = _styles;
    document.head.appendChild(el);
  }
}


// ── Shared micro-components ───────────────────────────────────────────────────

function Spinner() {
  return <span className="st-spinner" aria-label="loading" />;
}

function SuccessToast({ message = 'Settings saved', onDone }: { message?: string; onDone: () => void }) {
  useEffect(() => {
    const t = setTimeout(onDone, 3000);
    return () => clearTimeout(t);
  }, [onDone]);

  return (
    <div className="st-toast success">
      <span>✓</span>
      <span>{message}</span>
    </div>
  );
}

function ErrorBanner({ message, onDismiss }: { message: string; onDismiss: () => void }) {
  return (
    <div className="st-toast error">
      <span>✗</span>
      <span style={{ flex: 1 }}>{message}</span>
      <button className="st-toast-dismiss" onClick={onDismiss} aria-label="dismiss">×</button>
    </div>
  );
}

function ConnectivityBox({ result }: { result: ConnectivityResult }) {
  return (
    <div className={`st-result-box ${result.ok ? 'success' : 'failure'}`}>
      <span className="st-result-icon">{result.ok ? '✓' : '✗'}</span>
      <span className="st-result-msg">{result.message}</span>
    </div>
  );
}

function LoadingSpinner() {
  return (
    <div className="st-loading">
      <Spinner />
      <span>Loading settings…</span>
    </div>
  );
}

function ErrorPage({ message }: { message: string }) {
  return (
    <div className="st-error-page">
      <p>Failed to load settings: {message}</p>
      <p style={{ color: 'var(--text-muted)', marginTop: 8 }}>
        Make sure the bridge server is running (<code>uvicorn bridge.main:app --reload</code>).
      </p>
    </div>
  );
}

function PageHeader({ title, subtitle, configPath }: {
  title: string;
  subtitle: string;
  configPath: string;
}) {
  return (
    <div className="st-page-header">
      <h1 className="st-page-title">{title}</h1>
      <p className="st-page-subtitle">{subtitle}</p>
      {configPath && (
        <span className="st-config-chip">
          <span className="st-config-chip-label">config.py</span>
          {configPath}
        </span>
      )}
    </div>
  );
}


// ── Section: Database ─────────────────────────────────────────────────────────

function DatabaseSection({ initialValues }: { initialValues: DbConfig }) {
  const [form,        setForm]        = useState<DbConfig>(initialValues);
  const [pwdTouched,  setPwdTouched]  = useState(false);
  const [saving,      setSaving]      = useState(false);
  const [saveError,   setSaveError]   = useState('');
  const [saveSuccess, setSaveSuccess] = useState(false);
  const [testing,     setTesting]     = useState(false);
  const [testResult,  setTestResult]  = useState<ConnectivityResult | null>(null);

  useEffect(() => { setForm(initialValues); }, [initialValues]);

  function handleFieldChange(field: keyof DbConfig, value: string) {
    setForm(f => ({ ...f, [field]: value }));
    setTestResult(null);
  }

  async function handleSave() {
    setSaving(true);
    setSaveError('');
    try {
      const body: SaveDbRequest = {
        server:             form.server,
        database:           form.database,
        driver:             form.driver,
        trusted_connection: form.trusted_connection,
        username:           form.trusted_connection === 'yes' ? '' : form.username,
        password:           pwdTouched ? form.password : '',
      };
      await settingsApi.saveDatabase(body);
      setSaveSuccess(true);
      setPwdTouched(false);
    } catch (e: any) {
      setSaveError(e.message || 'Failed to save');
    } finally {
      setSaving(false);
    }
  }

  async function handleTest() {
    setTesting(true);
    setTestResult(null);
    try {
      const result = await settingsApi.testConnection();
      setTestResult(result);
    } catch (e: any) {
      setTestResult({ ok: false, message: e.message || 'Test failed' });
    } finally {
      setTesting(false);
    }
  }

  const isWindows = form.trusted_connection === 'yes';

  return (
    <div className="st-card">
      <div className="st-card-header">
        <span className="st-card-icon">🗄</span>
        <span className="st-card-title">DATABASE CONNECTION</span>
        <button className="st-test-btn" onClick={handleTest} disabled={testing}>
          {testing ? <><Spinner /> Testing…</> : 'Test Connection'}
        </button>
      </div>

      <div className="st-card-body">
        <div className="st-field">
          <label className="st-label">Server</label>
          <input
            className="st-input st-input-mono"
            value={form.server}
            onChange={e => handleFieldChange('server', e.target.value)}
            placeholder="localhost or localhost\SQLEXPRESS"
          />
        </div>

        <div className="st-field">
          <label className="st-label">Database</label>
          <input
            className="st-input st-input-mono"
            value={form.database}
            onChange={e => handleFieldChange('database', e.target.value)}
            placeholder="AcmeDev"
          />
        </div>

        <div className="st-field">
          <label className="st-label">ODBC Driver</label>
          <input
            className="st-input"
            value={form.driver}
            onChange={e => handleFieldChange('driver', e.target.value)}
            placeholder="ODBC Driver 17 for SQL Server"
          />
        </div>

        <div className="st-field">
          <label className="st-label">Authentication</label>
          <div className="st-radio-group">
            <label className="st-radio-option">
              <input
                type="radio"
                name="db-auth"
                checked={isWindows}
                onChange={() => { handleFieldChange('trusted_connection', 'yes'); }}
              />
              Windows Auth
            </label>
            <label className="st-radio-option">
              <input
                type="radio"
                name="db-auth"
                checked={!isWindows}
                onChange={() => { handleFieldChange('trusted_connection', 'no'); }}
              />
              SQL Login
            </label>
          </div>
        </div>

        {!isWindows && (
          <>
            <div className="st-field">
              <label className="st-label">Username</label>
              <input
                className="st-input st-input-mono"
                value={form.username}
                onChange={e => handleFieldChange('username', e.target.value)}
                placeholder="sa"
                autoComplete="username"
              />
            </div>

            <div className="st-field">
              <label className="st-label">Password</label>
              <input
                className="st-input st-input-mono"
                type="password"
                value={form.password}
                placeholder={pwdTouched ? '' : '●●●●●●●●'}
                onChange={e => {
                  setPwdTouched(true);
                  handleFieldChange('password', e.target.value);
                }}
                autoComplete="current-password"
              />
            </div>
            {!pwdTouched && (
              <div style={{ paddingLeft: 172, marginTop: -8, marginBottom: 10 }}>
                <span className="st-hint">Leave blank to keep existing password unchanged</span>
              </div>
            )}
          </>
        )}

        {testResult && <ConnectivityBox result={testResult} />}
        {saveError && <ErrorBanner message={saveError} onDismiss={() => setSaveError('')} />}
        {saveSuccess && <SuccessToast message="Database settings saved" onDone={() => setSaveSuccess(false)} />}
      </div>

      <div className="st-card-footer">
        <button className="st-save-btn" onClick={handleSave} disabled={saving}>
          {saving ? 'Saving…' : 'Save Database'}
        </button>
      </div>
    </div>
  );
}


// ── Section: Ollama ───────────────────────────────────────────────────────────

interface OllamaFormState {
  base_url:  string;
  optimizer: string;
  reasoner:  string;
}

function OllamaSection({ initialValues }: { initialValues: { base_url: string; models: { optimizer: string; reasoner: string } } }) {
  const [form,        setForm]        = useState<OllamaFormState>({
    base_url:  initialValues.base_url,
    optimizer: initialValues.models.optimizer,
    reasoner:  initialValues.models.reasoner,
  });
  const [saving,      setSaving]      = useState(false);
  const [saveError,   setSaveError]   = useState('');
  const [saveSuccess, setSaveSuccess] = useState(false);
  const [testing,     setTesting]     = useState(false);
  const [testResult,  setTestResult]  = useState<ConnectivityResult | null>(null);

  useEffect(() => {
    setForm({
      base_url:  initialValues.base_url,
      optimizer: initialValues.models.optimizer,
      reasoner:  initialValues.models.reasoner,
    });
  }, [initialValues]);

  function handleFieldChange(field: keyof OllamaFormState, value: string) {
    setForm(f => ({ ...f, [field]: value }));
    setTestResult(null);
  }

  async function handleSave() {
    setSaving(true);
    setSaveError('');
    try {
      const body: SaveOllamaRequest = {
        base_url:  form.base_url,
        optimizer: form.optimizer,
        reasoner:  form.reasoner,
      };
      await settingsApi.saveOllama(body);
      setSaveSuccess(true);
    } catch (e: any) {
      setSaveError(e.message || 'Failed to save');
    } finally {
      setSaving(false);
    }
  }

  async function handleTest() {
    setTesting(true);
    setTestResult(null);
    try {
      const result = await settingsApi.testOllama();
      setTestResult(result);
    } catch (e: any) {
      setTestResult({ ok: false, message: e.message || 'Test failed' });
    } finally {
      setTesting(false);
    }
  }

  return (
    <div className="st-card">
      <div className="st-card-header">
        <span className="st-card-icon">🤖</span>
        <span className="st-card-title">OLLAMA</span>
        <button className="st-test-btn" onClick={handleTest} disabled={testing}>
          {testing ? <><Spinner /> Testing…</> : 'Test Ollama'}
        </button>
      </div>

      <div className="st-card-body">
        <div className="st-field">
          <label className="st-label">Base URL</label>
          <input
            className="st-input st-input-mono"
            value={form.base_url}
            onChange={e => handleFieldChange('base_url', e.target.value)}
            placeholder="http://localhost:11434"
          />
        </div>

        <div className="st-field">
          <div>
            <div className="st-label">Optimizer model</div>
            <div className="st-hint">Query rewriting (Qwen2.5-Coder)</div>
          </div>
          <input
            className="st-input st-input-mono"
            value={form.optimizer}
            onChange={e => handleFieldChange('optimizer', e.target.value)}
            placeholder="qwen2.5-coder:14b"
          />
        </div>

        <div className="st-field">
          <div>
            <div className="st-label">Reasoner model</div>
            <div className="st-hint">Diagnosis &amp; plan analysis (DeepSeek-R1)</div>
          </div>
          <input
            className="st-input st-input-mono"
            value={form.reasoner}
            onChange={e => handleFieldChange('reasoner', e.target.value)}
            placeholder="deepseek-r1:14b"
          />
        </div>

        {testResult && <ConnectivityBox result={testResult} />}
        {saveError && <ErrorBanner message={saveError} onDismiss={() => setSaveError('')} />}
        {saveSuccess && <SuccessToast message="Ollama settings saved" onDone={() => setSaveSuccess(false)} />}
      </div>

      <div className="st-card-footer">
        <button className="st-save-btn" onClick={handleSave} disabled={saving}>
          {saving ? 'Saving…' : 'Save Ollama'}
        </button>
      </div>
    </div>
  );
}


// ── Section: Agent Behaviour ──────────────────────────────────────────────────

function AgentSection({ initialValues }: { initialValues: AgentConfig }) {
  const [form,        setForm]        = useState<AgentConfig>(initialValues);
  const [saving,      setSaving]      = useState(false);
  const [saveError,   setSaveError]   = useState('');
  const [saveSuccess, setSaveSuccess] = useState(false);
  const [runsError,   setRunsError]   = useState('');

  useEffect(() => { setForm(initialValues); }, [initialValues]);

  function handleRuns(value: string) {
    const n = parseInt(value, 10);
    if (isNaN(n)) {
      setRunsError('Must be a number');
    } else if (n < 1 || n > 100) {
      setRunsError('Must be between 1 and 100');
    } else {
      setRunsError('');
    }
    setForm(f => ({ ...f, benchmark_runs: isNaN(n) ? f.benchmark_runs : n }));
  }

  async function handleSave() {
    if (runsError) return;
    setSaving(true);
    setSaveError('');
    try {
      const body: SaveAgentRequest = {
        benchmark_runs:  form.benchmark_runs,
        auto_commit_git: form.auto_commit_git,
        save_reports:    form.save_reports,
      };
      await settingsApi.saveAgent(body);
      setSaveSuccess(true);
    } catch (e: any) {
      setSaveError(e.message || 'Failed to save');
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="st-card">
      <div className="st-card-header">
        <span className="st-card-icon">⚙</span>
        <span className="st-card-title">AGENT BEHAVIOUR</span>
      </div>

      <div className="st-card-body">
        <div className="st-field">
          <div>
            <div className="st-label">Benchmark runs</div>
            <div className="st-hint">Each query timed N times (1–100)</div>
          </div>
          <div>
            <input
              className={`st-input st-input-number${runsError ? ' st-input-error' : ''}`}
              type="number"
              min={1}
              max={100}
              value={form.benchmark_runs}
              onChange={e => handleRuns(e.target.value)}
            />
            {runsError && (
              <div style={{ fontSize: 11, color: 'var(--danger)', marginTop: 4 }}>{runsError}</div>
            )}
          </div>
        </div>

        <div className="st-field">
          <div>
            <div className="st-label">Auto-commit Git</div>
            <div className="st-hint">Commit after every optimization</div>
          </div>
          <div className="st-toggle-group">
            <label className="st-toggle-option">
              <input
                type="radio"
                name="auto-commit"
                checked={form.auto_commit_git}
                onChange={() => setForm(f => ({ ...f, auto_commit_git: true }))}
              />
              On
            </label>
            <label className="st-toggle-option">
              <input
                type="radio"
                name="auto-commit"
                checked={!form.auto_commit_git}
                onChange={() => setForm(f => ({ ...f, auto_commit_git: false }))}
              />
              Off
            </label>
          </div>
        </div>

        <div className="st-field">
          <div>
            <div className="st-label">Save reports</div>
            <div className="st-hint">Auto-save to /reports folder</div>
          </div>
          <div className="st-toggle-group">
            <label className="st-toggle-option">
              <input
                type="radio"
                name="save-reports"
                checked={form.save_reports}
                onChange={() => setForm(f => ({ ...f, save_reports: true }))}
              />
              On
            </label>
            <label className="st-toggle-option">
              <input
                type="radio"
                name="save-reports"
                checked={!form.save_reports}
                onChange={() => setForm(f => ({ ...f, save_reports: false }))}
              />
              Off
            </label>
          </div>
        </div>

        {saveError && <ErrorBanner message={saveError} onDismiss={() => setSaveError('')} />}
        {saveSuccess && <SuccessToast message="Agent settings saved" onDone={() => setSaveSuccess(false)} />}
      </div>

      <div className="st-card-footer">
        <button className="st-save-btn" onClick={handleSave} disabled={saving || !!runsError}>
          {saving ? 'Saving…' : 'Save Agent'}
        </button>
      </div>
    </div>
  );
}


// ── Section: Sandbox ──────────────────────────────────────────────────────────

function SandboxSection({ initialValues }: { initialValues: SandboxConfig }) {
  const [form,        setForm]        = useState<SandboxConfig>(initialValues);
  const [saving,      setSaving]      = useState(false);
  const [saveError,   setSaveError]   = useState('');
  const [saveSuccess, setSaveSuccess] = useState(false);
  const [timeoutErr,  setTimeoutErr]  = useState('');

  useEffect(() => { setForm(initialValues); }, [initialValues]);

  function handleTimeout(value: string) {
    const n = parseInt(value, 10);
    if (isNaN(n) || n < 30 || n > 3600) {
      setTimeoutErr('Must be between 30 and 3600 seconds');
    } else {
      setTimeoutErr('');
    }
    setForm(f => ({ ...f, timeout_s: isNaN(n) ? f.timeout_s : n }));
  }

  async function handleSave() {
    if (timeoutErr) return;
    setSaving(true);
    setSaveError('');
    try {
      const body: SaveSandboxRequest = {
        bak_path:  form.bak_path,
        data_dir:  form.data_dir,
        timeout_s: form.timeout_s,
      };
      await settingsApi.saveSandbox(body);
      setSaveSuccess(true);
    } catch (e: any) {
      setSaveError(e.message || 'Failed to save');
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="st-card">
      <div className="st-card-header">
        <span className="st-card-icon">🛡</span>
        <span className="st-card-title">SANDBOX</span>
      </div>

      <div className="st-card-body">
        <div style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 16, lineHeight: 1.5 }}>
          The shadow DB sandbox restores a <code>.bak</code> to a temporary copy of your database,
          applies proposed changes there, and benchmarks before touching production.
        </div>

        <div className="st-field">
          <div>
            <div className="st-label">BAK file path</div>
            <div className="st-hint">Windows path to .bak file</div>
          </div>
          <input
            className="st-input st-input-mono"
            value={form.bak_path}
            onChange={e => setForm(f => ({ ...f, bak_path: e.target.value }))}
            placeholder={String.raw`C:\Backups\AcmeDev.bak`}
          />
        </div>

        <div className="st-field">
          <div>
            <div className="st-label">SQL data dir</div>
            <div className="st-hint">Leave blank to auto-detect</div>
          </div>
          <input
            className="st-input st-input-mono"
            value={form.data_dir}
            onChange={e => setForm(f => ({ ...f, data_dir: e.target.value }))}
            placeholder={String.raw`C:\Program Files\Microsoft SQL Server\...\DATA`}
          />
        </div>

        <div className="st-field">
          <div>
            <div className="st-label">Restore timeout</div>
            <div className="st-hint">Seconds to wait (30–3600)</div>
          </div>
          <div>
            <input
              className="st-input st-input-number"
              type="number"
              min={30}
              max={3600}
              value={form.timeout_s}
              onChange={e => handleTimeout(e.target.value)}
            />
            <span style={{ marginLeft: 8, fontSize: 12, color: 'var(--text-muted)' }}>seconds</span>
            {timeoutErr && (
              <div style={{ fontSize: 11, color: 'var(--danger)', marginTop: 4 }}>{timeoutErr}</div>
            )}
          </div>
        </div>

        {saveError && <ErrorBanner message={saveError} onDismiss={() => setSaveError('')} />}
        {saveSuccess && <SuccessToast message="Sandbox settings saved" onDone={() => setSaveSuccess(false)} />}
      </div>

      <div className="st-card-footer">
        <button className="st-save-btn" onClick={handleSave} disabled={saving || !!timeoutErr}>
          {saving ? 'Saving…' : 'Save Sandbox'}
        </button>
      </div>
    </div>
  );
}


// ── Section: Active Client (read-only) ────────────────────────────────────────

function ActiveClientSection({ client }: { client: string }) {
  return (
    <div className="st-card">
      <div className="st-card-header">
        <span className="st-card-icon">👤</span>
        <span className="st-card-title">ACTIVE CLIENT</span>
      </div>

      <div className="st-client-card">
        <div style={{ flex: 1 }}>
          <div className="st-client-name">{client || '—'}</div>
          <div className="st-client-hint">
            To switch client or create a new workspace, use the Client Manager page.
          </div>
        </div>
        <Link to="/clients" className="st-client-link">
          → Manage in Client Manager
        </Link>
      </div>
    </div>
  );
}


// ── Main page ─────────────────────────────────────────────────────────────────

export default function Settings() {
  const [settings,  setSettings]  = useState<AllSettings | null>(null);
  const [loadError, setLoadError] = useState('');

  useEffect(() => {
    settingsApi.getAll()
      .then(setSettings)
      .catch((e: any) => setLoadError(e.message || 'Failed to load settings'));
  }, []);

  if (loadError)  return <ErrorPage message={loadError} />;
  if (!settings)  return <LoadingSpinner />;

  return (
    <div className="st-page">
      <PageHeader
        title="Settings"
        subtitle="Configure config.py from the web UI"
        configPath={settings.config_path}
      />

      <DatabaseSection    initialValues={settings.db}      />
      <OllamaSection      initialValues={settings.ollama}  />
      <AgentSection       initialValues={settings.agent}   />
      <SandboxSection     initialValues={settings.sandbox} />
      <ActiveClientSection client={settings.active_client} />
    </div>
  );
}
