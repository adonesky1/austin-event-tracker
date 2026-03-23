"use client";

import { FormEvent, useEffect, useState } from "react";

import { apiFetch } from "@/lib/api";
import type { PromptConfig } from "@/lib/types";

export function PromptsPanel() {
  const [prompt, setPrompt] = useState<PromptConfig | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  async function load() {
    try {
      const data = await apiFetch<PromptConfig>("/admin/prompts/synthesis");
      setPrompt(data);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load prompts");
    }
  }

  useEffect(() => {
    void load();
  }, []);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const formData = new FormData(event.currentTarget);
    setSaving(true);
    setMessage(null);
    setError(null);
    try {
      const updated = await apiFetch<PromptConfig>("/admin/prompts/synthesis", {
        method: "PUT",
        body: JSON.stringify({
          system_prompt: String(formData.get("system_prompt") ?? ""),
          user_prompt_template: String(formData.get("user_prompt_template") ?? ""),
        }),
      });
      setPrompt(updated);
      setMessage("Prompt configuration saved.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save prompts");
    } finally {
      setSaving(false);
    }
  }

  async function handleReset() {
    setSaving(true);
    setMessage(null);
    setError(null);
    try {
      const reset = await apiFetch<PromptConfig>("/admin/prompts/synthesis/reset", {
        method: "POST",
      });
      setPrompt(reset);
      setMessage("Prompt reset to defaults.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to reset prompt");
    } finally {
      setSaving(false);
    }
  }

  if (error && !prompt) {
    return <div className="error-card">{error}</div>;
  }

  if (!prompt) {
    return <div className="muted-card">Loading prompts…</div>;
  }

  return (
    <form className="stack-lg" onSubmit={handleSubmit}>
      <div className="card-grid">
        <section className="info-card stack-md">
          <div className="split-header">
            <div>
              <h2>Synthesis system prompt</h2>
              <p className="helper-text">
                {prompt.is_default ? "Using default prompt from code." : "Using DB override."}
              </p>
            </div>
          </div>
          <label className="field">
            <span>System prompt</span>
            <textarea
              className="code-textarea"
              defaultValue={prompt.system_prompt}
              name="system_prompt"
              rows={16}
            />
          </label>
        </section>

        <section className="info-card stack-md">
          <h2>User prompt template</h2>
          <label className="field">
            <span>User template</span>
            <textarea
              className="code-textarea"
              defaultValue={prompt.user_prompt_template}
              name="user_prompt_template"
              rows={16}
            />
          </label>
        </section>
      </div>

      <div className="action-row">
        <button className="primary-button" disabled={saving} type="submit">
          {saving ? "Saving…" : "Save prompt"}
        </button>
        <button
          className="secondary-button"
          disabled={saving}
          onClick={handleReset}
          type="button"
        >
          Reset to code default
        </button>
        {message ? <span className="success-text">{message}</span> : null}
        {error ? <span className="error-text">{error}</span> : null}
      </div>
    </form>
  );
}
