import { apiFetch } from './client';
import type { RunRecord, HistoryStats, TrendPoint, RunComparison } from '../types';

export const historyApi = {
  list: (opts?: {
    query?:       string;
    table?:       string;
    type?:        string;
    limit?:       number;
    offset?:      number;
    top?:         boolean;
    regressions?: boolean;
  }): Promise<RunRecord[]> => {
    const params = new URLSearchParams();
    if (opts?.query)       params.set('query',       opts.query);
    if (opts?.table)       params.set('table',       opts.table);
    if (opts?.type)        params.set('type',        opts.type);
    if (opts?.limit  != null) params.set('limit',   String(opts.limit));
    if (opts?.offset != null) params.set('offset',  String(opts.offset));
    if (opts?.top)         params.set('top',         'true');
    if (opts?.regressions) params.set('regressions', 'true');
    const qs = params.toString();
    return apiFetch<RunRecord[]>(`/api/history${qs ? `?${qs}` : ''}`);
  },

  stats: (): Promise<HistoryStats> =>
    apiFetch<HistoryStats>('/api/history/stats'),

  trend: (opts: { table?: string; query_hash?: string }): Promise<TrendPoint[]> => {
    const params = new URLSearchParams();
    if (opts.table)       params.set('table',       opts.table);
    if (opts.query_hash)  params.set('query_hash',  opts.query_hash);
    return apiFetch<TrendPoint[]>(`/api/history/trend?${params.toString()}`);
  },

  compare: (a: number, b: number): Promise<RunComparison> =>
    apiFetch<RunComparison>(`/api/history/compare?a=${a}&b=${b}`),

  get: (id: number): Promise<RunRecord> =>
    apiFetch<RunRecord>(`/api/history/${id}`),

  delete: (id: number): Promise<{ deleted: boolean; id: number }> =>
    apiFetch<{ deleted: boolean; id: number }>(`/api/history/${id}`, {
      method: 'DELETE',
    }),
};
