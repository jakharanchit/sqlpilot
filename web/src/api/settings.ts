import { apiFetch } from './client';
import type { AllSettings, ConnectivityResult } from '../types';

export interface SaveDbRequest {
  server:             string;
  database:           string;
  driver:             string;
  trusted_connection: 'yes' | 'no';
  username:           string;
  password:           string;
}

export interface SaveOllamaRequest {
  base_url:  string;
  optimizer: string;
  reasoner:  string;
}

export interface SaveAgentRequest {
  benchmark_runs:  number;
  auto_commit_git: boolean;
  save_reports:    boolean;
}

export interface SaveSandboxRequest {
  bak_path:  string;
  data_dir:  string;
  timeout_s: number;
}

export const settingsApi = {
  /** Get all current config.py values. */
  getAll: (): Promise<AllSettings> =>
    apiFetch('/api/settings'),

  /** Save DB connection fields. */
  saveDatabase: (body: SaveDbRequest): Promise<{ ok: boolean }> =>
    apiFetch('/api/settings/database', {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify(body),
    }),

  /** Save Ollama URL and model names. */
  saveOllama: (body: SaveOllamaRequest): Promise<{ ok: boolean }> =>
    apiFetch('/api/settings/ollama', {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify(body),
    }),

  /** Save agent behaviour flags. */
  saveAgent: (body: SaveAgentRequest): Promise<{ ok: boolean }> =>
    apiFetch('/api/settings/agent', {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify(body),
    }),

  /** Save sandbox paths and timeout. */
  saveSandbox: (body: SaveSandboxRequest): Promise<{ ok: boolean }> =>
    apiFetch('/api/settings/sandbox', {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify(body),
    }),

  /** Test DB connection live (does not save). */
  testConnection: (): Promise<ConnectivityResult> =>
    apiFetch('/api/settings/test-connection'),

  /** Test Ollama reachability live (does not save). */
  testOllama: (): Promise<ConnectivityResult> =>
    apiFetch('/api/settings/test-ollama'),
};
