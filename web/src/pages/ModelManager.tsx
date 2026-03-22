// src/pages/ModelManager.tsx — Phase 5
import { TopBar }     from "@/components/layout/TopBar";
import { PageShell }  from "@/components/layout/PageShell";
import { EmptyState } from "@/components/shared/EmptyState";

export default function ModelManager() {
  return (
    <>
      <TopBar title="Model Manager" />
      <PageShell>
        <EmptyState
          title="Model Manager — Phase 5"
          description="Manage Ollama models, VRAM usage, and pre-load models."
        />
      </PageShell>
    </>
  );
}
