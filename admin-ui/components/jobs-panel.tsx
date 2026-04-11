"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import { apiFetch } from "@/lib/api";
import type { JobInfo, JobRunInfo, JobScheduleUpdate } from "@/lib/types";

const DAY_OPTIONS = [
  { value: "mon", label: "Mon" },
  { value: "tue", label: "Tue" },
  { value: "wed", label: "Wed" },
  { value: "thu", label: "Thu" },
  { value: "fri", label: "Fri" },
  { value: "sat", label: "Sat" },
  { value: "sun", label: "Sun" },
];

function formatSchedule(job: JobInfo): string {
  const hour = job.hour;
  const ampm = hour < 12 ? "AM" : "PM";
  const displayHour = hour % 12 === 0 ? 12 : hour % 12;
  const timeStr = `${displayHour}:00 ${ampm} CT`;
  if (!job.day_of_week) return `Daily at ${timeStr}`;
  const days = job.day_of_week
    .split(",")
    .map((d) => d.charAt(0).toUpperCase() + d.slice(1))
    .join(", ");
  return `${days} at ${timeStr}`;
}

function formatNextRun(nextRun: string | null): string {
  if (!nextRun) return "—";
  const date = new Date(nextRun);
  const now = new Date();
  const diff = date.getTime() - now.getTime();
  const hours = Math.floor(diff / 3_600_000);
  const days = Math.floor(hours / 24);
  if (days > 0) return `in ${days}d ${hours % 24}h`;
  if (hours > 0) return `in ${hours}h`;
  const mins = Math.floor(diff / 60_000);
  return mins > 0 ? `in ${mins}m` : "soon";
}

function formatTimestamp(value: string | null): string {
  if (!value) return "—";
  return new Date(value).toLocaleString();
}

function formatRuntimeLabel(status: JobInfo["runtime"]["status"]): string {
  switch (status) {
    case "queued":
      return "Queued";
    case "running":
      return "Running";
    case "success":
      return "Succeeded";
    case "warning":
      return "Completed with warnings";
    case "failed":
      return "Failed";
    case "skipped":
      return "Skipped";
    default:
      return "Idle";
  }
}

function statusClassName(status: JobInfo["runtime"]["status"]): string {
  switch (status) {
    case "success":
      return "status-ok";
    case "warning":
    case "skipped":
      return "status-warn";
    case "failed":
      return "status-danger";
    case "queued":
    case "running":
      return "status-active";
    default:
      return "status-muted";
  }
}

function getSourceResults(job: JobInfo): Array<[string, Record<string, unknown>]> {
  const sourceResults = job.runtime.details?.source_results;
  if (!sourceResults || typeof sourceResults !== "object" || Array.isArray(sourceResults)) {
    return [];
  }

  return Object.entries(sourceResults).filter(
    (entry): entry is [string, Record<string, unknown>] =>
      !!entry[1] && typeof entry[1] === "object" && !Array.isArray(entry[1]),
  );
}

function hasFailures(job: JobInfo): boolean {
  return (
    job.runtime.status === "failed" ||
    job.recent_runs.some((run) => run.status === "failed")
  );
}

function sortRunsNewestFirst(runs: JobRunInfo[]): JobRunInfo[] {
  return [...runs].sort((a, b) => {
    const aTime = new Date(a.completed_at ?? a.started_at ?? a.created_at ?? 0).getTime();
    const bTime = new Date(b.completed_at ?? b.started_at ?? b.created_at ?? 0).getTime();
    return bTime - aTime;
  });
}

function TracebackDetails({
  traceback,
  label = "View traceback",
}: {
  traceback: string | null;
  label?: string;
}) {
  if (!traceback) return null;

  return (
    <details className="traceback-panel">
      <summary>{label}</summary>
      <pre>{traceback}</pre>
    </details>
  );
}

function JobRow({ job, onUpdate }: { job: JobInfo; onUpdate: (updated: JobInfo) => void }) {
  const [editing, setEditing] = useState(false);
  const [selectedDays, setSelectedDays] = useState<string[]>(
    job.day_of_week ? job.day_of_week.split(",") : [],
  );
  const [hour, setHour] = useState(job.hour);
  const [saving, setSaving] = useState(false);
  const [triggering, setTriggering] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [triggerError, setTriggerError] = useState<string | null>(null);
  const sourceResults = useMemo(() => getSourceResults(job), [job]);
  const historicalSourceResults = useMemo(() => {
    const latestDetails = job.recent_runs[0]?.details;
    if (sourceResults.length > 0 || !latestDetails) {
      return sourceResults;
    }

    const fallbackJob = {
      ...job,
      runtime: {
        ...job.runtime,
        details: latestDetails,
      },
    };
    return getSourceResults(fallbackJob);
  }, [job, sourceResults]);

  useEffect(() => {
    if (!editing) {
      setSelectedDays(job.day_of_week ? job.day_of_week.split(",") : []);
      setHour(job.hour);
    }
  }, [editing, job.day_of_week, job.hour]);

  function toggleDay(day: string) {
    setSelectedDays((prev) =>
      prev.includes(day) ? prev.filter((d) => d !== day) : [...prev, day],
    );
  }

  async function handleSave() {
    setSaving(true);
    setSaveError(null);
    try {
      const payload: JobScheduleUpdate = {
        day_of_week: selectedDays.length > 0 ? selectedDays.join(",") : null,
        hour,
      };
      const updated = await apiFetch<JobInfo>(`/admin/jobs/${job.id}/schedule`, {
        method: "PUT",
        body: JSON.stringify(payload),
      });
      onUpdate(updated);
      setEditing(false);
    } catch (err) {
      setSaveError(err instanceof Error ? err.message : "Save failed");
    } finally {
      setSaving(false);
    }
  }

  async function handleTrigger() {
    setTriggering(true);
    setTriggerError(null);
    try {
      const updated = await apiFetch<JobInfo>(`/admin/jobs/${job.id}/trigger`, { method: "POST" });
      onUpdate(updated);
    } catch (err) {
      setTriggerError(err instanceof Error ? err.message : "Trigger failed");
    } finally {
      setTriggering(false);
    }
  }

  return (
    <article className="info-card stack-sm">
      <div className="split-header">
        <div>
          <h2>{job.name}</h2>
          <p className="helper-text">{formatSchedule(job)}</p>
        </div>
        <span className="helper-text">Next: {formatNextRun(job.next_run)}</span>
      </div>

      <div className="job-status-row">
        <span className={`status-pill ${statusClassName(job.runtime.status)}`}>
          {formatRuntimeLabel(job.runtime.status)}
        </span>
        <span className="helper-text">
          {job.runtime.trigger
            ? `Last trigger: ${job.runtime.trigger}`
            : "No runs recorded yet"}
        </span>
      </div>

      {(job.runtime.summary || job.runtime.started_at || job.runtime.completed_at) && (
        <section className="job-runtime-panel stack-sm">
          {job.runtime.summary ? (
            <p className="job-runtime-summary">{job.runtime.summary}</p>
          ) : null}
          <dl className="job-runtime-grid">
            <div>
              <dt>Started</dt>
              <dd>{formatTimestamp(job.runtime.started_at)}</dd>
            </div>
            <div>
              <dt>Finished</dt>
              <dd>{formatTimestamp(job.runtime.completed_at)}</dd>
            </div>
          </dl>

          {historicalSourceResults.length > 0 ? (
            <div className="job-source-results">
              <p className="helper-text" style={{ marginTop: 0 }}>
                Source results
              </p>
              <div className="job-source-list">
                {historicalSourceResults.map(([sourceName, result]) => {
                  const status = typeof result.status === "string" ? result.status : "unknown";
                  const count = typeof result.count === "number" ? result.count : null;
                  const error = typeof result.error === "string" ? result.error : null;
                  return (
                    <div className="job-source-item" key={sourceName}>
                      <div className="stack-sm" style={{ gap: "0.25rem" }}>
                        <strong>{sourceName}</strong>
                        {error ? <span className="error-text">{error}</span> : null}
                      </div>
                      <div className="job-source-meta">
                        <span className={`status-pill ${status === "error" ? "status-danger" : "status-ok"}`}>
                          {status}
                        </span>
                        {count !== null ? <span className="helper-text">{count} events</span> : null}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          ) : null}
        </section>
      )}

      {job.runtime.error ? <div className="error-card">{job.runtime.error}</div> : null}
      {job.runtime.traceback ? <TracebackDetails traceback={job.runtime.traceback} /> : null}
      {triggerError ? <div className="error-card">{triggerError}</div> : null}

      {job.recent_runs.length > 0 ? (
        <section className="job-history-panel stack-sm">
          <div className="split-header">
            <div>
              <h3 className="job-section-title">Recent runs</h3>
              <p className="helper-text">Persisted history survives backend restarts.</p>
            </div>
          </div>
          <div className="job-history-list">
            {job.recent_runs.map((run) => (
              <div className="job-history-item" key={run.id}>
                <div className="job-history-topline">
                  <span className={`status-pill ${statusClassName(run.status as JobInfo["runtime"]["status"])}`}>
                    {formatRuntimeLabel(run.status as JobInfo["runtime"]["status"])}
                  </span>
                  <span className="helper-text">
                    {run.completed_at
                      ? formatTimestamp(run.completed_at)
                      : run.started_at
                        ? formatTimestamp(run.started_at)
                        : "Pending"}
                  </span>
                </div>
                <p className="job-history-summary">
                  {run.summary || run.error || "No summary recorded."}
                </p>
                <div className="job-history-meta">
                  <span className="helper-text">Trigger: {run.trigger}</span>
                  {run.error ? <span className="error-text">{run.error}</span> : null}
                </div>
                <TracebackDetails traceback={run.traceback} />
              </div>
            ))}
          </div>
        </section>
      ) : null}

      {editing ? (
        <div className="stack-sm">
          <div className="field">
            <p className="helper-text" style={{ marginBottom: "0.5rem" }}>
              Days (leave empty for daily)
            </p>
            <div className="job-day-picker">
              {DAY_OPTIONS.map(({ value, label }) => (
                <label className="job-day-option" key={value}>
                  <input
                    type="checkbox"
                    checked={selectedDays.includes(value)}
                    onChange={() => toggleDay(value)}
                  />
                  {label}
                </label>
              ))}
            </div>
          </div>
          <div className="field job-hour-field">
            <label className="helper-text" htmlFor={`hour-${job.id}`}>
              Hour (0–23, CT)
            </label>
            <input
              id={`hour-${job.id}`}
              type="number"
              min={0}
              max={23}
              value={hour}
              onChange={(e) => setHour(Number(e.target.value))}
            />
          </div>
          {saveError && <p className="error-text">{saveError}</p>}
          <div className="action-row">
            <button className="primary-button" onClick={handleSave} disabled={saving} type="button">
              {saving ? "Saving…" : "Save"}
            </button>
            <button className="secondary-button" onClick={() => setEditing(false)} type="button">
              Cancel
            </button>
          </div>
        </div>
      ) : (
        <div className="job-actions">
          <button className="secondary-button" onClick={() => setEditing(true)} type="button">
            Edit schedule
          </button>
          <button
            className="secondary-button"
            onClick={handleTrigger}
            disabled={triggering}
            type="button"
          >
            {triggering ? "Triggering…" : "Run now"}
          </button>
        </div>
      )}
    </article>
  );
}

export function JobsPanel() {
  const [jobs, setJobs] = useState<JobInfo[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [showFailuresOnly, setShowFailuresOnly] = useState(false);

  const loadJobs = useCallback(async () => {
    try {
      const result = await apiFetch<JobInfo[]>("/admin/jobs");
      setJobs(result);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load jobs");
    }
  }, []);

  useEffect(() => {
    void loadJobs();
    const interval = window.setInterval(() => {
      void loadJobs();
    }, 4000);
    return () => window.clearInterval(interval);
  }, [loadJobs]);

  if (error) return <div className="error-card">{error}</div>;
  if (jobs.length === 0) return <div className="muted-card">Loading jobs…</div>;

  const visibleJobs = showFailuresOnly ? jobs.filter(hasFailures) : jobs;
  const recentFailures = sortRunsNewestFirst(
    jobs.flatMap((job) => job.recent_runs.filter((run) => run.status === "failed")),
  ).slice(0, 8);

  function handleUpdate(updated: JobInfo) {
    setJobs((prev) => prev.map((j) => (j.id === updated.id ? updated : j)));
  }

  return (
    <div className="stack-md">
      <section className="info-card stack-sm">
        <div className="split-header">
          <div>
            <h2>Run history</h2>
            <p className="helper-text">
              Persisted job runs and errors are stored in the database for debugging.
            </p>
          </div>
          <label className="job-filter-toggle">
            <input
              type="checkbox"
              checked={showFailuresOnly}
              onChange={(event) => setShowFailuresOnly(event.target.checked)}
            />
            <span>Show jobs with failures only</span>
          </label>
        </div>

        {recentFailures.length > 0 ? (
          <div className="job-failures-list">
            {recentFailures.map((run) => (
              <div className="job-failure-item" key={run.id}>
                <div className="job-history-topline">
                  <strong>{run.job_name}</strong>
                  <span className="helper-text">
                    {run.completed_at
                      ? formatTimestamp(run.completed_at)
                      : formatTimestamp(run.started_at)}
                  </span>
                </div>
                <p className="job-history-summary">{run.error || run.summary || "Run failed."}</p>
                <div className="job-history-meta">
                  <span className="helper-text">Trigger: {run.trigger}</span>
                  <span className="status-pill status-danger">Failed</span>
                </div>
                <TracebackDetails traceback={run.traceback} />
              </div>
            ))}
          </div>
        ) : (
          <div className="muted-card">No persisted job failures yet.</div>
        )}
      </section>

      {visibleJobs.length === 0 ? (
        <div className="muted-card">No jobs match the current filter.</div>
      ) : null}

      {visibleJobs.map((job) => (
        <JobRow key={job.id} job={job} onUpdate={handleUpdate} />
      ))}
    </div>
  );
}
