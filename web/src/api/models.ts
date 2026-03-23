// web/src/api/models.ts
// Phase 5 — Ollama model management API calls.

import { apiFetch } from './client';
import type { OllamaModel, RunningModel, ActiveModels, Job } from '../types';

export const modelsApi = {
  /** List all pulled models + active model config. */
  list: (): Promise<{ models: OllamaModel[]; active: ActiveModels }> =>
    apiFetch('/api/models'),

  /** Models currently loaded in Ollama memory. */
  running: (): Promise<RunningModel[]> =>
    apiFetch('/api/models/running'),

  /** Enqueue a pull job. Stream progress via /api/jobs/{id}/stream. */
  pull: (name: string): Promise<Job> =>
    apiFetch<Job>('/api/models/pull', {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify({ name }),
    }),

  /** Delete a model from Ollama. */
  delete: (name: string): Promise<{ deleted: boolean; name: string }> =>
    apiFetch(`/api/models/${encodeURIComponent(name)}`, { method: 'DELETE' }),
};
