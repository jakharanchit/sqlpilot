import { create } from 'zustand';
import type { JobResult, JobStatus, LogLine } from '../types';

interface JobStore {
  activeJobId:  string | null;
  status:       JobStatus | null;
  logLines:     LogLine[];
  currentStep:  number;
  totalSteps:   number;
  stepLabel:    string;
  result:       JobResult | null;
  error:        string | null;

  setActiveJob: (id: string, status: JobStatus) => void;
  setStatus:    (status: JobStatus) => void;
  appendLog:    (line: LogLine) => void;
  setStep:      (step: number, total: number, label: string) => void;
  setResult:    (result: JobResult) => void;
  setError:     (error: string) => void;
  reset:        () => void;
}

const INITIAL: Pick<JobStore,
  'activeJobId' | 'status' | 'logLines' | 'currentStep' |
  'totalSteps' | 'stepLabel' | 'result' | 'error'
> = {
  activeJobId:  null,
  status:       null,
  logLines:     [],
  currentStep:  0,
  totalSteps:   9,
  stepLabel:    '',
  result:       null,
  error:        null,
};

export const useJobStore = create<JobStore>((set) => ({
  ...INITIAL,

  setActiveJob: (id, status) => set({ activeJobId: id, status }),
  setStatus:    (status) => set({ status }),
  appendLog:    (line) => set((s) => ({
    logLines: s.logLines.length > 2000
      ? [...s.logLines.slice(-1800), line]   // cap at 2000 lines
      : [...s.logLines, line],
  })),
  setStep: (step, total, label) => set({ currentStep: step, totalSteps: total, stepLabel: label }),
  setResult: (result) => set({ result }),
  setError:  (error)  => set({ error }),
  reset: () => set(INITIAL),
}));
