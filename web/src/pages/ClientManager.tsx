// src/pages/ClientManager.tsx — Phase 5
import { TopBar }     from "@/components/layout/TopBar";
import { PageShell }  from "@/components/layout/PageShell";
import { EmptyState } from "@/components/shared/EmptyState";

export default function ClientManager() {
  return (
    <>
      <TopBar title="Client Manager" />
      <PageShell>
        <EmptyState
          title="Client Manager — Phase 5"
          description="Switch clients, create workspaces, and edit connection settings."
        />
      </PageShell>
    </>
  );
}
