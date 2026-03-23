// web/src/api/clients.ts
// Phase 5 — Multi-client workspace API calls.

import { apiFetch } from './client';
import type {
  ClientRecord,
  ClientConfig,
  ClientPaths,
  NewClientRequest,
  UpdateClientRequest,
} from '../types';

export interface ClientDetail {
  name:   string;
  config: ClientConfig;
  paths:  ClientPaths;
}

export const clientsApi = {
  /** List all client workspaces with summary stats. */
  list: (): Promise<ClientRecord[]> =>
    apiFetch('/api/clients'),

  /** Full config and paths for the currently active client. */
  active: (): Promise<ClientDetail> =>
    apiFetch('/api/clients/active'),

  /** Switch the active client. Returns the new active client's detail. */
  switchTo: (name: string): Promise<ClientDetail> =>
    apiFetch(`/api/clients/${encodeURIComponent(name)}/switch`, { method: 'POST' }),

  /** Create a new client workspace. */
  create: (body: NewClientRequest): Promise<ClientDetail> =>
    apiFetch('/api/clients', {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify(body),
    }),

  /** Full config and paths for a named client. */
  get: (name: string): Promise<ClientDetail> =>
    apiFetch(`/api/clients/${encodeURIComponent(name)}`),

  /** Update a client's settings (only supplied fields are changed). */
  update: (name: string, body: UpdateClientRequest): Promise<ClientConfig> =>
    apiFetch(`/api/clients/${encodeURIComponent(name)}`, {
      method:  'PUT',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify(body),
    }),

  /** Delete a client workspace. Blocked if it is the active client. */
  delete: (name: string): Promise<{ deleted: boolean; name: string }> =>
    apiFetch(`/api/clients/${encodeURIComponent(name)}`, { method: 'DELETE' }),
};
