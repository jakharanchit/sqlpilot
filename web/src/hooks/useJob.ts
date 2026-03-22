import { useCallback, useState } from 'react';
import { useSSE } from './useSSE';
import { useJobStore } from '../store/jobStore';
import { jobsApi } from '../api/jobs';
import type {
  AnalyzeParams,
  FullRunParams,
  BenchmarkParams,
  SSEEvent,
  SSEStepEvent,
  SSELogEvent,
} from '../types';

export function useJob() {
  const store = useJobStore();
  const [streamUrl, setStreamUrl] = useState<string | null>(null);

  // ── SSE consumer ──────────────────────────────────────────────────────────
  useSSE(streamUrl, {
    onMessage: (event: SSEEvent) => {
      if (event.type === 'log') {
        const e = event as SSELogEvent;
        store.appendLog({ line: e.line, ts: e.ts, kind: 'log' });
      } else if (event.type === 'step') {
        const e = event as SSEStepEvent;
        store.setStep(e.step, e.total, e.label);
        store.appendLog({
          line: `▶ Step ${e.step}/${e.total} — ${e.label}`,
          ts: new Date().toLocaleTimeString('en-GB', { hour12: false }),
          kind: 'step',
        });
      }
    },
    onComplete: (result) => {
      store.setResult(result);
      store.setStatus('completed');
      setStreamUrl(null);
    },
    onError: (message) => {
      store.setError(message);
      store.setStatus('failed');
      setStreamUrl(null);
      store.appendLog({
        line: `✗ ${message}`,
        ts: new Date().toLocaleTimeString('en-GB', { hour12: false }),
        kind: 'error',
      });
    },
  });

  // ── Submit helpers ────────────────────────────────────────────────────────
  const _submit = useCallback(async (type: string, params: object): Promise<string> => {
    store.reset();
    const job = await jobsApi.create(type, params);
    store.setActiveJob(job.job_id, job.status as any);
    setStreamUrl(`/api/jobs/${job.job_id}/stream`);
    return job.job_id;
  }, [store]);

  const runFullPipeline = useCallback(
    (params: FullRunParams) => _submit('full_run', params),
    [_submit],
  );

  const runAnalyze = useCallback(
    (params: AnalyzeParams) => _submit('analyze', params),
    [_submit],
  );

  const runBenchmark = useCallback(
    (params: BenchmarkParams) => _submit('benchmark', params),
    [_submit],
  );

  const cancel = useCallback(async () => {
    if (!store.activeJobId) return;
    await jobsApi.cancel(store.activeJobId);
    setStreamUrl(null);
    store.setStatus('cancelled');
  }, [store]);

  const isRunning = store.status === 'running' || store.status === 'queued';

  return {
    runFullPipeline,
    runAnalyze,
    runBenchmark,
    cancel,
    isRunning,
    status: store.status,
  };
}
