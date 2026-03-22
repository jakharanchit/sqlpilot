import { TopBar } from "@/components/layout/TopBar";
import { PageShell } from "@/components/layout/PageShell";

import { useState, useEffect } from 'react';
import { historyApi } from '../api/history';
import type { HistoryStats, RunRecord } from '../types';
import StatsRow    from '../components/history/StatsRow';
import RunsTable   from '../components/history/RunsTable';
import TrendChart  from '../components/history/TrendChart';
import ComparePanel from '../components/history/ComparePanel';
import MigrationList from '../components/migrations/MigrationList';

type Tab = 'runs' | 'trends' | 'compare' | 'migrations';

const TABS: { key: Tab; label: string; icon: string }[] = [
  { key: 'runs',       label: 'Runs',       icon: '📋' },
  { key: 'trends',     label: 'Trends',     icon: '📈' },
  { key: 'compare',    label: 'Compare',    icon: '⚖️' },
  { key: 'migrations', label: 'Migrations', icon: '🚀' },
];

export default function History() {
  const [tab,            setTab]            = useState<Tab>('runs');
  const [stats,          setStats]          = useState<HistoryStats | null>(null);
  const [compareRunA,    setCompareRunA]    = useState<RunRecord | null>(null);

  useEffect(() => {
    historyApi.stats()
      .then(setStats)
      .catch(() => {/* non-fatal */});
  }, []);

  // When a run is clicked in the table, switch to Compare tab
  function handleSelectRun(run: RunRecord) {
    setCompareRunA(run);
    setTab('compare');
  }

  return (
    <>
      <TopBar title="History & Migrations" />
      <PageShell>
        <div className="history-page">
          <p className="history-sub" style={{ marginBottom: 16 }}>
            Browse every optimization run, view trends, compare results, and manage migrations
          </p>

      {/* Stats headline */}
      <StatsRow stats={stats} />

      {/* Tab bar */}
      <div className="history-tabs">
        {TABS.map(t => (
          <button
            key={t.key}
            className={`history-tab${tab === t.key ? ' history-tab--active' : ''}`}
            onClick={() => setTab(t.key)}
          >
            <span className="history-tab__icon">{t.icon}</span>
            {t.label}
          </button>
        ))}
      </div>

      {/* Tab content */}
      <div className="history-content">
        {tab === 'runs' && (
          <RunsTable onSelectRun={handleSelectRun} />
        )}
        {tab === 'trends' && (
          <TrendChart />
        )}
        {tab === 'compare' && (
          <ComparePanel preselectedA={compareRunA} />
        )}
        {tab === 'migrations' && (
          <MigrationList />
        )}
      </div>
    </div>
    </PageShell>
    </>
  );
}

/* ── Styles ─────────────────────────────────────────────── */
const _styles = `
.history-page {
  display: flex;
  flex-direction: column;
  gap: 0;
  max-width: 1200px;
}

.history-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  margin-bottom: 20px;
}

.history-title {
  font-size: 22px;
  font-weight: 700;
  color: var(--text-primary);
  margin: 0 0 4px;
}

.history-sub {
  font-size: 13px;
  color: var(--text-muted);
  margin: 0;
}

.history-tabs {
  display: flex;
  gap: 2px;
  margin-bottom: 16px;
  border-bottom: 1.5px solid var(--border);
  padding-bottom: 0;
}

.history-tab {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 9px 18px;
  background: none;
  border: none;
  border-bottom: 2px solid transparent;
  margin-bottom: -1.5px;
  font-size: 13px;
  font-weight: 500;
  color: var(--text-secondary);
  cursor: pointer;
  transition: color 0.15s, border-color 0.15s;
  white-space: nowrap;
}
.history-tab:hover { color: var(--text-primary); }
.history-tab--active {
  color: var(--accent);
  border-bottom-color: var(--accent);
  font-weight: 600;
}

.history-tab__icon {
  font-size: 15px;
}

.history-content {
  padding-top: 4px;
}
`;

if (typeof document !== 'undefined') {
  const id = 'history-page-styles';
  if (!document.getElementById(id)) {
    const el = document.createElement('style');
    el.id = id;
    el.textContent = _styles;
    document.head.appendChild(el);
  }
}
