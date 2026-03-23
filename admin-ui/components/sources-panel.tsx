"use client";

import { useEffect, useState } from "react";

import { apiFetch } from "@/lib/api";
import type { SourceRecord } from "@/lib/types";

export function SourcesPanel() {
  const [sources, setSources] = useState<SourceRecord[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    void apiFetch<{ sources: SourceRecord[] }>("/admin/sources")
      .then((result) => setSources(result.sources))
      .catch((err) => setError(err instanceof Error ? err.message : "Failed to load sources"));
  }, []);

  if (error) {
    return <div className="error-card">{error}</div>;
  }

  if (sources.length === 0) {
    return <div className="muted-card">Loading sources…</div>;
  }

  return (
    <div className="stack-md">
      <div className="muted-card">
        Source toggles are still informational in v1. The backend endpoint exists, but persistence is
        not wired yet.
      </div>
      <div className="card-grid">
        {sources.map((source) => (
          <article className="info-card stack-sm" key={source.name}>
            <div className="split-header">
              <div>
                <h2>{source.name}</h2>
                <p className="helper-text">{source.type}</p>
              </div>
              <span
                className={
                  source.status === "healthy"
                    ? "status-pill status-ok"
                    : "status-pill status-warn"
                }
              >
                {source.status}
              </span>
            </div>
            <div className="detail-row">
              <span>Enabled</span>
              <strong>{source.enabled ? "Yes" : "No"}</strong>
            </div>
            <button className="secondary-button" disabled type="button">
              Toggle coming soon
            </button>
          </article>
        ))}
      </div>
    </div>
  );
}
