"use client";

import {
  ChangeEvent,
  KeyboardEvent as ReactKeyboardEvent,
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
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
  available_processors?: WatcherProcessorOption[];
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

type WatcherEventPayload = {
  id?: string;
  event_type: string;
  created_at: string;
  payload?: Record<string, unknown> | null;
  job_id?: string | null;
  watcher_id?: string | null;
};

type WatcherStatsTimelinePoint = {
  bucket: string;
  count: number;
};

type WatcherStatsEntry = {
  event_type: string;
  total: number;
  timeline: WatcherStatsTimelinePoint[];
};

type WatcherStatsResponse = {
  lookback_hours: number;
  total_events: number;
  event_types: WatcherStatsEntry[];
};

type WatcherPreset = {
  id: string;
  name: string;
  description: string;
  config: Partial<WatcherConfigResponse>;
};

type WatcherProcessorOption = {
  id: string;
  name: string;
  description: string;
  default_options: Record<string, unknown>;
};

type PatternTestOutcome = {
  path: string;
  status: string;
  reason: string;
  matched_includes: string[];
  matched_excludes: string[];
  include_globs: string[];
  exclude_globs: string[];
};

const SSE_HISTORY = 50;
const MAX_EVENT_LOG = 200;
const STATS_REFRESH_INTERVAL = 60_000;

const formatDisplayTimestamp = (value: string): string => {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return date.toLocaleString();
};

const formatBucketLabel = (value: string): string => {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
};

const summarisePayload = (payload: Record<string, unknown> | null | undefined): string | null => {
  if (!payload) {
    return null;
  }
  try {
    const serialised = JSON.stringify(payload);
    if (serialised.length > 140) {
      return `${serialised.slice(0, 137)}...`;
    }
    return serialised;
  } catch (err) {
    console.error("Failed to serialise watcher payload", err);
    return null;
  }
};

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001";

export default function WatcherPage() {
  const [status, setStatus] = useState<WatcherStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [eventLog, setEventLog] = useState<WatcherEventPayload[]>([]);
  const [sseStatus, setSseStatus] = useState<"idle" | "connecting" | "open" | "error">("idle");
  const eventSourceRef = useRef<EventSource | null>(null);
  const reconnectTimerRef = useRef<number | null>(null);
  const [streamError, setStreamError] = useState<string | null>(null);
  const [stats, setStats] = useState<WatcherStatsResponse | null>(null);
  const [statsLoading, setStatsLoading] = useState(true);
  const statsTimerRef = useRef<number | null>(null);
  const [presets, setPresets] = useState<WatcherPreset[]>([]);
  const [selectedPresetId, setSelectedPresetId] = useState<string>("");
  const [availableProcessors, setAvailableProcessors] = useState<WatcherProcessorOption[]>([]);
  const [patternPath, setPatternPath] = useState("");
  const [patternResult, setPatternResult] = useState<PatternTestOutcome | null>(null);
  const [patternTesting, setPatternTesting] = useState(false);
  const [patternError, setPatternError] = useState<string | null>(null);

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

  const timelineEvents = useMemo(() => {
    if (!eventLog.length) {
      return [] as WatcherEventPayload[];
    }
    return [...eventLog].reverse();
  }, [eventLog]);

  const recentEvents = useMemo(() => timelineEvents.slice(0, 30), [timelineEvents]);

  const selectedPreset = useMemo(() => {
    if (!selectedPresetId) {
      return null;
    }
    return presets.find((preset) => preset.id === selectedPresetId) ?? null;
  }, [presets, selectedPresetId]);

  const connectionBadge = useMemo(() => {
    switch (sseStatus) {
      case "open":
        return { label: "Streaming", dot: "bg-green-400", tone: "text-green-300" };
      case "connecting":
        return { label: "Connecting", dot: "bg-yellow-400", tone: "text-yellow-300" };
      case "error":
        return { label: "Disconnected", dot: "bg-red-400", tone: "text-red-300" };
      default:
        return { label: "Idle", dot: "bg-dark-text-tertiary", tone: "text-dark-text-tertiary" };
    }
  }, [sseStatus]);

  const statsEventTypes = useMemo(() => stats?.event_types ?? [], [stats]);
  const lookbackHours = stats?.lookback_hours ?? 24;
  const totalEventsCount = useMemo(() => {
    if (stats?.total_events !== undefined) {
      return stats.total_events;
    }
    if (status?.total_events !== undefined) {
      return status.total_events;
    }
    return 0;
  }, [stats, status]);

  const patternStatusTheme = useMemo(() => {
    if (!patternResult) {
      return null;
    }
    switch (patternResult.status) {
      case "included":
        return { border: "border-green-400/40", background: "bg-green-500/10", tone: "text-green-300" };
      case "excluded":
        return { border: "border-amber-400/40", background: "bg-amber-500/10", tone: "text-amber-200" };
      default:
        return { border: "border-dark-border", background: "bg-dark-bg-elevated/40", tone: "text-dark-text-secondary" };
    }
  }, [patternResult]);

  // Load configuration
  const loadConfig = useCallback(async () => {
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
  setAvailableProcessors(data.available_processors || []);
      
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load configuration");
    } finally {
      setLoading(false);
    }
  }, []);

  const loadStatus = useCallback(async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/v1/watcher/status`);
      if (!response.ok) throw new Error("Failed to load status");
      const data = await response.json();
      setStatus(data);
    } catch (err) {
      console.error("Failed to load watcher status:", err);
    }
  }, []);

  useEffect(() => {
    void loadConfig();
    void loadStatus();
  }, [loadConfig, loadStatus]);

  const loadPresets = useCallback(async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/v1/watcher/presets`);
      if (!response.ok) return;
      const data = (await response.json()) as WatcherPreset[];
      setPresets(data);
    } catch (err) {
      console.error("Failed to load watcher presets:", err);
    }
  }, []);

  useEffect(() => {
    void loadPresets();
  }, [loadPresets]);

  const loadStats = useCallback(async () => {
    setStatsLoading(true);
    try {
      const response = await fetch(`${API_BASE_URL}/api/v1/watcher/stats?lookback_hours=24`);
      if (!response.ok) throw new Error("Failed to load watcher statistics");
      const data = (await response.json()) as WatcherStatsResponse;
      setStats(data);
    } catch (err) {
      console.error("Failed to load watcher statistics:", err);
    } finally {
      setStatsLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadStats();
    if (typeof window !== "undefined") {
      const interval = window.setInterval(() => {
        void loadStats();
      }, STATS_REFRESH_INTERVAL);
      statsTimerRef.current = interval;
      return () => window.clearInterval(interval);
    }
    return undefined;
  }, [loadStats]);

  const stopEventStream = useCallback(() => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
    }
    if (typeof window !== "undefined" && reconnectTimerRef.current !== null) {
      window.clearTimeout(reconnectTimerRef.current);
      reconnectTimerRef.current = null;
    }
  }, []);

  const appendEvent = useCallback((payload: WatcherEventPayload) => {
    setEventLog((previous) => {
      const next = [...previous, payload];
      if (next.length > MAX_EVENT_LOG) {
        return next.slice(next.length - MAX_EVENT_LOG);
      }
      return next;
    });
    setStatus((prev) => {
      if (!prev) {
        return prev;
      }
      const updated: WatcherStatus = {
        ...prev,
        total_events: prev.total_events + 1,
        last_event: {
          event_type: payload.event_type,
          created_at: payload.created_at,
          payload: payload.payload ?? null,
        },
      };
      return updated;
    });
  }, []);

  const startEventStream = useCallback(function startStream() {
    if (typeof window === "undefined" || typeof window.EventSource === "undefined") {
      setSseStatus("error");
      setStreamError("Live event streaming is not supported in this environment.");
      return;
    }

    stopEventStream();
    setStreamError(null);
    setSseStatus("connecting");

    const endpoint = `${API_BASE_URL}/api/v1/watcher/events?history=${SSE_HISTORY}`;
    const source = new window.EventSource(endpoint, { withCredentials: true });
    eventSourceRef.current = source;

    const handleWatcherEvent: EventListener = (event) => {
      const message = event as MessageEvent<string>;
      if (!message.data) {
        return;
      }
      try {
        const payload = JSON.parse(message.data) as WatcherEventPayload & { event_type: string };
        appendEvent(payload);
      } catch (parseError) {
        console.error("Failed to parse watcher event:", parseError);
      }
    };

    const handleHeartbeat: EventListener = () => {
      if (sseStatus !== "open") {
        setSseStatus("open");
      }
    };

    source.onopen = () => {
      setSseStatus("open");
      setStreamError(null);
      if (reconnectTimerRef.current !== null && typeof window !== "undefined") {
        window.clearTimeout(reconnectTimerRef.current);
        reconnectTimerRef.current = null;
      }
    };

    source.onerror = () => {
      setSseStatus("error");
      setStreamError("Live stream disconnected. Retrying...");
      stopEventStream();
      if (typeof window !== "undefined" && reconnectTimerRef.current === null) {
        reconnectTimerRef.current = window.setTimeout(() => {
          reconnectTimerRef.current = null;
          startStream();
        }, 3000);
      }
    };

    source.addEventListener("watcher-event", handleWatcherEvent);
    source.addEventListener("heartbeat", handleHeartbeat);
  }, [appendEvent, stopEventStream, sseStatus]);

  useEffect(() => {
    startEventStream();
    return () => {
      stopEventStream();
      setSseStatus("idle");
    };
  }, [startEventStream, stopEventStream]);

  const applyPreset = useCallback((preset: WatcherPreset) => {
    const { config } = preset;
    if (config.roots && Array.isArray(config.roots)) {
      setRoots([...config.roots]);
    }
    if (config.include_globs && Array.isArray(config.include_globs)) {
      setIncludeGlobs([...config.include_globs]);
    }
    if (config.exclude_globs && Array.isArray(config.exclude_globs)) {
      setExcludeGlobs([...config.exclude_globs]);
    }
    if (config.allowed_mime_types && Array.isArray(config.allowed_mime_types)) {
      setAllowedMimeTypes([...config.allowed_mime_types]);
    }
    if (typeof config.max_file_size_mb === "number") {
      setMaxFileSize(config.max_file_size_mb);
    }
    if (typeof config.batch_window_seconds === "number") {
      setBatchWindow(config.batch_window_seconds);
    }
    if (typeof config.auto_create_jobs === "boolean") {
      setAutoCreateJobs(config.auto_create_jobs);
    }
    if (typeof config.enabled === "boolean") {
      setEnabled(config.enabled);
    }
    setSuccessMessage(`Preset "${preset.name}" applied. Save to persist changes.`);
  }, []);

  const handlePresetChange = useCallback(
    (event: ChangeEvent<HTMLSelectElement>) => {
      const presetId = event.target.value;
      setSelectedPresetId(presetId);
      const preset = presets.find((entry) => entry.id === presetId);
      if (preset) {
        applyPreset(preset);
      }
    },
    [applyPreset, presets],
  );

  const handlePatternTest = useCallback(async () => {
    const sample = patternPath.trim();
    if (!sample) {
      setPatternError("Enter a sample path to evaluate.");
      setPatternResult(null);
      return;
    }

    setPatternTesting(true);
    setPatternError(null);

    try {
      const response = await fetch(`${API_BASE_URL}/api/v1/watcher/pattern/test`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          path: sample,
          include_globs: includeGlobs,
          exclude_globs: excludeGlobs,
        }),
      });

      if (!response.ok) {
        const detail = await response.json().catch(() => ({}));
        throw new Error(detail.detail || "Pattern test failed");
      }

      const data = (await response.json()) as PatternTestOutcome;
      setPatternResult(data);
    } catch (err) {
      setPatternError(err instanceof Error ? err.message : "Pattern test failed");
      setPatternResult(null);
    } finally {
      setPatternTesting(false);
    }
  }, [excludeGlobs, includeGlobs, patternPath]);

  const handlePatternKeyDown = useCallback(
    (event: ReactKeyboardEvent<HTMLInputElement>) => {
      if (event.key === "Enter") {
        event.preventDefault();
        void handlePatternTest();
      }
    },
    [handlePatternTest],
  );

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
      const saved = (await response.json().catch(() => null)) as WatcherConfigResponse | null;
      if (saved) {
        setAvailableProcessors(saved.available_processors || []);
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
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
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
              <div className="p-4 rounded-lg bg-dark-bg-elevated/50">
                <p className="text-sm font-medium text-dark-text-secondary mb-2">Processors Available</p>
                <p className="text-lg font-semibold text-dark-text-primary">{availableProcessors.length}</p>
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

        {/* Live Event Stream */}
        <Card className="mb-6 p-6">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <h3 className="text-lg font-semibold text-dark-text-primary">Live Event Stream</h3>
              <p className="text-sm text-dark-text-tertiary">
                Real-time watcher activity captured from the background processor.
              </p>
            </div>
            <div className={`flex items-center gap-2 text-xs ${connectionBadge.tone}`}>
              <span className={`h-2 w-2 rounded-full ${connectionBadge.dot}`} />
              {connectionBadge.label}
            </div>
          </div>
          {streamError && (
            <div className="mt-4 rounded-md border border-amber-400/40 bg-amber-500/10 px-3 py-2 text-xs text-amber-200">
              {streamError}
            </div>
          )}
          <div className="mt-4 max-h-72 overflow-y-auto rounded-lg border border-dark-border/40 bg-dark-bg-elevated/30 p-3">
            {recentEvents.length ? (
              <ul className="space-y-3">
                {recentEvents.map((event, index) => {
                  const summary = summarisePayload(event.payload);
                  const jobLabel = event.job_id ? `Job ${event.job_id}` : null;
                  return (
                    <li
                      key={event.id ?? `${event.event_type}-${event.created_at}-${index}`}
                      className="rounded-md bg-dark-bg-elevated/40 p-3"
                    >
                      <div className="flex items-start justify-between gap-3">
                        <div className="min-w-0">
                          <p className="text-sm font-semibold text-dark-text-primary">{event.event_type}</p>
                          {jobLabel && (
                            <p className="mt-1 text-xs text-dark-text-tertiary">{jobLabel}</p>
                          )}
                          {summary && (
                            <p className="mt-2 break-all font-mono text-[11px] text-dark-text-secondary/90">
                              {summary}
                            </p>
                          )}
                        </div>
                        <span className="whitespace-nowrap text-xs text-dark-text-tertiary">
                          {formatDisplayTimestamp(event.created_at)}
                        </span>
                      </div>
                    </li>
                  );
                })}
              </ul>
            ) : (
              <p className="text-sm text-dark-text-tertiary">Waiting for watcher activity...</p>
            )}
          </div>
        </Card>

        {/* Analytics */}
        <Card className="mb-6 p-6">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <h3 className="text-lg font-semibold text-dark-text-primary">Watcher Analytics</h3>
              <p className="text-sm text-dark-text-tertiary">Activity for the last {lookbackHours} hours</p>
            </div>
            <div className="text-right">
              <p className="text-xs uppercase tracking-wide text-dark-text-tertiary">Events</p>
              <p className="text-xl font-semibold text-dark-text-primary">
                {totalEventsCount.toLocaleString()}
              </p>
            </div>
          </div>
          {statsLoading ? (
            <div className="mt-6 flex justify-center">
              <div className="h-8 w-8 animate-spin rounded-full border-4 border-fluent-blue-500 border-t-transparent" />
            </div>
          ) : statsEventTypes.length ? (
            <div className="mt-4 grid gap-3">
              {statsEventTypes.map((entry) => (
                <div
                  key={entry.event_type}
                  className="rounded-lg border border-dark-border/40 bg-dark-bg-elevated/30 p-3"
                >
                  <div className="flex items-center justify-between text-sm">
                    <span className="font-semibold text-dark-text-primary">{entry.event_type}</span>
                    <span className="text-dark-text-secondary">{entry.total.toLocaleString()}</span>
                  </div>
                  {entry.timeline.length > 0 && (
                    <div className="mt-3 flex flex-wrap gap-2 text-[10px] text-dark-text-tertiary">
                      {entry.timeline.slice(-6).map((point) => (
                        <span
                          key={`${entry.event_type}-${point.bucket}`}
                          className="rounded bg-dark-bg-elevated/60 px-2 py-1"
                        >
                          {formatBucketLabel(point.bucket)} · {point.count}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              ))}
            </div>
          ) : (
            <p className="mt-4 text-sm text-dark-text-tertiary">
              No watcher activity recorded in the selected window.
            </p>
          )}
        </Card>

        {/* Presets */}
        {presets.length > 0 && (
          <Card className="mb-6 p-6">
            <h3 className="text-lg font-semibold text-dark-text-primary mb-2">Configuration Presets</h3>
            <p className="text-sm text-dark-text-tertiary mb-4">
              Pick a starting template to populate the watcher settings quickly.
            </p>
            <div className="flex flex-col gap-3 md:flex-row md:items-center">
              <label className="w-full text-sm text-dark-text-secondary md:flex-1">
                <span className="sr-only">Select a watcher preset</span>
                <select
                  value={selectedPresetId}
                  onChange={handlePresetChange}
                  className="mt-0 w-full rounded-md border border-dark-border bg-dark-bg-elevated px-3 py-2 text-sm text-dark-text-primary"
                >
                  <option value="">Choose a preset…</option>
                  {presets.map((preset) => (
                    <option key={preset.id} value={preset.id}>
                      {preset.name}
                    </option>
                  ))}
                </select>
              </label>
              {selectedPreset && (
                <div className="text-xs text-dark-text-tertiary md:w-1/2">
                  {selectedPreset.description}
                </div>
              )}
            </div>
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
              <label className="relative inline-flex h-8 w-14 cursor-pointer select-none items-center">
                <span className="sr-only">{enabled ? "Disable file watcher" : "Enable file watcher"}</span>
                <input
                  type="checkbox"
                  checked={enabled}
                  onChange={() => setEnabled(!enabled)}
                  className="sr-only"
                />
                <span
                  className={`pointer-events-none absolute inset-0 rounded-full transition-colors ${
                    enabled ? "bg-fluent-success" : "bg-dark-border"
                  }`}
                />
                <span
                  className={`pointer-events-none absolute h-6 w-6 transform rounded-full bg-white transition-transform ${
                    enabled ? "translate-x-7" : "translate-x-1"
                  }`}
                />
              </label>
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

          {/* Pattern Tester */}
          <Card className="p-6">
            <h3 className="text-lg font-semibold text-dark-text-primary mb-2">Pattern Tester</h3>
            <p className="text-sm text-dark-text-tertiary mb-4">
              Validate whether a sample file path would be processed using the current include and exclude rules.
            </p>
            <div className="flex flex-col gap-3 md:flex-row md:items-center">
              <Input
                value={patternPath}
                onChange={(event) => setPatternPath(event.target.value)}
                onKeyDown={handlePatternKeyDown}
                placeholder="/var/logs/errors/app.log"
                className="flex-1"
              />
              <Button
                variant="secondary"
                onClick={handlePatternTest}
                disabled={patternTesting}
              >
                {patternTesting ? "Testing..." : "Test Path"}
              </Button>
            </div>
            {patternError && (
              <p className="mt-3 text-xs text-red-300">{patternError}</p>
            )}
            {patternResult && patternStatusTheme && (
              <div
                className={`mt-4 rounded-lg border ${patternStatusTheme.border} ${patternStatusTheme.background} p-4`}
              >
                <p className={`text-sm font-semibold ${patternStatusTheme.tone}`}>
                  Result: {patternResult.status.toUpperCase()} — {patternResult.reason}
                </p>
                <div className="mt-3 grid gap-3 md:grid-cols-2">
                  <div>
                    <p className="text-xs font-medium text-dark-text-tertiary uppercase tracking-wide">Matched include patterns</p>
                    {patternResult.matched_includes.length ? (
                      <ul className="mt-2 space-y-1 text-xs text-dark-text-secondary">
                        {patternResult.matched_includes.map((pattern) => (
                          <li key={pattern} className="font-mono">{pattern}</li>
                        ))}
                      </ul>
                    ) : (
                      <p className="mt-2 text-xs text-dark-text-tertiary">None</p>
                    )}
                  </div>
                  <div>
                    <p className="text-xs font-medium text-dark-text-tertiary uppercase tracking-wide">Matched exclude patterns</p>
                    {patternResult.matched_excludes.length ? (
                      <ul className="mt-2 space-y-1 text-xs text-dark-text-secondary">
                        {patternResult.matched_excludes.map((pattern) => (
                          <li key={pattern} className="font-mono">{pattern}</li>
                        ))}
                      </ul>
                    ) : (
                      <p className="mt-2 text-xs text-dark-text-tertiary">None</p>
                    )}
                  </div>
                </div>
              </div>
            )}
          </Card>

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
              <label className="relative inline-flex h-8 w-14 cursor-pointer select-none items-center">
                <span className="sr-only">
                  {autoCreateJobs ? "Disable auto-create analysis jobs" : "Enable auto-create analysis jobs"}
                </span>
                <input
                  type="checkbox"
                  checked={autoCreateJobs}
                  onChange={() => setAutoCreateJobs(!autoCreateJobs)}
                  className="sr-only"
                />
                <span
                  className={`pointer-events-none absolute inset-0 rounded-full transition-colors ${
                    autoCreateJobs ? "bg-fluent-success" : "bg-dark-border"
                  }`}
                />
                <span
                  className={`pointer-events-none absolute h-6 w-6 transform rounded-full bg-white transition-transform ${
                    autoCreateJobs ? "translate-x-7" : "translate-x-1"
                  }`}
                />
              </label>
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
