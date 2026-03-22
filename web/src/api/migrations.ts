import { apiFetch } from './client';
import type { Migration } from '../types';

export const migrationsApi = {
  list: (status?: string): Promise<Migration[]> => {
    const qs = status ? `?status=${encodeURIComponent(status)}` : '';
    return apiFetch<Migration[]>(`/api/migrations${qs}`);
  },

  get: (number: number): Promise<Migration> =>
    apiFetch<Migration>(`/api/migrations/${number}`),

  markApplied: (
    number: number,
    client?: string,
  ): Promise<{ success: boolean; migration: Migration }> =>
    apiFetch<{ success: boolean; migration: Migration }>(
      `/api/migrations/${number}/apply`,
      {
        method:  'POST',
        headers: { 'Content-Type': 'application/json' },
        body:    JSON.stringify({ client: client ?? null }),
      },
    ),

  rollback: (
    number: number,
  ): Promise<{ success: boolean; migration: Migration }> =>
    apiFetch<{ success: boolean; migration: Migration }>(
      `/api/migrations/${number}/rollback`,
      { method: 'POST' },
    ),
};
