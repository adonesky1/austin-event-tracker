"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";

import { apiFetch } from "@/lib/api";
import type { AdminProfile } from "@/lib/types";

function listToText(values: string[]) {
  return values.join(", ");
}

function textToList(value: string) {
  return value
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
}

function agesToText(values: Array<{ age: number }>) {
  return values.map((item) => item.age).join(", ");
}

function textToAges(value: string) {
  return value
    .split(",")
    .map((item) => Number(item.trim()))
    .filter((item) => Number.isFinite(item))
    .map((age) => ({ age }));
}

export function PreferencesPanel() {
  const [profile, setProfile] = useState<AdminProfile | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    void apiFetch<AdminProfile>("/admin/profile")
      .then(setProfile)
      .catch((err) => setError(err instanceof Error ? err.message : "Failed to load profile"));
  }, []);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const formData = new FormData(event.currentTarget);
    setSaving(true);
    setMessage(null);
    setError(null);

    try {
      const payload = {
        email: String(formData.get("email") ?? ""),
        city: String(formData.get("city") ?? "austin"),
        budget: String(formData.get("budget") ?? "moderate"),
        crowd_sensitivity: String(formData.get("crowd_sensitivity") ?? "medium"),
        max_distance_miles: Number(formData.get("max_distance_miles") ?? 30),
        max_events_per_digest: Number(formData.get("max_events_per_digest") ?? 15),
        interests: textToList(String(formData.get("interests") ?? "")),
        dislikes: textToList(String(formData.get("dislikes") ?? "")),
        preferred_neighborhoods: textToList(
          String(formData.get("preferred_neighborhoods") ?? ""),
        ),
        preferred_days: textToList(String(formData.get("preferred_days") ?? "")),
        preferred_times: textToList(String(formData.get("preferred_times") ?? "")),
        adults: textToAges(String(formData.get("adults") ?? "")),
        children: textToAges(String(formData.get("children") ?? "")),
      };

      const updated = await apiFetch<AdminProfile>("/admin/profile", {
        method: "PATCH",
        body: JSON.stringify(payload),
      });
      setProfile(updated);
      setMessage("Preferences saved.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save preferences");
    } finally {
      setSaving(false);
    }
  }

  const formValues = useMemo(() => {
    if (!profile) return null;
    return {
      ...profile,
      interestsText: listToText(profile.interests),
      dislikesText: listToText(profile.dislikes),
      neighborhoodsText: listToText(profile.preferred_neighborhoods),
      daysText: listToText(profile.preferred_days),
      timesText: listToText(profile.preferred_times),
      adultsText: agesToText(profile.adults),
      childrenText: agesToText(profile.children),
    };
  }, [profile]);

  if (error && !profile) {
    return <div className="error-card">{error}</div>;
  }

  if (!formValues) {
    return <div className="muted-card">Loading preferences…</div>;
  }

  return (
    <form className="stack-lg" onSubmit={handleSubmit}>
      <div className="card-grid">
        <section className="info-card stack-md">
          <h2>Household basics</h2>
          <label className="field">
            <span>Email</span>
            <input defaultValue={formValues.email} name="email" type="email" />
          </label>
          <label className="field">
            <span>City</span>
            <input defaultValue={formValues.city} name="city" />
          </label>
          <label className="field">
            <span>Adults ages</span>
            <input defaultValue={formValues.adultsText} name="adults" />
          </label>
          <label className="field">
            <span>Children ages</span>
            <input defaultValue={formValues.childrenText} name="children" />
          </label>
        </section>

        <section className="info-card stack-md">
          <h2>Scoring preferences</h2>
          <label className="field">
            <span>Budget</span>
            <select defaultValue={formValues.budget} name="budget">
              <option value="free">free</option>
              <option value="low">low</option>
              <option value="moderate">moderate</option>
              <option value="any">any</option>
            </select>
          </label>
          <label className="field">
            <span>Crowd sensitivity</span>
            <select defaultValue={formValues.crowd_sensitivity} name="crowd_sensitivity">
              <option value="low">low</option>
              <option value="medium">medium</option>
              <option value="high">high</option>
            </select>
          </label>
          <label className="field">
            <span>Max distance miles</span>
            <input
              defaultValue={formValues.max_distance_miles}
              min={0}
              name="max_distance_miles"
              type="number"
            />
          </label>
          <label className="field">
            <span>Max events per digest</span>
            <input
              defaultValue={formValues.max_events_per_digest}
              min={1}
              name="max_events_per_digest"
              type="number"
            />
          </label>
        </section>
      </div>

      <div className="card-grid">
        <section className="info-card stack-md">
          <h2>Interests and dislikes</h2>
          <label className="field">
            <span>Interests</span>
            <textarea defaultValue={formValues.interestsText} name="interests" rows={5} />
          </label>
          <label className="field">
            <span>Dislikes</span>
            <textarea defaultValue={formValues.dislikesText} name="dislikes" rows={4} />
          </label>
        </section>

        <section className="info-card stack-md">
          <h2>Timing and neighborhoods</h2>
          <label className="field">
            <span>Preferred neighborhoods</span>
            <textarea
              defaultValue={formValues.neighborhoodsText}
              name="preferred_neighborhoods"
              rows={4}
            />
          </label>
          <label className="field">
            <span>Preferred days</span>
            <input defaultValue={formValues.daysText} name="preferred_days" />
          </label>
          <label className="field">
            <span>Preferred times</span>
            <input defaultValue={formValues.timesText} name="preferred_times" />
          </label>
        </section>
      </div>

      <div className="action-row">
        <button className="primary-button" disabled={saving} type="submit">
          {saving ? "Saving…" : "Save preferences"}
        </button>
        {message ? <span className="success-text">{message}</span> : null}
        {error ? <span className="error-text">{error}</span> : null}
      </div>
    </form>
  );
}
