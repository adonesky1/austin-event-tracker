"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { apiFetch } from "@/lib/api";
import type { DigestDetail } from "@/lib/types";

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

export function DigestDetailPanel({ id }: { id: string }) {
  const [digest, setDigest] = useState<DigestDetail | null>(null);
  const [tab, setTab] = useState<"preview" | "plaintext">("preview");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    void apiFetch<DigestDetail>(`/admin/digests/${id}`)
      .then(setDigest)
      .catch((err) => setError(err instanceof Error ? err.message : "Failed to load digest"));
  }, [id]);

  if (error) return <div className="error-card">{error}</div>;
  if (!digest) return <div className="muted-card">Loading…</div>;

  return (
    <div className="stack-md">
      <Link href="/digests" className="helper-text" style={{ textDecoration: "none" }}>
        ← Back to digests
      </Link>

      <div className="info-card stack-sm">
        <h2>{digest.subject}</h2>
        <div className="detail-row">
          <span>Sent</span>
          <strong>{formatDate(digest.sent_at)}</strong>
        </div>
        <div className="detail-row">
          <span>Status</span>
          <strong>{digest.status}</strong>
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
      </div>

      <div style={{ display: "flex", gap: "0.5rem" }}>
        <button
          className={tab === "preview" ? "primary-button" : "secondary-button"}
          onClick={() => setTab("preview")}
          type="button"
        >
          Preview
        </button>
        <button
          className={tab === "plaintext" ? "primary-button" : "secondary-button"}
          onClick={() => setTab("plaintext")}
          type="button"
        >
          Plain text
        </button>
      </div>

      {tab === "preview" ? (
        <iframe
          srcDoc={digest.html_content}
          style={{ width: "100%", height: "600px", border: "1px solid var(--border)", borderRadius: "var(--radius)" }}
          title="Digest preview"
          sandbox="allow-same-origin"
        />
      ) : (
        <pre
          style={{
            whiteSpace: "pre-wrap",
            fontFamily: "monospace",
            fontSize: "0.85rem",
            background: "var(--surface-2)",
            padding: "1rem",
            borderRadius: "var(--radius)",
            overflowX: "auto",
          }}
        >
          {digest.plaintext_content}
        </pre>
      )}
    </div>
  );
}
