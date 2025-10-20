"use client";

import { useState, useEffect } from "react";
import { Header } from "@/components/layout/Header";
import { Settings, Eye, Edit2, Save, X, RefreshCw } from "lucide-react";

interface PromptTemplate {
  name: string;
  description: string;
  system_prompt: string;
  user_prompt_template: string;
  variables: string[];
  editable: boolean;
  custom?: boolean;
}

interface PromptsList {
  [key: string]: {
    name: string;
    description: string;
    editable: boolean;
    variables: string[];
  };
}

export default function PromptsPage() {
  const [prompts, setPrompts] = useState<PromptsList>({});
  const [selectedPrompt, setSelectedPrompt] = useState<string | null>(null);
  const [promptDetail, setPromptDetail] = useState<PromptTemplate | null>(null);
  const [isEditing, setIsEditing] = useState(false);
  const [editedPrompt, setEditedPrompt] = useState<PromptTemplate | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadPrompts();
  }, []);

  const loadPrompts = async () => {
    try {
      setLoading(true);
      const response = await fetch("/api/prompts");
      if (!response.ok) throw new Error("Failed to load prompts");
      const data = await response.json();
      setPrompts(data.templates);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load prompts");
    } finally {
      setLoading(false);
    }
  };

  const loadPromptDetail = async (templateName: string) => {
    try {
      const response = await fetch(`/api/prompts/${templateName}`);
      if (!response.ok) throw new Error("Failed to load prompt details");
      const data = await response.json();
      setPromptDetail(data);
      setEditedPrompt(data);
      setSelectedPrompt(templateName);
      setIsEditing(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load prompt");
    }
  };

  const savePrompt = async () => {
    if (!selectedPrompt || !editedPrompt) return;

    try {
      setSaving(true);
      const response = await fetch(`/api/prompts/${selectedPrompt}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          system_prompt: editedPrompt.system_prompt,
          user_prompt_template: editedPrompt.user_prompt_template,
          description: editedPrompt.description,
        }),
      });

      if (!response.ok) throw new Error("Failed to save prompt");

      await loadPrompts();
      await loadPromptDetail(selectedPrompt);
      setIsEditing(false);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save prompt");
    } finally {
      setSaving(false);
    }
  };

  const resetPrompts = async () => {
    if (!confirm("Are you sure you want to reset all prompts to defaults? This cannot be undone.")) {
      return;
    }

    try {
      setSaving(true);
      const response = await fetch("/api/prompts/reset", {
        method: "POST",
      });

      if (!response.ok) throw new Error("Failed to reset prompts");

      await loadPrompts();
      setSelectedPrompt(null);
      setPromptDetail(null);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to reset prompts");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="min-h-screen bg-dark-bg-primary">
      <Header title="Prompt Templates" subtitle="Configure AI Analysis Prompts" />

      <div className="border-b border-dark-border bg-dark-bg-secondary">
        <div className="container mx-auto px-6 py-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-fluent-blue-500/20">
                <Settings className="h-6 w-6 text-fluent-blue-400" />
              </div>
              <div>
                <h1 className="hero-title">Prompt Management</h1>
                <p className="text-sm text-dark-text-tertiary">
                  View and customize prompts used for RCA analysis
                </p>
              </div>
            </div>
            <button
              onClick={resetPrompts}
              disabled={saving}
              className="flex items-center gap-2 rounded-lg bg-dark-bg-tertiary px-4 py-2 text-sm font-medium text-dark-text-primary hover:bg-dark-bg-tertiary/80 disabled:opacity-50"
            >
              <RefreshCw className="h-4 w-4" />
              Reset to Defaults
            </button>
          </div>
        </div>
      </div>

      <div className="container mx-auto px-6 py-8">
        {error && (
          <div className="mb-6 rounded-lg border border-red-500/50 bg-red-500/10 p-4">
            <p className="text-sm text-red-400">{error}</p>
          </div>
        )}

        <div className="grid gap-6 lg:grid-cols-3">
          {/* Prompt List */}
          <div className="lg:col-span-1">
            <div className="rounded-lg border border-dark-border bg-dark-bg-secondary p-4">
              <h2 className="mb-4 text-lg font-semibold text-dark-text-primary">
                Available Templates
              </h2>

              {loading ? (
                <div className="text-center text-dark-text-tertiary">
                  <div className="animate-pulse">Loading...</div>
                </div>
              ) : (
                <div className="space-y-2">
                  {Object.entries(prompts).map(([key, prompt]) => (
                    <button
                      key={key}
                      onClick={() => loadPromptDetail(key)}
                      className={`w-full rounded-lg border p-3 text-left transition-all ${
                        selectedPrompt === key
                          ? "border-fluent-blue-500 bg-fluent-blue-500/10"
                          : "border-dark-border bg-dark-bg-tertiary hover:border-dark-border/50"
                      }`}
                    >
                      <div className="flex items-start justify-between">
                        <div className="flex-1">
                          <h3 className="font-medium text-dark-text-primary">
                            {prompt.name}
                          </h3>
                          <p className="mt-1 text-xs text-dark-text-tertiary">
                            {prompt.description}
                          </p>
                          <div className="mt-2 flex flex-wrap gap-1">
                            {prompt.variables.map((variable) => (
                              <span
                                key={variable}
                                className="rounded bg-dark-bg-primary px-2 py-0.5 text-xs font-mono text-fluent-blue-400"
                              >
                                {`{${variable}}`}
                              </span>
                            ))}
                          </div>
                        </div>
                        {prompt.editable && (
                          <Edit2 className="h-4 w-4 text-fluent-blue-400" />
                        )}
                      </div>
                    </button>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* Prompt Detail */}
          <div className="lg:col-span-2">
            {promptDetail ? (
              <div className="rounded-lg border border-dark-border bg-dark-bg-secondary p-6">
                <div className="mb-6 flex items-center justify-between">
                  <div>
                    <h2 className="text-xl font-semibold text-dark-text-primary">
                      {promptDetail.name}
                    </h2>
                    <p className="mt-1 text-sm text-dark-text-tertiary">
                      {promptDetail.description}
                    </p>
                  </div>
                  <div className="flex gap-2">
                    {isEditing ? (
                      <>
                        <button
                          onClick={savePrompt}
                          disabled={saving}
                          className="flex items-center gap-2 rounded-lg bg-fluent-blue-500 px-4 py-2 text-sm font-medium text-white hover:bg-fluent-blue-500/90 disabled:opacity-50"
                        >
                          <Save className="h-4 w-4" />
                          {saving ? "Saving..." : "Save"}
                        </button>
                        <button
                          onClick={() => {
                            setIsEditing(false);
                            setEditedPrompt(promptDetail);
                          }}
                          className="flex items-center gap-2 rounded-lg bg-dark-bg-tertiary px-4 py-2 text-sm font-medium text-dark-text-primary hover:bg-dark-bg-tertiary/80"
                        >
                          <X className="h-4 w-4" />
                          Cancel
                        </button>
                      </>
                    ) : (
                      promptDetail.editable && (
                        <button
                          onClick={() => setIsEditing(true)}
                          className="flex items-center gap-2 rounded-lg bg-fluent-blue-500 px-4 py-2 text-sm font-medium text-white hover:bg-fluent-blue-500/90"
                        >
                          <Edit2 className="h-4 w-4" />
                          Edit
                        </button>
                      )
                    )}
                  </div>
                </div>

                <div className="space-y-6">
                  {/* System Prompt */}
                  <div>
                    <label className="mb-2 block text-sm font-medium text-dark-text-secondary">
                      System Prompt
                    </label>
                    {isEditing ? (
                      <textarea
                        value={editedPrompt?.system_prompt || ""}
                        onChange={(e) =>
                          setEditedPrompt({
                            ...editedPrompt!,
                            system_prompt: e.target.value,
                          })
                        }
                        className="w-full rounded-lg border border-dark-border bg-dark-bg-tertiary p-3 font-mono text-sm text-dark-text-primary placeholder-dark-text-tertiary focus:border-fluent-blue-500 focus:outline-none"
                        rows={4}
                        placeholder="Enter system prompt..."
                        aria-label="System Prompt"
                      />
                    ) : (
                      <div className="rounded-lg border border-dark-border bg-dark-bg-tertiary p-4 font-mono text-sm text-dark-text-primary whitespace-pre-wrap">
                        {promptDetail.system_prompt}
                      </div>
                    )}
                  </div>

                  {/* User Prompt Template */}
                  <div>
                    <label className="mb-2 block text-sm font-medium text-dark-text-secondary">
                      User Prompt Template
                    </label>
                    {isEditing ? (
                      <textarea
                        value={editedPrompt?.user_prompt_template || ""}
                        onChange={(e) =>
                          setEditedPrompt({
                            ...editedPrompt!,
                            user_prompt_template: e.target.value,
                          })
                        }
                        className="w-full rounded-lg border border-dark-border bg-dark-bg-tertiary p-3 font-mono text-sm text-dark-text-primary placeholder-dark-text-tertiary focus:border-fluent-blue-500 focus:outline-none"
                        rows={12}
                        placeholder="Enter user prompt template..."
                        aria-label="User Prompt Template"
                      />
                    ) : (
                      <div className="rounded-lg border border-dark-border bg-dark-bg-tertiary p-4 font-mono text-sm text-dark-text-primary whitespace-pre-wrap">
                        {promptDetail.user_prompt_template}
                      </div>
                    )}
                  </div>

                  {/* Variables */}
                  <div>
                    <label className="mb-2 block text-sm font-medium text-dark-text-secondary">
                      Available Variables
                    </label>
                    <div className="flex flex-wrap gap-2">
                      {promptDetail.variables.map((variable) => (
                        <span
                          key={variable}
                          className="rounded-lg bg-fluent-blue-500/20 px-3 py-1.5 font-mono text-sm text-fluent-blue-400"
                        >
                          {`{${variable}}`}
                        </span>
                      ))}
                    </div>
                    <p className="mt-2 text-xs text-dark-text-tertiary">
                      These variables will be automatically replaced when the prompt is used
                    </p>
                  </div>
                </div>
              </div>
            ) : (
              <div className="flex h-96 items-center justify-center rounded-lg border border-dark-border bg-dark-bg-secondary">
                <div className="text-center">
                  <Eye className="mx-auto h-12 w-12 text-dark-text-tertiary" />
                  <p className="mt-4 text-dark-text-tertiary">
                    Select a template to view its details
                  </p>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
