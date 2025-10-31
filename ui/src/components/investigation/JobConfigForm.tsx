"use client";

import { useState, useEffect } from "react";
import { Card } from "@/components/ui";
import Link from "next/link";
import { Eye } from "lucide-react";

interface JobConfig {
  job_type: string;
  provider: string;
  model: string;
  priority: number;
  file_ids?: string[];
  prompt_template?: string;
}

interface JobConfigFormProps {
  fileIds: string[];
  onSubmit: (jobId: string) => void;
  disabled?: boolean;
}

interface PromptTemplate {
  name: string;
  description: string;
}

export function JobConfigForm({ fileIds, onSubmit, disabled = false }: JobConfigFormProps) {
  const [config, setConfig] = useState<JobConfig>({
    job_type: "rca_analysis",
    provider: "copilot",
    model: "gpt-4",
    priority: 5,
    prompt_template: "rca_analysis",
  });
  const [promptTemplates, setPromptTemplates] = useState<Record<string, PromptTemplate>>({});
  const [loadingPrompts, setLoadingPrompts] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const authToken = process.env.NEXT_PUBLIC_API_AUTH_TOKEN;

  // Load available prompt templates
  useEffect(() => {
    const loadPrompts = async () => {
      try {
        const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8001";
        const response = await fetch(`${apiBaseUrl}/api/v1/prompts`);
        if (response.ok) {
          const data = await response.json();
          setPromptTemplates(data.templates || {});
        }
      } catch (err) {
        console.error("Failed to load prompt templates:", err);
      } finally {
        setLoadingPrompts(false);
      }
    };
    loadPrompts();
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setIsSubmitting(true);

    try {
      const payload = {
        job_type: config.job_type,
        provider: config.provider,
        model: config.model,
        priority: config.priority,
        file_ids: fileIds,
        input_manifest: {
          prompt_template: config.prompt_template,
        },
      };
      console.log("Creating job with payload:", JSON.stringify(payload, null, 2));

  const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8001";
      const response = await fetch(`${apiBaseUrl}/api/jobs`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(authToken ? { Authorization: `Bearer ${authToken}` } : {}),
        },
        body: JSON.stringify(payload),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || "Failed to create job");
      }

      const result = await response.json();
      onSubmit(result.job_id || result.id);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create job");
    } finally {
      setIsSubmitting(false);
    }
  };

  const canSubmit = fileIds.length > 0 && !disabled && !isSubmitting;

  return (
    <Card className="p-6">
      <div className="mb-4">
        <h3 className="section-title">Job Configuration</h3>
        <p className="text-xs text-dark-text-tertiary">
          Configure the analysis parameters
        </p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-4">
        {/* Job Type */}
        <div>
          <label htmlFor="job_type" className="mb-2 block text-sm font-medium text-dark-text-secondary">
            Job Type
          </label>
          <select
            id="job_type"
            value={config.job_type}
            onChange={(e) => setConfig({ ...config, job_type: e.target.value })}
            className="input w-full"
            disabled={disabled}
          >
            <option value="rca_analysis">RCA Analysis</option>
            <option value="log_analysis">Log Analysis</option>
            <option value="incident_investigation">Incident Investigation</option>
          </select>
        </div>

        {/* Provider */}
        <div>
          <label htmlFor="provider" className="mb-2 block text-sm font-medium text-dark-text-secondary">
            Provider
          </label>
          <select
            id="provider"
            value={config.provider}
            onChange={(e) => setConfig({ ...config, provider: e.target.value })}
            className="input w-full"
            disabled={disabled}
          >
            <option value="copilot">GitHub Copilot</option>
            <option value="openai">OpenAI</option>
            <option value="anthropic">Anthropic</option>
            <option value="ollama">Ollama (Local)</option>
          </select>
        </div>

        {/* Prompt Template */}
        <div>
          <label htmlFor="prompt_template" className="mb-2 flex items-center justify-between text-sm font-medium text-dark-text-secondary">
            <span>Prompt Template</span>
            <Link
              href="/prompts"
              className="flex items-center gap-1 text-xs text-fluent-blue-400 hover:text-fluent-blue-300"
              target="_blank"
            >
              <Eye className="h-3 w-3" />
              View All
            </Link>
          </label>
          <select
            id="prompt_template"
            value={config.prompt_template}
            onChange={(e) => setConfig({ ...config, prompt_template: e.target.value })}
            className="input w-full"
            disabled={disabled || loadingPrompts}
          >
            {loadingPrompts ? (
              <option>Loading templates...</option>
            ) : (
              Object.entries(promptTemplates).map(([key, template]) => (
                <option key={key} value={key}>
                  {template.name}
                </option>
              ))
            )}
          </select>
          {config.prompt_template && promptTemplates[config.prompt_template] && (
            <p className="mt-1 text-xs text-dark-text-tertiary">
              {promptTemplates[config.prompt_template].description}
            </p>
          )}
        </div>

        {/* Model */}
        <div>
          <label htmlFor="model" className="mb-2 block text-sm font-medium text-dark-text-secondary">
            Model
          </label>
          <select
            id="model"
            value={config.model}
            onChange={(e) => setConfig({ ...config, model: e.target.value })}
            className="input w-full"
            disabled={disabled}
          >
            {config.provider === "copilot" && (
              <>
                <option value="gpt-4">GPT-4</option>
                <option value="gpt-4o">GPT-4o</option>
                <option value="gpt-3.5-turbo">GPT-3.5 Turbo</option>
              </>
            )}
            {config.provider === "openai" && (
              <>
                <option value="gpt-4">GPT-4</option>
                <option value="gpt-4-turbo">GPT-4 Turbo</option>
                <option value="gpt-3.5-turbo">GPT-3.5 Turbo</option>
              </>
            )}
            {config.provider === "anthropic" && (
              <>
                <option value="claude-3-opus">Claude 3 Opus</option>
                <option value="claude-3-sonnet">Claude 3 Sonnet</option>
                <option value="claude-3-haiku">Claude 3 Haiku</option>
              </>
            )}
            {config.provider === "ollama" && (
              <>
                <option value="llama2">Llama 2</option>
                <option value="codellama">Code Llama</option>
                <option value="mistral">Mistral</option>
              </>
            )}
          </select>
        </div>

        {/* Priority */}
        <div>
          <label htmlFor="priority" className="mb-2 block text-sm font-medium text-dark-text-secondary">
            Priority: {config.priority}
          </label>
          <input
            id="priority"
            type="range"
            min="0"
            max="10"
            value={config.priority}
            onChange={(e) => setConfig({ ...config, priority: parseInt(e.target.value) })}
            className="w-full accent-fluent-blue-500"
            disabled={disabled}
          />
          <div className="mt-1 flex justify-between text-xs text-dark-text-tertiary">
            <span>Low</span>
            <span>High</span>
          </div>
        </div>

        {/* File count info */}
        <div className="rounded-lg bg-dark-bg-tertiary p-3">
          <div className="flex items-center gap-2 text-sm">
            <svg
              className="h-4 w-4 text-fluent-blue-400"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
              />
            </svg>
            <span className="text-dark-text-secondary">
              {fileIds.length === 0 ? (
                "No files uploaded"
              ) : (
                <span>
                  {fileIds.length} {fileIds.length === 1 ? "file" : "files"} ready for analysis
                </span>
              )}
            </span>
          </div>
        </div>

        {/* Error display */}
        {error && (
          <div className="rounded-lg bg-red-500/10 p-3 text-sm text-red-400">
            <div className="flex items-start gap-2">
              <svg
                className="h-5 w-5 flex-shrink-0"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                />
              </svg>
              <span>{error}</span>
            </div>
          </div>
        )}

        {/* Submit button */}
        <button
          type="submit"
          disabled={!canSubmit}
          className="btn-primary w-full disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {isSubmitting ? (
            <div className="flex items-center justify-center gap-2">
              <div className="h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent" />
              <span>Starting Analysis...</span>
            </div>
          ) : (
            <div className="flex items-center justify-center gap-2">
              <svg
                className="h-5 w-5"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z"
                />
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                />
              </svg>
              <span>Start Analysis</span>
            </div>
          )}
        </button>

        {!canSubmit && fileIds.length === 0 && (
          <p className="text-center text-xs text-dark-text-tertiary">
            Upload at least one file to start analysis
          </p>
        )}
      </form>
    </Card>
  );
}
