import { SectionShell } from "@/components/section-shell";
import { JobsPanel } from "@/components/jobs-panel";

export default function JobsPage() {
  return (
    <SectionShell
      title="Scheduled jobs"
      description="View and edit cron schedules, or trigger jobs manually."
    >
      <JobsPanel />
    </SectionShell>
  );
}
