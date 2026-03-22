// src/pages/Optimizer.tsx — Phase 2
import { TopBar }     from "@/components/layout/TopBar";
import { PageShell }  from "@/components/layout/PageShell";
import { EmptyState } from "@/components/shared/EmptyState";

export default function Optimizer() {
  return (
    <>
      <TopBar title="Query Optimizer" />
      <PageShell>
        <EmptyState
          title="Query Optimizer — Phase 2"
          description="Submit a SQL query and watch the 9-step pipeline stream live."
        />
      </PageShell>
    </>
  );
}
