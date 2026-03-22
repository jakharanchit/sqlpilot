import { useEffect, useState } from 'react';
import { useJobStore } from '../../store/jobStore';
import { jobsApi }     from '../../api/jobs';
import type { JobSummary } from '../../types';

function ImpBadge({ pct }: { pct: number | null }) {
  if (pct === null || pct === undefined) return <span className="rrp-badge neutral">—</span>;
  if (pct > 0)  return <span className="rrp-badge success">+{pct}%</span>;
  if (pct < 0)  return <span className="rrp-badge danger">{pct}%</span>;
  return <span className="rrp-badge neutral">0%</span>;
}

function relTime(iso: string): string {
  const diff = Math.floor((Date.now() - new Date(iso).getTime()) / 1000);
  if (diff < 60)  return `${diff}s ago`;
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  return `${Math.floor(diff / 3600)}h ago`;
}

export function RecentRunsPanel() {
  const { status, result } = useJobStore();
  const [runs, setRuns] = useState<JobSummary[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchRuns = () => {
    jobsApi.list({ limit: 8 })
      .then((data) => { setRuns(data); setLoading(false); })
      .catch(() => setLoading(false));
  };

  // Fetch on mount
  useEffect(() => { fetchRuns(); }, []);

  // Refresh when a job completes
  useEffect(() => {
    if (status === 'completed' || status === 'failed') {
      const t = setTimeout(fetchRuns, 600);
      return () => clearTimeout(t);
    }
  }, [status]);

  if (loading) {
    return (
      <div className="card rrp-card">
        <div className="rrp-header">Recent Jobs</div>
        <div className="rrp-loading">Loading…</div>
      </div>
    );
  }

  return (
    <div className="card rrp-card">
      <div className="rrp-header">
        <span>Recent Jobs</span>
        <button className="rrp-refresh" onClick={fetchRuns} title="Refresh">↺</button>
      </div>

      {runs.length === 0 ? (
        <div className="rrp-empty">No jobs yet — submit a query to start</div>
      ) : (
        <div className="rrp-list">
          {runs.map((job) => {
            const impPct = job.status === 'completed' && result
              ? result.benchmark?.improvement_pct ?? null
              : null;

            return (
              <div key={job.job_id} className="rrp-row">
                <div className="rrp-left">
                  <span className={`rrp-type-badge rrp-type-${job.type}`}>
                    {job.type.replace('_', ' ')}
                  </span>
                  <span className="rrp-time">{relTime(job.created_at)}</span>
                </div>
                <div className="rrp-right">
                  <span className={`rrp-status rrp-status-${job.status}`}>
                    {job.status}
                  </span>
                  <ImpBadge pct={impPct} />
                </div>
              </div>
            );
          })}
        </div>
      )}

      <style>{`
        .rrp-card { padding: 14px; }
        .rrp-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          font-size: 11px;
          font-weight: 700;
          color: var(--text-secondary);
          letter-spacing: 0.06em;
          text-transform: uppercase;
          margin-bottom: 10px;
        }
        .rrp-refresh {
          background: none;
          border: none;
          cursor: pointer;
          color: var(--text-muted);
          font-size: 14px;
          padding: 0 4px;
          line-height: 1;
          transition: color 0.15s;
        }
        .rrp-refresh:hover { color: var(--accent); }
        .rrp-loading, .rrp-empty {
          font-size: 12px;
          color: var(--text-muted);
          text-align: center;
          padding: 12px 0;
        }
        .rrp-list { display: flex; flex-direction: column; gap: 6px; }
        .rrp-row {
          display: flex;
          justify-content: space-between;
          align-items: center;
          padding: 6px 8px;
          border-radius: 7px;
          background: var(--bg-elevated);
        }
        .rrp-left { display: flex; align-items: center; gap: 7px; }
        .rrp-right { display: flex; align-items: center; gap: 6px; }
        .rrp-type-badge {
          font-size: 10px;
          font-weight: 600;
          padding: 2px 7px;
          border-radius: 4px;
          background: var(--accent-light);
          color: var(--accent);
        }
        .rrp-type-badge.rrp-type-analyze { background: #f0fdf4; color: #16a34a; }
        .rrp-type-badge.rrp-type-benchmark { background: #fffbeb; color: #d97706; }
        .rrp-time { font-size: 10px; color: var(--text-muted); }
        .rrp-status {
          font-size: 10px;
          font-weight: 500;
          color: var(--text-muted);
        }
        .rrp-status.rrp-status-completed { color: var(--success); }
        .rrp-status.rrp-status-failed    { color: var(--danger); }
        .rrp-status.rrp-status-running   { color: var(--accent); }
        .rrp-badge {
          font-size: 10px;
          font-weight: 600;
          padding: 1px 6px;
          border-radius: 4px;
        }
        .rrp-badge.success { background: var(--success-light); color: #166534; }
        .rrp-badge.danger  { background: var(--danger-light);  color: #991b1b; }
        .rrp-badge.neutral { background: var(--bg-elevated);   color: var(--text-muted); }
      `}</style>
    </div>
  );
}
