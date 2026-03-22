// src/pages/DeploymentGate.tsx — Phase 4
import { TopBar }     from "@/components/layout/TopBar";
import { PageShell }  from "@/components/layout/PageShell";
import { EmptyState } from "@/components/shared/EmptyState";

export default function DeploymentGate() {
  return (
    <>
      <TopBar title="Deployment Gate" />
      <PageShell>
        <EmptyState
          title="Deployment Gate — Phase 4"
          description="Sandbox test, confirm, and deploy SQL migrations safely."
        />
      </PageShell>
    </>
  );
}
