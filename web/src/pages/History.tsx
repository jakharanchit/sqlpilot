// src/pages/History.tsx — Phase 3
import { TopBar }     from "@/components/layout/TopBar";
import { PageShell }  from "@/components/layout/PageShell";
import { EmptyState } from "@/components/shared/EmptyState";

export default function History() {
  return (
    <>
      <TopBar title="History & Trends" />
      <PageShell>
        <EmptyState
          title="History & Trends — Phase 3"
          description="Browse run history, trend charts, and side-by-side comparisons."
        />
      </PageShell>
    </>
  );
}
