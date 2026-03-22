import { useCallback } from 'react';
import { QueryInput }   from '../components/optimizer/QueryInput';
import { PipelineLog }  from '../components/optimizer/PipelineLog';
import { StepProgress } from '../components/optimizer/StepProgress';
import { ResultPanel }  from '../components/optimizer/ResultPanel';
import { useJob }       from '../hooks/useJob';
import { useJobStore }  from '../store/jobStore';

export default function Optimizer() {
  const { runFullPipeline, runAnalyze, runBenchmark, cancel, isRunning } = useJob();
  const store = useJobStore();

  const handleFullRun = useCallback((
    query:         string,
    label:         string,
    benchmarkRuns: number | null,
    safe:          boolean,
    noDeploy:      boolean,
  ) => {
    runFullPipeline({ query, label, benchmark_runs: benchmarkRuns, safe, no_deploy: noDeploy });
  }, [runFullPipeline]);

  const handleAnalyze = useCallback((query: string, label: string) => {
    runAnalyze({ query, label });
  }, [runAnalyze]);

  const handleBenchmark = useCallback((
    before: string,
    after:  string,
    label:  string,
    runs:   number | null,
  ) => {
    runBenchmark({ before, after, label, runs: runs ?? undefined });
  }, [runBenchmark]);

  const handleClear = useCallback(() => store.reset(), [store]);

  return (
    <div className="optimizer-page">
      {/* ── Left: query input ─────────────────────────────── */}
      <div className="op-left card">
        <QueryInput
          onFullRun={handleFullRun}
          onAnalyze={handleAnalyze}
          onBenchmark={handleBenchmark}
          isRunning={isRunning}
          onCancel={cancel}
        />
      </div>

      {/* ── Middle: pipeline log + step progress ──────────── */}
      <div className="op-middle">
        {/* Step tracker */}
        <div className="op-steps card">
          <StepProgress
            currentStep={store.currentStep}
            totalSteps={store.totalSteps}
            stepLabel={store.stepLabel}
            status={store.status}
          />
        </div>

        {/* Live log */}
        <div className="op-log">
          <PipelineLog
            lines={store.logLines}
            status={store.status}
            onClear={store.logLines.length > 0 ? handleClear : undefined}
          />
        </div>
      </div>

      {/* ── Right: results ────────────────────────────────── */}
      <div className="op-right card">
        <ResultPanel
          result={store.result}
          status={store.status}
          error={store.error}
        />
      </div>

      <style>{`
        .optimizer-page {
          display: grid;
          grid-template-columns: 320px 1fr 300px;
          gap: 14px;
          height: 100%;
          min-height: 0;
        }
        .op-left, .op-right {
          height: 100%;
          min-height: 0;
          overflow: hidden;
        }
        .op-middle {
          display: flex;
          flex-direction: column;
          gap: 10px;
          min-height: 0;
        }
        .op-steps {
          flex-shrink: 0;
          padding: 12px 14px;
          max-height: 280px;
          overflow-y: auto;
        }
        .op-log {
          flex: 1;
          min-height: 0;
          border-radius: 10px;
          overflow: hidden;
        }

        /* Responsive: collapse to 2-col on narrower screens */
        @media (max-width: 1100px) {
          .optimizer-page {
            grid-template-columns: 300px 1fr;
            grid-template-rows: 1fr auto;
          }
          .op-right {
            grid-column: 1 / -1;
            height: auto;
            max-height: 400px;
          }
        }
      `}</style>
    </div>
  );
}
