"use client";

import { useEffect, useState } from "react";

import { apiFetch } from "@/lib/api";
import type { JobInfo, JobScheduleUpdate } from "@/lib/types";

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

function JobRow({ job, onUpdate }: { job: JobInfo; onUpdate: (updated: JobInfo) => void }) {
  const [editing, setEditing] = useState(false);
  const [selectedDays, setSelectedDays] = useState<string[]>(
    job.day_of_week ? job.day_of_week.split(",") : [],
  );
  const [hour, setHour] = useState(job.hour);
  const [saving, setSaving] = useState(false);
  const [triggering, setTriggering] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [triggerMessage, setTriggerMessage] = useState<string | null>(null);

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
    setTriggerMessage(null);
    try {
      await apiFetch(`/admin/jobs/${job.id}/trigger`, { method: "POST" });
      setTriggerMessage("Job triggered");
      setTimeout(() => setTriggerMessage(null), 3000);
    } catch (err) {
      setTriggerMessage(err instanceof Error ? err.message : "Trigger failed");
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

      {editing ? (
        <div className="stack-sm">
          <div>
            <p className="helper-text" style={{ marginBottom: "0.5rem" }}>
              Days (leave empty for daily)
            </p>
            <div style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap" }}>
              {DAY_OPTIONS.map(({ value, label }) => (
                <label key={value} style={{ display: "flex", alignItems: "center", gap: "0.25rem", cursor: "pointer" }}>
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
          <div>
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
              style={{ marginLeft: "0.5rem", width: "4rem" }}
            />
          </div>
          {saveError && <p className="error-text">{saveError}</p>}
          <div style={{ display: "flex", gap: "0.5rem" }}>
            <button className="primary-button" onClick={handleSave} disabled={saving} type="button">
              {saving ? "Saving…" : "Save"}
            </button>
            <button className="secondary-button" onClick={() => setEditing(false)} type="button">
              Cancel
            </button>
          </div>
        </div>
      ) : (
        <div style={{ display: "flex", gap: "0.5rem", alignItems: "center" }}>
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
          {triggerMessage && <span className="helper-text">{triggerMessage}</span>}
        </div>
      )}
    </article>
  );
}

export function JobsPanel() {
  const [jobs, setJobs] = useState<JobInfo[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    void apiFetch<JobInfo[]>("/admin/jobs")
      .then(setJobs)
      .catch((err) => setError(err instanceof Error ? err.message : "Failed to load jobs"));
  }, []);

  if (error) return <div className="error-card">{error}</div>;
  if (jobs.length === 0) return <div className="muted-card">Loading jobs…</div>;

  function handleUpdate(updated: JobInfo) {
    setJobs((prev) => prev.map((j) => (j.id === updated.id ? updated : j)));
  }

  return (
    <div className="stack-md">
      {jobs.map((job) => (
        <JobRow key={job.id} job={job} onUpdate={handleUpdate} />
      ))}
    </div>
  );
}
