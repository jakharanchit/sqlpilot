// web/src/pages/ModelManager.tsx
// Phase 5 — Ollama model management page.

import { useState, useEffect } from 'react';
import { modelsApi } from '../api/models';
import type { OllamaModel, RunningModel, ActiveModels } from '../types';

import ActiveModelsPanel from '../components/models/ActiveModelsPanel';
import ModelCard from '../components/models/ModelCard';
import PullModelPanel from '../components/models/PullModelPanel';
import RunningModelsPanel from '../components/models/RunningModelsPanel';
import { LoadingSpinner } from '@/components/shared/LoadingSpinner';

// Shared layout components assumed to exist from Phase 1
import TopBar from '../components/layout/TopBar';

const _styles = `
.mm-page {
  max-width: 820px;
  padding: 24px 28px;
}
.mm-section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 13px;
  font-weight: 600;
  color: var(--text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.06em;
  margin-bottom: 12px;
}
.mm-section-header button {
  font-size: 12px;
  padding: 4px 12px;
  border: 0.5px solid var(--border-strong);
  border-radius: 5px;
  background: var(--bg-surface);
  color: var(--text-secondary);
  cursor: pointer;
  transition: background 0.12s;
}
.mm-section-header button:hover {
  background: var(--bg-elevated);
}
.mm-models-section {
  background: var(--bg-surface);
  border: 0.5px solid var(--border);
  border-radius: 10px;
  padding: 16px 20px;
  margin-bottom: 20px;
}
.mm-empty {
  font-size: 13px;
  color: var(--text-muted);
  padding: 12px 0;
  font-style: italic;
}
`;

if (typeof document !== 'undefined') {
  const id = 'mm-styles';
  if (!document.getElementById(id)) {
    const el = document.createElement('style');
    el.id = id;
    el.textContent = _styles;
    document.head.appendChild(el);
  }
}

export default function ModelManager() {
  const [data, setData] = useState<{ models: OllamaModel[]; active: ActiveModels } | null>(null);
  const [running, setRunning] = useState<RunningModel[]>([]);
  const [loading, setLoading] = useState(true);
  const [deleting, setDeleting] = useState<string | null>(null);
  const [error, setError] = useState('');

  async function load() {
    setLoading(true);
    setError('');
    try {
      const [modelsData, runningData] = await Promise.all([
        modelsApi.list(),
        modelsApi.running(),
      ]);
      setData(modelsData);
      setRunning(runningData);
    } catch (err: any) {
      setError(err?.message ?? 'Failed to load model data. Is Ollama running?');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { load(); }, []);

  async function handleDelete(name: string) {
    setDeleting(name);
    try {
      await modelsApi.delete(name);
      await load();
    } finally {
      setDeleting(null);
    }
  }

  // Determine which roles a model fills
  const activeRoles = (modelName: string): string[] => {
    if (!data) return [];
    const roles: string[] = [];
    if (data.active.optimizer === modelName) roles.push('optimizer');
    if (data.active.reasoner === modelName) roles.push('reasoner');
    return roles;
  };

  return (
    <div className="mm-page">
      <TopBar title="Model Manager"  />

      {error && (
        <div style={{
          padding: '12px 16px',
          background: 'var(--danger-light)',
          borderRadius: 8,
          color: 'var(--danger)',
          fontSize: 13,
          marginBottom: 20,
        }}>
          ✗ {error}
        </div>
      )}

      {data && <ActiveModelsPanel active={data.active} />}

      <div className="mm-models-section">
        <div className="mm-section-header">
          Available Models ({data?.models.length ?? 0} pulled)
          <button onClick={load}>↻ Refresh</button>
        </div>

        {loading && <LoadingSpinner />}

        {!loading && data?.models.length === 0 && (
          <div className="mm-empty">
            No models pulled yet. Use Pull New Model below to get started.
          </div>
        )}

        {data?.models.map(m => (
          <ModelCard
            key={m.name}
            model={m}
            activeRoles={activeRoles(m.name)}
            onDelete={handleDelete}
            deleting={deleting === m.name}
          />
        ))}
      </div>

      <PullModelPanel onPulled={load} />

      <RunningModelsPanel running={running} />
    </div>
  );
}
