import { DashboardPanel } from "@/components/dashboard-panel";
import { SectionShell } from "@/components/section-shell";

export default function DashboardPage() {
  return (
    <SectionShell
      title="Dashboard"
      description="Quick visibility into the profile, sources, and Google Calendar sync state."
    >
      <DashboardPanel />
    </SectionShell>
  );
}
