// web/src/api/sandbox.ts
import { apiFetch } from './client';
import type { Job, ShadowDB } from '../types';

export const sandboxApi = {
  /** Enqueue a sandbox test job. Returns a Job — stream via /api/jobs/{id}/stream. */
  runTest: (opts?: {
    migration_numbers?: number[];
    bak_path?:          string;
    threshold_pct?:     number;
  }): Promise<Job> =>
    apiFetch<Job>('/api/sandbox/test', {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify(opts ?? {}),
    }),

  /** List all shadow databases currently on SQL Server. */
  listShadows: (): Promise<ShadowDB[]> =>
    apiFetch<ShadowDB[]>('/api/sandbox/shadows'),

  /** Destroy a named shadow database. */
  destroyShadow: (name: string): Promise<{ destroyed: boolean; name: string }> =>
    apiFetch<{ destroyed: boolean; name: string }>(
      `/api/sandbox/shadows/${encodeURIComponent(name)}`,
      { method: 'DELETE' },
    ),

  /** Return sandbox configuration status. */
  config: (): Promise<{
    configured:  boolean;
    bak_path:    string;
    bak_exists:  boolean;
    shadow_name: string;
  }> => apiFetch('/api/sandbox/config'),
};
