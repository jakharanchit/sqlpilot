// src/pages/Dashboard.tsx
import { useEffect } from "react";
import { TopBar }           from "@/components/layout/TopBar";
import { PageShell }        from "@/components/layout/PageShell";
import { SystemStatusRow }  from "@/components/dashboard/SystemStatusRow";
import { HardwareGauges }   from "@/components/dashboard/HardwareGauges";
import { ActiveJobCard }    from "@/components/dashboard/ActiveJobCard";
import { RecentRunsPanel }  from "@/components/dashboard/RecentRunsPanel";
import { useSystemStats }   from "@/hooks/useSystemStats";
import { useClientStore }   from "@/store/clientStore";

// Kick off stats polling as soon as the Dashboard mounts
function StatsPoller() {
  useSystemStats();
  return null;
}

export default function Dashboard() {
  const setActiveClient = useClientStore(s => s.setActiveClient);

  // Resolve active client from the bridge on mount
  useEffect(() => {
    fetch("/api/clients/active")
      .then(r => r.ok ? r.json() : null)
      .then(d => { if (d?.name) setActiveClient(d.name); })
      .catch(() => {/* no clients endpoint yet — Phase 5 */});
  }, [setActiveClient]);

  return (
    <>
      <StatsPoller />
      <TopBar
        title="Dashboard"
        actions={<ActiveJobIndicator />}
      />
      <PageShell>
        <SystemStatusRow />
        <HardwareGauges />
        <ActiveJobCard />
        <RecentRunsPanel />
      </PageShell>
    </>
  );
}

/** Small amber pill in the TopBar when a job is running */
function ActiveJobIndicator() {
  // Phase 2 wires this to jobStore.activeJobId
  // Phase 1: always hidden (no active job)
  return null;
}
