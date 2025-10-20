"use client";

import { useEffect, useState } from "react";
import { Header } from "@/components/layout/Header";
import { Alert, Button, Card, Input } from "@/components/ui";

type WatcherConfigResponse = {
  enabled: boolean;
  roots: string[];
  include_globs: string[];
  exclude_globs: string[];
  max_file_size_mb: number | null;
  allowed_mime_types: string[];
  batch_window_seconds: number | null;
  auto_create_jobs: boolean;
};

interface WatcherStatus {
  enabled: boolean;
  roots: string[];
  auto_create_jobs: boolean;
  total_events: number;
  last_event?: {
    event_type: string;
    created_at: string;
    payload: Record<string, unknown> | null;
  };
}

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function WatcherPage() {
  const [status, setStatus] = useState<WatcherStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  // Form state
  const [enabled, setEnabled] = useState(true);
  const [roots, setRoots] = useState<string[]>(["/app/watch-folder"]);
  const [includeGlobs, setIncludeGlobs] = useState<string[]>(["**/*.log", "**/*.txt", "**/*.json", "**/*.csv"]);
  const [excludeGlobs, setExcludeGlobs] = useState<string[]>(["**/~*", "**/*.tmp", "**/Processed/**"]);
  const [maxFileSize, setMaxFileSize] = useState<number>(100);
  const [allowedMimeTypes, setAllowedMimeTypes] = useState<string[]>(["text/plain", "application/json"]);
  const [batchWindow, setBatchWindow] = useState<number>(5);
  const [autoCreateJobs, setAutoCreateJobs] = useState(true);

  // Temporary input states for adding items
  const [newRoot, setNewRoot] = useState("");
  const [newIncludeGlob, setNewIncludeGlob] = useState("");
  const [newExcludeGlob, setNewExcludeGlob] = useState("");
  const [newMimeType, setNewMimeType] = useState("");

  // Load configuration
  useEffect(() => {
    loadConfig();
    loadStatus();
  }, []);

  const loadConfig = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/v1/watcher/config`);
      if (!response.ok) throw new Error("Failed to load configuration");
      const data = (await response.json()) as WatcherConfigResponse;
      
      // Populate form
      setEnabled(data.enabled);
      setRoots(data.roots || []);
      setIncludeGlobs(data.include_globs || []);
      setExcludeGlobs(data.exclude_globs || []);
      setMaxFileSize(data.max_file_size_mb || 100);
      setAllowedMimeTypes(data.allowed_mime_types || []);
      setBatchWindow(data.batch_window_seconds || 5);
      setAutoCreateJobs(data.auto_create_jobs);
      
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load configuration");
    } finally {
      setLoading(false);
    }
  };

  const loadStatus = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/v1/watcher/status`);
      if (!response.ok) throw new Error("Failed to load status");
      const data = await response.json();
      setStatus(data);
    } catch (err) {
      console.error("Failed to load watcher status:", err);
    }
  };

  const handleSave = async () => {
    setSaving(true);
    setError(null);
    setSuccessMessage(null);

    try {
      const payload = {
        enabled,
        roots,
        include_globs: includeGlobs,
        exclude_globs: excludeGlobs,
        max_file_size_mb: maxFileSize,
        allowed_mime_types: allowedMimeTypes,
        batch_window_seconds: batchWindow,
        auto_create_jobs: autoCreateJobs,
      };

      const response = await fetch(`${API_BASE_URL}/api/v1/watcher/config`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || "Failed to save configuration");
      }
      setSuccessMessage("File watcher configuration saved successfully!");
      
      // Reload status
      await loadStatus();
      
      // Clear success message after 5 seconds
      setTimeout(() => setSuccessMessage(null), 5000);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save configuration");
    } finally {
      setSaving(false);
    }
  };

  const addRoot = () => {
    if (newRoot && !roots.includes(newRoot)) {
      setRoots([...roots, newRoot]);
      setNewRoot("");
    }
  };

  const removeRoot = (index: number) => {
    setRoots(roots.filter((_, i) => i !== index));
  };

  const addIncludeGlob = () => {
    if (newIncludeGlob && !includeGlobs.includes(newIncludeGlob)) {
      setIncludeGlobs([...includeGlobs, newIncludeGlob]);
      setNewIncludeGlob("");
    }
  };

  const removeIncludeGlob = (index: number) => {
    setIncludeGlobs(includeGlobs.filter((_, i) => i !== index));
  };

  const addExcludeGlob = () => {
    if (newExcludeGlob && !excludeGlobs.includes(newExcludeGlob)) {
      setExcludeGlobs([...excludeGlobs, newExcludeGlob]);
      setNewExcludeGlob("");
    }
  };

  const removeExcludeGlob = (index: number) => {
    setExcludeGlobs(excludeGlobs.filter((_, i) => i !== index));
  };

  const addMimeType = () => {
    if (newMimeType && !allowedMimeTypes.includes(newMimeType)) {
      setAllowedMimeTypes([...allowedMimeTypes, newMimeType]);
      setNewMimeType("");
    }
  };

  const removeMimeType = (index: number) => {
    setAllowedMimeTypes(allowedMimeTypes.filter((_, i) => i !== index));
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-dark-bg-primary">
        <Header title="File Watcher" subtitle="Automated File Monitoring" />
        <div className="container mx-auto px-4 py-12 text-center">
          <div className="inline-block animate-spin rounded-full h-12 w-12 border-4 border-fluent-blue-500 border-t-transparent"></div>
          <p className="mt-4 text-dark-text-secondary">Loading configuration...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-dark-bg-primary">
      <Header title="File Watcher" subtitle="Automated File Monitoring" />

      <div className="container mx-auto px-4 py-8 max-w-6xl">
        {/* Page Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-dark-text-primary mb-2">
            File Watcher Configuration
          </h1>
          <p className="text-dark-text-secondary">
            Configure folders to monitor for automatic file analysis. Files dropped into watched folders
            are automatically processed and moved to a{" "}
            <span className="font-mono text-dark-text-primary/80">Processed</span>{" "}
            subfolder.
          </p>
        </div>

        {/* Alerts */}
        {error && (
          <Alert variant="error" className="mb-6" onClose={() => setError(null)}>
            {error}
          </Alert>
        )}

        {successMessage && (
          <Alert variant="success" className="mb-6" onClose={() => setSuccessMessage(null)}>
            {successMessage}
          </Alert>
        )}

        {/* Status Card */}
        {status && (
          <Card className="mb-6 p-6 bg-gradient-to-br from-fluent-blue-500/10 via-transparent to-dark-bg-secondary border-fluent-blue-500/30">
            <h2 className="text-xl font-semibold text-dark-text-primary mb-4 flex items-center gap-2">
              <svg className="w-5 h-5 text-fluent-info" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              Watcher Status
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="p-4 rounded-lg bg-dark-bg-elevated/50">
                <div className="flex items-center gap-2 mb-2">
                  <div className={`w-3 h-3 rounded-full ${status.enabled ? 'bg-fluent-success animate-pulse' : 'bg-dark-text-tertiary'}`}></div>
                  <span className="text-sm font-medium text-dark-text-secondary">Status</span>
                </div>
                <p className="text-lg font-semibold text-dark-text-primary">
                  {status.enabled ? "Active" : "Inactive"}
                </p>
              </div>
              <div className="p-4 rounded-lg bg-dark-bg-elevated/50">
                <p className="text-sm font-medium text-dark-text-secondary mb-2">Total Events</p>
                <p className="text-lg font-semibold text-dark-text-primary">{status.total_events.toLocaleString()}</p>
              </div>
              <div className="p-4 rounded-lg bg-dark-bg-elevated/50">
                <p className="text-sm font-medium text-dark-text-secondary mb-2">Watched Folders</p>
                <p className="text-lg font-semibold text-dark-text-primary">{status.roots.length}</p>
              </div>
            </div>
            {status.last_event && (
              <div className="mt-4 p-3 rounded-lg bg-dark-bg-elevated/30 border border-dark-border/20">
                <p className="text-xs font-medium text-dark-text-tertiary mb-1">Last Event</p>
                <p className="text-sm text-dark-text-secondary">
                  <span className="font-mono text-fluent-info">{status.last_event.event_type}</span>
                  {" • "}
                  <span className="text-dark-text-tertiary">
                    {new Date(status.last_event.created_at).toLocaleString()}
                  </span>
                </p>
              </div>
            )}
          </Card>
        )}

        {/* Configuration Form */}
        <div className="space-y-6">
          {/* Enable/Disable */}
          <Card className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-lg font-semibold text-dark-text-primary mb-1">Enable File Watcher</h3>
                <p className="text-sm text-dark-text-tertiary">
                  Turn on automatic monitoring of configured folders
                </p>
              </div>
              <button
                onClick={() => setEnabled(!enabled)}
                type="button"
                className={`relative inline-flex h-8 w-14 items-center rounded-full transition-colors ${
                  enabled ? "bg-fluent-success" : "bg-dark-border"
                }`}
                aria-pressed={enabled ? "true" : "false"}
                aria-label={enabled ? "Disable file watcher" : "Enable file watcher"}
              >
                <span
                  className={`inline-block h-6 w-6 transform rounded-full bg-white transition-transform ${
                    enabled ? "translate-x-7" : "translate-x-1"
                  }`}
                />
              </button>
            </div>
          </Card>

          {/* Watch Folders */}
          <Card className="p-6">
            <h3 className="text-lg font-semibold text-dark-text-primary mb-4">Watch Folders</h3>
            <p className="text-sm text-dark-text-tertiary mb-4">
              Folders to monitor for new files. Files will be automatically processed and moved to a{" "}
              <span className="font-mono text-dark-text-primary/80">Processed</span>{" "}
              subfolder.
            </p>
            <div className="space-y-3">
              {roots.map((root, index) => (
                <div key={index} className="flex items-center gap-2 p-3 rounded-lg bg-dark-bg-elevated/30 border border-dark-border/20">
                  <svg className="w-5 h-5 text-fluent-blue-400 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z" />
                  </svg>
                  <span className="flex-1 font-mono text-sm text-dark-text-primary">{root}</span>
                  <button
                    onClick={() => removeRoot(index)}
                    type="button"
                    className="p-1 rounded hover:bg-fluent-error/20 text-fluent-error transition-colors"
                    aria-label={`Remove watch folder ${root}`}
                  >
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                    </svg>
                  </button>
                </div>
              ))}
              <div className="flex gap-2">
                <Input
                  value={newRoot}
                  onChange={(e) => setNewRoot(e.target.value)}
                  onKeyPress={(e) => e.key === "Enter" && addRoot()}
                  placeholder="/path/to/watch/folder"
                  className="flex-1"
                />
                  <Button onClick={addRoot} variant="secondary">
                  Add Folder
                </Button>
              </div>
            </div>
          </Card>

          {/* File Patterns */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Include Patterns */}
            <Card className="p-6">
              <h3 className="text-lg font-semibold text-dark-text-primary mb-2">Include Patterns</h3>
              <p className="text-sm text-dark-text-tertiary mb-4">
                File patterns to watch (glob patterns supported)
              </p>
              <div className="space-y-2">
                {includeGlobs.map((glob, index) => (
                  <div key={index} className="flex items-center gap-2 p-2 rounded bg-dark-bg-elevated/30">
                    <span className="flex-1 font-mono text-sm text-dark-text-primary">{glob}</span>
                    <button
                      onClick={() => removeIncludeGlob(index)}
                      type="button"
                      className="p-1 rounded hover:bg-fluent-error/20 text-fluent-error transition-colors"
                      aria-label={`Remove include pattern ${glob}`}
                    >
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                      </svg>
                    </button>
                  </div>
                ))}
                <div className="flex gap-2">
                  <Input
                    value={newIncludeGlob}
                    onChange={(e) => setNewIncludeGlob(e.target.value)}
                    onKeyPress={(e) => e.key === "Enter" && addIncludeGlob()}
                    placeholder="**/*.log"
                    className="flex-1"
                  />
                  <Button onClick={addIncludeGlob} variant="secondary" size="sm">
                    Add Pattern
                  </Button>
                </div>
              </div>
            </Card>

            {/* Exclude Patterns */}
            <Card className="p-6">
              <h3 className="text-lg font-semibold text-dark-text-primary mb-2">Exclude Patterns</h3>
              <p className="text-sm text-dark-text-tertiary mb-4">
                File patterns to ignore
              </p>
              <div className="space-y-2">
                {excludeGlobs.map((glob, index) => (
                  <div key={index} className="flex items-center gap-2 p-2 rounded bg-dark-bg-elevated/30">
                    <span className="flex-1 font-mono text-sm text-dark-text-primary">{glob}</span>
                    <button
                      onClick={() => removeExcludeGlob(index)}
                      type="button"
                      className="p-1 rounded hover:bg-fluent-error/20 text-fluent-error transition-colors"
                      aria-label={`Remove exclusion pattern ${glob}`}
                    >
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                      </svg>
                    </button>
                  </div>
                ))}
                <div className="flex gap-2">
                  <Input
                    value={newExcludeGlob}
                    onChange={(e) => setNewExcludeGlob(e.target.value)}
                    onKeyPress={(e) => e.key === "Enter" && addExcludeGlob()}
                    placeholder="**/Processed/**"
                    className="flex-1"
                  />
                  <Button onClick={addExcludeGlob} variant="secondary" size="sm">
                    Add Pattern
                  </Button>
                </div>
              </div>
            </Card>
          </div>

          {/* Advanced Settings */}
          <Card className="p-6">
            <h3 className="text-lg font-semibold text-dark-text-primary mb-4">Advanced Settings</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div>
                <label className="block text-sm font-medium text-dark-text-secondary mb-2">
                  Max File Size (MB)
                </label>
                <Input
                  type="number"
                  value={maxFileSize}
                  onChange={(e) => setMaxFileSize(parseInt(e.target.value) || 100)}
                  min="1"
                  max="1000"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-dark-text-secondary mb-2">
                  Batch Window (seconds)
                </label>
                <Input
                  type="number"
                  value={batchWindow}
                  onChange={(e) => setBatchWindow(parseInt(e.target.value) || 5)}
                  min="1"
                  max="60"
                />
                <p className="text-xs text-dark-text-tertiary mt-1">
                  Time to wait before processing multiple files together
                </p>
              </div>
            </div>

            <div className="mt-6">
              <label className="block text-sm font-medium text-dark-text-secondary mb-2">
                Allowed MIME Types
              </label>
              <div className="space-y-2">
                <div className="flex flex-wrap gap-2">
                  {allowedMimeTypes.map((mime, index) => (
                    <span
                      key={index}
                      className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-fluent-blue-500/20 text-fluent-blue-400 text-sm border border-fluent-blue-500/30"
                    >
                      {mime}
                      <button
                        onClick={() => removeMimeType(index)}
                        type="button"
                        className="hover:text-fluent-error transition-colors"
                        aria-label={`Remove MIME type ${mime}`}
                      >
                        <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                        </svg>
                      </button>
                    </span>
                  ))}
                </div>
                <div className="flex gap-2">
                  <Input
                    value={newMimeType}
                    onChange={(e) => setNewMimeType(e.target.value)}
                    onKeyPress={(e) => e.key === "Enter" && addMimeType()}
                    placeholder="text/plain"
                    className="flex-1"
                  />
                  <Button onClick={addMimeType} variant="secondary" size="sm">
                    Add
                  </Button>
                </div>
              </div>
            </div>

            <div className="mt-6 flex items-center justify-between p-4 rounded-lg bg-dark-bg-elevated/30 border border-dark-border/20">
              <div>
                <p className="font-medium text-dark-text-primary">Auto-create Analysis Jobs</p>
                <p className="text-sm text-dark-text-tertiary">Automatically trigger RCA for detected files</p>
              </div>
              <button
                onClick={() => setAutoCreateJobs(!autoCreateJobs)}
                type="button"
                className={`relative inline-flex h-8 w-14 items-center rounded-full transition-colors ${
                  autoCreateJobs ? "bg-fluent-success" : "bg-dark-border"
                }`}
                aria-pressed={autoCreateJobs ? "true" : "false"}
                aria-label={autoCreateJobs ? "Disable auto-create analysis jobs" : "Enable auto-create analysis jobs"}
              >
                <span
                  className={`inline-block h-6 w-6 transform rounded-full bg-white transition-transform ${
                    autoCreateJobs ? "translate-x-7" : "translate-x-1"
                  }`}
                />
              </button>
            </div>
          </Card>

          {/* Save Button */}
          <div className="flex justify-end gap-4">
            <Button variant="secondary" onClick={loadConfig}>
              Reset
            </Button>
            <Button
              variant="primary"
              onClick={handleSave}
              loading={saving}
              icon={
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                </svg>
              }
            >
              Save Configuration
            </Button>
          </div>
        </div>

        {/* Info Card */}
        <Card className="mt-8 p-6 bg-gradient-to-r from-fluent-info/10 via-transparent to-dark-bg-secondary border-fluent-info/30">
          <h3 className="text-lg font-semibold text-dark-text-primary mb-2 flex items-center gap-2">
            <svg className="w-5 h-5 text-fluent-info" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            How It Works
          </h3>
          <ul className="space-y-2 text-sm text-dark-text-secondary">
            <li className="flex items-start gap-2">
              <svg className="w-5 h-5 text-fluent-info mt-0.5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <span>Files dropped into watched folders are automatically detected</span>
            </li>
            <li className="flex items-start gap-2">
              <svg className="w-5 h-5 text-fluent-info mt-0.5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <span>Files are validated against include/exclude patterns and MIME types</span>
            </li>
            <li className="flex items-start gap-2">
              <svg className="w-5 h-5 text-fluent-info mt-0.5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <span>RCA analysis jobs are automatically created (if enabled)</span>
            </li>
            <li className="flex items-start gap-2">
              <svg className="w-5 h-5 text-fluent-info mt-0.5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <span>
                Processed files are moved to a{" "}
                <span className="font-mono text-dark-text-primary/80">Processed</span>{" "}
                subfolder to avoid re-processing
              </span>
            </li>
          </ul>
        </Card>
      </div>
    </div>
  );
}
