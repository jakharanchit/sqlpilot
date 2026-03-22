import { api } from './client';
import type { JobDetail, JobSummary, JobStatus } from '../types';

export const jobsApi = {
  create: async (type: string, params: object): Promise<{
    job_id: string;
    status: JobStatus;
    created_at: string;
    type: string;
  }> => api.post('/api/jobs', { type, params }),

  list: async (opts?: {
    type?:   string;
    status?: string;
    limit?:  number;
    offset?: number;
  }): Promise<JobSummary[]> => {
    const q = new URLSearchParams();
    if (opts?.type)   q.set('type',   opts.type);
    if (opts?.status) q.set('status', opts.status);
    if (opts?.limit)  q.set('limit',  String(opts.limit));
    if (opts?.offset) q.set('offset', String(opts.offset));
    const qs = q.toString();
    return api.get(`/api/jobs${qs ? `?${qs}` : ''}`);
  },

  get: (jobId: string): Promise<JobDetail> =>
    api.get(`/api/jobs/${jobId}`),

  cancel: (jobId: string): Promise<{ cancelled: boolean; job_id: string }> =>
    api.delete(`/api/jobs/${jobId}`),

  /** Build the SSE stream URL for a job. */
  streamUrl: (jobId: string): string => `/api/jobs/${jobId}/stream`,
};
