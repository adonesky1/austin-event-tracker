import { SectionShell } from "@/components/section-shell";
import { DigestsPanel } from "@/components/digests-panel";

export default function DigestsPage() {
  return (
    <SectionShell
      title="Digest history"
      description="Browse previously sent digests and preview their full content."
    >
      <DigestsPanel />
    </SectionShell>
  );
}
