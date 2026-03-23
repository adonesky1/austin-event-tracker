import { PromptsPanel } from "@/components/prompts-panel";
import { SectionShell } from "@/components/section-shell";

export default function PromptsPage() {
  return (
    <SectionShell
      title="Prompts"
      description="Override the synthesis prompts without redeploying the backend."
    >
      <PromptsPanel />
    </SectionShell>
  );
}
