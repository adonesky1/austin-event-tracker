import { DigestDetailPanel } from "@/components/digest-detail-panel";
import { SectionShell } from "@/components/section-shell";

export default function DigestDetailPage({ params }: { params: { id: string } }) {
  return (
    <SectionShell title="Digest" description="Full content of this digest.">
      <DigestDetailPanel id={params.id} />
    </SectionShell>
  );
}
