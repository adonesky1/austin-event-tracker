"use client";

import { useEffect, useState } from "react";

import { apiFetch } from "@/lib/api";
import type { AdminProfile, CalendarStatus, SourceRecord } from "@/lib/types";

export function DashboardPanel() {
  const [profile, setProfile] = useState<AdminProfile | null>(null);
  const [calendar, setCalendar] = useState<CalendarStatus | null>(null);
  const [sources, setSources] = useState<SourceRecord[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      try {
        const [profileData, calendarData, sourceData] = await Promise.all([
          apiFetch<AdminProfile>("/admin/profile"),
          apiFetch<CalendarStatus>("/admin/calendar/status"),
          apiFetch<{ sources: SourceRecord[] }>("/admin/sources"),
        ]);
        setProfile(profileData);
        setCalendar(calendarData);
        setSources(sourceData.sources);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load dashboard");
      }
    }
    void load();
  }, []);

  if (error) {
    return <div className="error-card">{error}</div>;
  }

  if (!profile || !calendar) {
    return <div className="muted-card">Loading dashboard…</div>;
  }

  const healthySources = sources.filter((source) => source.status === "healthy").length;

  return (
    <div className="stack-lg">
      <div className="metric-grid">
        <div className="metric-card">
          <span className="metric-label">Interests</span>
          <strong>{profile.interests.length}</strong>
          <p>{profile.interests.join(", ") || "No interests configured yet"}</p>
        </div>
        <div className="metric-card">
          <span className="metric-label">Healthy sources</span>
          <strong>{healthySources}</strong>
          <p>{healthySources} healthy sources currently reporting</p>
        </div>
        <div className="metric-card">
          <span className="metric-label">Calendar sync</span>
          <strong>{calendar.enabled ? "Enabled" : "Disabled"}</strong>
          <p>
            {calendar.latest_run
              ? `Last run ${calendar.latest_run.status} at ${new Date(
                  calendar.latest_run.started_at,
                ).toLocaleString()}`
              : "No sync has run yet"}
          </p>
        </div>
      </div>

      <div className="card-grid">
        <article className="info-card">
          <h2>Profile snapshot</h2>
          <dl className="detail-list">
            <div>
              <dt>Email</dt>
              <dd>{profile.email}</dd>
            </div>
            <div>
              <dt>Budget</dt>
              <dd>{profile.budget}</dd>
            </div>
            <div>
              <dt>Preferred neighborhoods</dt>
              <dd>{profile.preferred_neighborhoods.join(", ") || "—"}</dd>
            </div>
          </dl>
        </article>

        <article className="info-card">
          <h2>Calendar snapshot</h2>
          <dl className="detail-list">
            <div>
              <dt>Name</dt>
              <dd>{calendar.calendar_name || "Not configured"}</dd>
            </div>
            <div>
              <dt>Threshold</dt>
              <dd>{calendar.min_score}</dd>
            </div>
            <div>
              <dt>Window</dt>
              <dd>{calendar.horizon_days} days</dd>
            </div>
          </dl>
        </article>
      </div>
    </div>
  );
}
