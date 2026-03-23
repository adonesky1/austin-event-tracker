import { SectionShell } from "@/components/section-shell";
import { SourcesPanel } from "@/components/sources-panel";

export default function SourcesPage() {
  return (
    <SectionShell
      title="Sources"
      description="Inspect source status and current enablement. Source persistence can be added next."
    >
      <SourcesPanel />
    </SectionShell>
  );
}
