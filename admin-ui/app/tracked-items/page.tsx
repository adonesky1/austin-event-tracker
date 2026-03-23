import { SectionShell } from "@/components/section-shell";
import { TrackedItemsPanel } from "@/components/tracked-items-panel";

export default function TrackedItemsPage() {
  return (
    <SectionShell
      title="Tracked items"
      description="Boost artists, venues, keywords, and recurring series that should surface higher."
    >
      <TrackedItemsPanel />
    </SectionShell>
  );
}
