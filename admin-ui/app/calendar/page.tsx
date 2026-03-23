import { CalendarPanel } from "@/components/calendar-panel";
import { SectionShell } from "@/components/section-shell";

export default function CalendarPage() {
  return (
    <SectionShell
      title="Google Calendar"
      description="Preview and trigger curated event syncs while keeping long diagnostics in dedicated blocks."
    >
      <CalendarPanel />
    </SectionShell>
  );
}
