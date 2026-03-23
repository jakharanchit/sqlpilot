// src/pages/PlanVisualizer.tsx — Phase 6
import TopBar     from "@/components/layout/TopBar";
import { PageShell }  from "@/components/layout/PageShell";
import { EmptyState } from "@/components/shared/EmptyState";

export default function PlanVisualizer() {
  return (
    <>
      <TopBar title="Plan Visualizer" />
      <PageShell>
        <EmptyState
          title="Plan Visualizer — Phase 6"
          description="Upload .sqlplan files for D3 before/after diff visualization."
        />
      </PageShell>
    </>
  );
}
