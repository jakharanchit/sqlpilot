// src/pages/Settings.tsx — Phase 7
import { TopBar }     from "@/components/layout/TopBar";
import { PageShell }  from "@/components/layout/PageShell";
import { EmptyState } from "@/components/shared/EmptyState";

export default function Settings() {
  return (
    <>
      <TopBar title="Settings" />
      <PageShell>
        <EmptyState
          title="Settings — Phase 7"
          description="Edit config.py settings from the browser."
        />
      </PageShell>
    </>
  );
}
