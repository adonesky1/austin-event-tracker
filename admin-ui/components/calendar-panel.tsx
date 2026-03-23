"use client";

import { useEffect, useState } from "react";

import { apiFetch } from "@/lib/api";
import type { CalendarPreview, CalendarStatus } from "@/lib/types";

export function CalendarPanel() {
  const [status, setStatus] = useState<CalendarStatus | null>(null);
  const [preview, setPreview] = useState<CalendarPreview | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function loadStatus() {
    try {
      const nextStatus = await apiFetch<CalendarStatus>("/admin/calendar/status");
      setStatus(nextStatus);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load calendar status");
    }
  }

  useEffect(() => {
    void loadStatus();
  }, []);

  async function runPreview() {
    setBusy(true);
    try {
      const result = await apiFetch<CalendarPreview>("/admin/calendar/preview");
      setPreview(result);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Preview failed");
    } finally {
      setBusy(false);
    }
  }

  async function runSync() {
    setBusy(true);
    try {
      const result = await apiFetch<CalendarPreview>("/admin/calendar/sync", {
        method: "POST",
      });
      setPreview(result);
      await loadStatus();
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Sync failed");
    } finally {
      setBusy(false);
    }
  }

  if (!status && error) {
    return <div className="error-card">{error}</div>;
  }

  if (!status) {
    return <div className="muted-card">Loading calendar status…</div>;
  }

  return (
    <div className="stack-lg">
      <div className="card-grid">
        <article className="info-card stack-md">
          <h2>Calendar configuration</h2>
          <dl className="detail-list">
            <div>
              <dt>Enabled</dt>
              <dd>{status.enabled ? "Yes" : "No"}</dd>
            </div>
            <div>
              <dt>Name</dt>
              <dd>{status.calendar_name || "—"}</dd>
            </div>
            <div>
              <dt>Threshold</dt>
              <dd>{status.min_score}</dd>
            </div>
            <div>
              <dt>Window</dt>
              <dd>{status.horizon_days} days</dd>
            </div>
          </dl>
        </article>

        <article className="info-card stack-md">
          <h2>Latest run</h2>
          {status.latest_run ? (
            <dl className="detail-list">
              <div>
                <dt>Status</dt>
                <dd>{status.latest_run.status}</dd>
              </div>
              <div>
                <dt>Started</dt>
                <dd>{new Date(status.latest_run.started_at).toLocaleString()}</dd>
              </div>
              <div>
                <dt>Counts</dt>
                <dd>
                  {status.latest_run.created_count} created · {status.latest_run.updated_count} updated
                  · {status.latest_run.deleted_count} deleted
                </dd>
              </div>
            </dl>
          ) : (
            <p className="helper-text">No sync has been recorded yet.</p>
          )}
        </article>
      </div>

      <div className="action-row">
        <button className="secondary-button" disabled={busy} onClick={() => void runPreview()} type="button">
          {busy ? "Working…" : "Preview next sync"}
        </button>
        <button className="primary-button" disabled={busy} onClick={() => void runSync()} type="button">
          Run manual sync
        </button>
      </div>

      {error ? <div className="error-card">{error}</div> : null}

      {preview ? (
        <article className="info-card stack-md">
          <h2>Latest preview/result</h2>
          <div className="metric-grid">
            <div className="metric-card">
              <span className="metric-label">Selected</span>
              <strong>{preview.selected_count}</strong>
            </div>
            <div className="metric-card">
              <span className="metric-label">Create</span>
              <strong>{preview.created_count}</strong>
            </div>
            <div className="metric-card">
              <span className="metric-label">Update</span>
              <strong>{preview.updated_count}</strong>
            </div>
            <div className="metric-card">
              <span className="metric-label">Delete</span>
              <strong>{preview.deleted_count}</strong>
            </div>
          </div>
          <div className="stack-sm">
            {preview.selected_events.slice(0, 10).map((item) => (
              <div className="detail-row" key={item.id}>
                <span>{item.title}</span>
                <strong>{item.score.toFixed(2)}</strong>
              </div>
            ))}
          </div>
        </article>
      ) : null}
    </div>
  );
}
