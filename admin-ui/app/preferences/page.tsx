import { PreferencesPanel } from "@/components/preferences-panel";
import { SectionShell } from "@/components/section-shell";

export default function PreferencesPage() {
  return (
    <SectionShell
      title="Preferences"
      description="Edit the single family profile used by curation, ranking, and digest generation."
    >
      <PreferencesPanel />
    </SectionShell>
  );
}
