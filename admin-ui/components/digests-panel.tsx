"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { apiFetch } from "@/lib/api";
import type { DigestSummary } from "@/lib/types";

function StatusBadge({ status }: { status: string }) {
  const className =
    status === "sent"
      ? "status-pill status-ok"
      : status === "failed"
        ? "status-pill status-error"
        : "status-pill status-warn";
  return <span className={className}>{status}</span>;
}

function formatDate(iso: string | null): string {
  if (!iso) return "—";
  return new Date(iso).toLocaleString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

export function DigestsPanel() {
  const [digests, setDigests] = useState<DigestSummary[]>([]);
  const [total, setTotal] = useState(0);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    void apiFetch<{ digests: DigestSummary[]; total: number }>("/admin/digests")
      .then((result) => {
        setDigests(result.digests);
        setTotal(result.total);
      })
      .catch((err) => setError(err instanceof Error ? err.message : "Failed to load digests"));
  }, []);

  if (error) return <div className="error-card">{error}</div>;

  if (digests.length === 0 && total === 0) {
    return <div className="muted-card">No digests sent yet.</div>;
  }

  return (
    <div className="stack-md">
      {digests.map((digest) => (
        <Link
          key={digest.id}
          href={`/digests/${digest.id}`}
          style={{ textDecoration: "none", color: "inherit" }}
        >
          <article className="info-card stack-sm" style={{ cursor: "pointer" }}>
            <div className="split-header">
              <div>
                <h2>{digest.subject}</h2>
                <p className="helper-text">{formatDate(digest.sent_at)}</p>
              </div>
              <StatusBadge status={digest.status} />
            </div>
            <div className="detail-row">
              <span>Events</span>
              <strong>{digest.event_count}</strong>
            </div>
            <div className="detail-row">
              <span>Window</span>
              <strong>
                {digest.window_start} → {digest.window_end}
              </strong>
            </div>
          </article>
        </Link>
      ))}
    </div>
  );
}
