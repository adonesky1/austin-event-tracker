"use client";

import { FormEvent, useEffect, useState } from "react";

import { apiFetch } from "@/lib/api";
import type { TrackedItem } from "@/lib/types";

type Draft = {
  label: string;
  kind: TrackedItem["kind"];
  enabled: boolean;
  boost_weight: number;
  notes: string;
};

const EMPTY_DRAFT: Draft = {
  label: "",
  kind: "artist",
  enabled: true,
  boost_weight: 0.15,
  notes: "",
};

export function TrackedItemsPanel() {
  const [items, setItems] = useState<TrackedItem[]>([]);
  const [draft, setDraft] = useState<Draft>(EMPTY_DRAFT);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function load() {
    try {
      const data = await apiFetch<TrackedItem[]>("/admin/tracked-items");
      setItems(data);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load tracked items");
    }
  }

  useEffect(() => {
    void load();
  }, []);

  async function createItem(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    try {
      const created = await apiFetch<TrackedItem>("/admin/tracked-items", {
        method: "POST",
        body: JSON.stringify(draft),
      });
      setItems((current) => [...current, created]);
      setDraft(EMPTY_DRAFT);
      setMessage("Tracked item added.");
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to add tracked item");
    }
  }

  async function saveItem(item: TrackedItem) {
    try {
      const updated = await apiFetch<TrackedItem>(`/admin/tracked-items/${item.id}`, {
        method: "PATCH",
        body: JSON.stringify(item),
      });
      setItems((current) => current.map((entry) => (entry.id === item.id ? updated : entry)));
      setMessage(`Updated ${updated.label}.`);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to update tracked item");
    }
  }

  async function removeItem(itemId: string) {
    try {
      await apiFetch(`/admin/tracked-items/${itemId}`, { method: "DELETE" });
      setItems((current) => current.filter((item) => item.id !== itemId));
      setMessage("Tracked item removed.");
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to remove tracked item");
    }
  }

  return (
    <div className="stack-lg">
      <form className="info-card stack-md" onSubmit={createItem}>
        <h2>Add tracked item</h2>
        <div className="compact-grid">
          <label className="field">
            <span>Label</span>
            <input
              onChange={(event) => setDraft((current) => ({ ...current, label: event.target.value }))}
              value={draft.label}
            />
          </label>
          <label className="field">
            <span>Kind</span>
            <select
              onChange={(event) =>
                setDraft((current) => ({
                  ...current,
                  kind: event.target.value as Draft["kind"],
                }))
              }
              value={draft.kind}
            >
              <option value="artist">artist</option>
              <option value="venue">venue</option>
              <option value="keyword">keyword</option>
              <option value="series">series</option>
            </select>
          </label>
          <label className="field">
            <span>Boost weight</span>
            <input
              min={0}
              onChange={(event) =>
                setDraft((current) => ({
                  ...current,
                  boost_weight: Number(event.target.value),
                }))
              }
              step="0.01"
              type="number"
              value={draft.boost_weight}
            />
          </label>
          <label className="field checkbox-field">
            <input
              checked={draft.enabled}
              onChange={(event) =>
                setDraft((current) => ({ ...current, enabled: event.target.checked }))
              }
              type="checkbox"
            />
            <span>Enabled</span>
          </label>
        </div>
        <label className="field">
          <span>Notes</span>
          <textarea
            onChange={(event) => setDraft((current) => ({ ...current, notes: event.target.value }))}
            rows={3}
            value={draft.notes}
          />
        </label>
        <div className="action-row">
          <button className="primary-button" type="submit">
            Add tracked item
          </button>
        </div>
      </form>

      {message ? <div className="success-banner">{message}</div> : null}
      {error ? <div className="error-card">{error}</div> : null}

      <div className="stack-md">
        {items.length === 0 ? (
          <div className="muted-card">No tracked items yet.</div>
        ) : (
          items.map((item) => (
            <TrackedItemCard
              item={item}
              key={item.id}
              onDelete={removeItem}
              onSave={saveItem}
            />
          ))
        )}
      </div>
    </div>
  );
}

function TrackedItemCard({
  item,
  onSave,
  onDelete,
}: {
  item: TrackedItem;
  onSave: (item: TrackedItem) => Promise<void>;
  onDelete: (itemId: string) => Promise<void>;
}) {
  const [draft, setDraft] = useState<TrackedItem>(item);

  useEffect(() => {
    setDraft(item);
  }, [item]);

  return (
    <article className="info-card stack-md">
      <div className="split-header">
        <div>
          <h2>{item.label}</h2>
          <p className="helper-text">
            {item.kind} · boost {item.boost_weight.toFixed(2)}
          </p>
        </div>
        <span className={item.enabled ? "status-pill status-ok" : "status-pill status-muted"}>
          {item.enabled ? "Enabled" : "Disabled"}
        </span>
      </div>

      <div className="compact-grid">
        <label className="field">
          <span>Label</span>
          <input
            onChange={(event) => setDraft((current) => ({ ...current, label: event.target.value }))}
            value={draft.label}
          />
        </label>
        <label className="field">
          <span>Kind</span>
          <select
            onChange={(event) =>
              setDraft((current) => ({
                ...current,
                kind: event.target.value as TrackedItem["kind"],
              }))
            }
            value={draft.kind}
          >
            <option value="artist">artist</option>
            <option value="venue">venue</option>
            <option value="keyword">keyword</option>
            <option value="series">series</option>
          </select>
        </label>
        <label className="field">
          <span>Boost weight</span>
          <input
            min={0}
            onChange={(event) =>
              setDraft((current) => ({
                ...current,
                boost_weight: Number(event.target.value),
              }))
            }
            step="0.01"
            type="number"
            value={draft.boost_weight}
          />
        </label>
        <label className="field checkbox-field">
          <input
            checked={draft.enabled}
            onChange={(event) =>
              setDraft((current) => ({ ...current, enabled: event.target.checked }))
            }
            type="checkbox"
          />
          <span>Enabled</span>
        </label>
      </div>

      <label className="field">
        <span>Notes</span>
        <textarea
          onChange={(event) => setDraft((current) => ({ ...current, notes: event.target.value }))}
          rows={3}
          value={draft.notes ?? ""}
        />
      </label>

      <div className="action-row">
        <button className="primary-button" onClick={() => void onSave(draft)} type="button">
          Save
        </button>
        <button
          className="danger-button"
          onClick={() => void onDelete(draft.id)}
          type="button"
        >
          Delete
        </button>
      </div>
    </article>
  );
}
