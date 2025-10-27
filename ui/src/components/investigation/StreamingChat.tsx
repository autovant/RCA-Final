"use client";

import { useState, useEffect, useRef, useCallback, useMemo, type KeyboardEvent } from "react";
import { Card } from "@/components/ui";

type StepStatus = "pending" | "in-progress" | "completed" | "failed";
type MessageVariant = "info" | "success" | "warning" | "error";

interface StepDefinition {
  id: string;
  label: string;
  description: string;
}

interface StepState extends StepDefinition {
  status: StepStatus;
  lastMessage?: string;
  lastUpdated?: Date;
  details?: Record<string, unknown>;
}

interface LogEntry {
  id: string;
  content: string;
  timestamp: Date;
  variant: MessageVariant;
}

interface JobEventPayload {
  event_type: string;
  data?: Record<string, unknown>;
  created_at?: string;
  id?: string;
}

interface StreamingChatProps {
  jobId: string | null;
  onStatusChange?: (status: string) => void;
}

type FileProgressStatus = "pending" | "processing" | "completed" | "quarantined";

type FileSecurityState = "clear" | "redacted" | "warnings" | "quarantined";
 
type SseStatus = "idle" | "connecting" | "open" | "closed" | "error" | "unsupported";

interface FileProgressEntry {
  key: string;
  fileId?: string;
  name: string;
  status: FileProgressStatus;
  position?: number;
  total?: number;
  startedAt?: Date;
  completedAt?: Date;
  chunks?: number;
  redactionTotal?: number;
  warningCount?: number;
  errorCount?: number;
  securityState?: FileSecurityState;
  validationWarnings?: string[];
}

interface FileProgressStats {
  total: number;
  completed: number;
  processing: number;
  quarantined: number;
}

interface FilePreviewSummary {
  fileId: string;
  filename: string;
  lineCount: number;
  chunkCount: number;
  sampleHead: string[];
  sampleTail: string[];
  topKeywords: string[];
  errorCount: number;
  warningCount: number;
  criticalCount: number;
  infoCount: number;
  redactionApplied: boolean;
  redactionCounts: Record<string, number>;
  redactionFailsafeTriggered: boolean;
  redactionValidationWarnings: string[];
  checksum?: string;
  fileSize?: number;
  contentType?: string;
}

const STEP_DEFINITIONS: StepDefinition[] = [
  {
    id: "classification",
    label: "Classifying uploaded files",
    description: "Analyzing file types and preparing analysis pipeline.",
  },
  {
    id: "redaction",
    label: "🔒 PII Protection: Scanning & Redacting Sensitive Data",
    description: "Multi-pass scanning for credentials, secrets, and personal data with strict validation.",
  },
  {
    id: "chunking",
    label: "Segmenting content into analysis-ready chunks",
    description: "Breaking documents into analysis-ready chunks.",
  },
  {
    id: "embedding",
    label: "Generating semantic embeddings",
    description: "Creating semantic vectors for similarity search.",
  },
  {
    id: "storage",
    label: "Storing structured insights",
    description: "Persisting structured artefacts for later retrieval.",
  },
  {
    id: "correlation",
    label: "Correlating with historical incidents",
    description: "Searching for similar incidents and patterns.",
  },
  {
    id: "llm",
    label: "Running AI-powered root cause analysis",
    description: "Using GitHub Copilot to analyze root causes.",
  },
  {
    id: "report",
    label: "Preparing final RCA report",
    description: "Compiling the final RCA report and insights.",
  },
  {
    id: "completed",
    label: "Analysis completed successfully",
    description: "RCA analysis complete and report ready.",
  },
];

const createInitialSteps = (): StepState[] =>
  STEP_DEFINITIONS.map((step) => ({ ...step, status: "pending" }));

const MAX_LOG_ITEMS = 200;

const STEP_STATUS_PRIORITY: Record<StepStatus, number> = {
  pending: 0,
  "in-progress": 1,
  completed: 2,
  failed: 3,
};

function normaliseProgressStatus(rawStatus: string): StepStatus {
  const value = rawStatus.toLowerCase();
  if (["completed", "complete", "success", "done"].includes(value)) {
    return "completed";
  }
  if (["failed", "error", "cancelled"].includes(value)) {
    return "failed";
  }
  if (["started", "running", "in_progress", "in-progress"].includes(value)) {
    return "in-progress";
  }
  return "pending";
}

function variantForStatus(status: StepStatus): MessageVariant {
  switch (status) {
    case "completed":
      return "success";
    case "failed":
      return "error";
    case "in-progress":
      return "info";
    default:
      return "info";
  }
}

function formatTime(date: Date): string {
  return date.toLocaleTimeString("en-US", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
  });
}

function formatDuration(totalSeconds: number): string {
  if (!Number.isFinite(totalSeconds) || totalSeconds < 0) {
    return "—";
  }
  if (totalSeconds === 0) {
    return "0s";
  }

  const hours = Math.floor(totalSeconds / 3600);
  const minutes = Math.floor((totalSeconds % 3600) / 60);
  const seconds = Math.floor(totalSeconds % 60);

  const segments: string[] = [];
  if (hours > 0) {
    segments.push(`${hours}h`);
  }
  if (minutes > 0 || hours > 0) {
    segments.push(`${minutes}m`);
  }
  if (hours === 0 && (minutes < 2 || seconds > 0)) {
    segments.push(`${seconds}s`);
  }

  return segments.join(" ") || "<1s";
}

function formatBytes(bytes?: number): string {
  if (bytes == null || Number.isNaN(bytes) || bytes < 0) {
    return "—";
  }
  if (bytes === 0) {
    return "0 B";
  }

  const units = ["B", "KB", "MB", "GB"];
  let value = bytes;
  let unitIndex = 0;

  while (value >= 1024 && unitIndex < units.length - 1) {
    value /= 1024;
    unitIndex += 1;
  }

  const precision = value >= 100 || unitIndex === 0 ? 0 : value >= 10 ? 1 : 2;
  return `${value.toFixed(precision)} ${units[unitIndex]}`;
}

function estimateEtaSeconds(
  start: Date | null,
  progress: number,
  now: Date = new Date()
): number | null {
  if (!start || Number.isNaN(start.getTime())) {
    return null;
  }
  if (progress <= 0 || progress >= 100) {
    return progress >= 100 ? 0 : null;
  }

  const elapsed = Math.max(0, Math.floor((now.getTime() - start.getTime()) / 1000));
  if (elapsed === 0) {
    return null;
  }

  const estimatedTotal = Math.round((elapsed / progress) * 100);
  const eta = Math.max(0, estimatedTotal - elapsed);
  return Number.isFinite(eta) ? eta : null;
}

function buildFileKey(details: Record<string, unknown>): string {
  const fileId = typeof details.file_id === "string" ? details.file_id : undefined;
  if (fileId) {
    return fileId;
  }
  const filename = typeof details.filename === "string" ? details.filename : undefined;
  const fileNumber = typeof details.file_number === "number" ? details.file_number : undefined;
  return [filename ?? "file", fileNumber ?? "0"].join("-");
}

function extractRedactionTotal(value: unknown): number | undefined {
  if (typeof value === "number") {
    return value;
  }
  if (value && typeof value === "object") {
    const counts = Object.values(value as Record<string, unknown>);
    return counts.reduce<number>((sum, current) => {
      return sum + (typeof current === "number" ? current : 0);
    }, 0);
  }
  return undefined;
}

function arraysDifferent(first: string[], second: string[]): boolean {
  if (first.length !== second.length) {
    return true;
  }
  for (let index = 0; index < first.length; index += 1) {
    if (first[index] !== second[index]) {
      return true;
    }
  }
  return false;
}

function hasSummaryChanged(existing: FilePreviewSummary | undefined, next: FilePreviewSummary): boolean {
  if (!existing) {
    return true;
  }
  if (
    existing.lineCount !== next.lineCount ||
    existing.chunkCount !== next.chunkCount ||
    existing.errorCount !== next.errorCount ||
    existing.warningCount !== next.warningCount ||
    existing.criticalCount !== next.criticalCount ||
    existing.infoCount !== next.infoCount
  ) {
    return true;
  }
  if (
    existing.redactionApplied !== next.redactionApplied ||
    existing.redactionFailsafeTriggered !== next.redactionFailsafeTriggered
  ) {
    return true;
  }
  if (
    arraysDifferent(existing.sampleHead, next.sampleHead) ||
    arraysDifferent(existing.sampleTail, next.sampleTail) ||
    arraysDifferent(existing.topKeywords, next.topKeywords) ||
    arraysDifferent(existing.redactionValidationWarnings, next.redactionValidationWarnings)
  ) {
    return true;
  }

  const existingKeys = Object.keys(existing.redactionCounts).sort();
  const nextKeys = Object.keys(next.redactionCounts).sort();
  if (existingKeys.length !== nextKeys.length) {
    return true;
  }
  for (let index = 0; index < nextKeys.length; index += 1) {
    const key = nextKeys[index];
    if (existingKeys[index] !== key || existing.redactionCounts[key] !== next.redactionCounts[key]) {
      return true;
    }
  }

  if (existing.fileSize !== next.fileSize || existing.contentType !== next.contentType) {
    return true;
  }
  if (existing.checksum !== next.checksum) {
    return true;
  }
  return false;
}

function StepStatusIcon({ status }: { status: StepStatus }) {
  const base = "flex h-6 w-6 items-center justify-center rounded-full border text-xs font-semibold";
  switch (status) {
    case "completed":
      return (
        <div className={`${base} border-green-500 bg-green-500/10 text-green-400`}>
          ✓
        </div>
      );
    case "in-progress":
      return (
        <div className={`${base} border-fluent-blue-400 bg-fluent-blue-500/10 text-fluent-blue-300 animate-pulse`}>
          •
        </div>
      );
    case "failed":
      return (
        <div className={`${base} border-red-500 bg-red-500/10 text-red-400`}>
          !
        </div>
      );
    default:
      return (
        <div className={`${base} border-dark-border bg-transparent text-dark-text-tertiary`}>
          •
        </div>
      );
  }
}

const STREAMING_HEALTH_STATES = {
  healthy: {
    tone: "text-green-400",
    background: "bg-green-500/10",
    border: "border-green-500/40",
    icon: "✓",
    message: "Live updates are connected.",
  },
  warning: {
    tone: "text-yellow-300",
    background: "bg-yellow-500/10",
    border: "border-yellow-500/40",
    icon: "⚠",
    message: "Experiencing temporary interruptions. Retrying...",
  },
  error: {
    tone: "text-red-300",
    background: "bg-red-500/10",
    border: "border-red-500/40",
    icon: "!",
    message: "Live stream disconnected. Using fallback updates.",
  },
} as const;

type StreamingHealthState = keyof typeof STREAMING_HEALTH_STATES;

const LOG_VARIANT_STYLES: Record<MessageVariant, string> = {
  info: "bg-dark-text-tertiary",
  success: "bg-green-400",
  warning: "bg-yellow-400",
  error: "bg-red-400",
};

const LOG_TEXT_STYLES: Record<MessageVariant, string> = {
  info: "text-dark-text-secondary",
  success: "text-green-400",
  warning: "text-yellow-300",
  error: "text-red-400",
};

const FILE_STATUS_LABELS: Record<FileProgressStatus, string> = {
  pending: "Pending",
  processing: "Processing",
  completed: "Completed",
  quarantined: "Quarantined",
};

const FILE_STATUS_CLASSES: Record<FileProgressStatus, string> = {
  pending: "border border-dark-border/50 bg-dark-bg-tertiary/70 text-dark-text-tertiary",
  processing: "border border-fluent-blue-500/40 bg-fluent-blue-500/10 text-fluent-blue-200",
  completed: "border border-green-500/40 bg-green-500/10 text-green-300",
  quarantined: "border border-red-500/50 bg-red-500/10 text-red-300",
};

const FILE_SECURITY_LABELS: Record<FileSecurityState, string> = {
  clear: "Clean",
  redacted: "Redacted",
  warnings: "Warnings",
  quarantined: "Quarantined",
};

const FILE_SECURITY_CLASSES: Record<FileSecurityState, string> = {
  clear: "border border-dark-border/40 bg-dark-bg-tertiary/80 text-dark-text-secondary",
  redacted: "border border-fluent-blue-500/40 bg-fluent-blue-500/10 text-fluent-blue-200",
  warnings: "border border-yellow-500/40 bg-yellow-500/10 text-yellow-200",
  quarantined: "border border-red-500/50 bg-red-500/10 text-red-300",
};

export function StreamingChat({ jobId, onStatusChange }: StreamingChatProps) {
  const [steps, setSteps] = useState<StepState[]>(createInitialSteps);
  const [logEntries, setLogEntries] = useState<LogEntry[]>([]);
  const [status, setStatus] = useState<string>("idle");
  const statusRef = useRef<string>("idle");
  const [isConnected, setIsConnected] = useState(false);
  const [lastHeartbeat, setLastHeartbeat] = useState<Date | null>(null);
  const [progressPercentage, setProgressPercentage] = useState<number>(0);
  const [fileProgressMap, setFileProgressMap] = useState<Record<string, FileProgressEntry>>({});
  const [totalFiles, setTotalFiles] = useState<number | null>(null);
  const jobStartTimeRef = useRef<Date | null>(null);
  const [elapsedSeconds, setElapsedSeconds] = useState(0);
  const [etaSeconds, setEtaSeconds] = useState<number | null>(null);
  const [fileSummaries, setFileSummaries] = useState<Record<string, FilePreviewSummary>>({});
  const [selectedFileKey, setSelectedFileKey] = useState<string | null>(null);
  
  // PII Protection Stats
  const [piiStats, setPiiStats] = useState<{
    totalRedacted: number;
    filesScanned: number;
    validationWarnings: number;
  }>({ totalRedacted: 0, filesScanned: 0, validationWarnings: 0 });

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const reconnectNotifiedRef = useRef(false);
  const lastEventTimestampRef = useRef<string | null>(null);
  const seenEventIdsRef = useRef<Set<string>>(new Set());
  const pollingActiveRef = useRef(false); // Track if polling is already running
  const pollTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const consecutiveFailuresRef = useRef(0);
  const [pollingStatus, setPollingStatus] = useState<"idle" | "polling" | "error" | "stopped" | "completed">("idle");
  const [lastError, setLastError] = useState<string | null>(null);
  const [pendingRetryDelay, setPendingRetryDelay] = useState<number | null>(null);
  const [pollingSessionId, setPollingSessionId] = useState(0);
  const previousJobIdRef = useRef<string | null>(null);
  const progressBarRef = useRef<HTMLDivElement | null>(null);
  const [isCancelling, setIsCancelling] = useState(false);
  const [isRetrying, setIsRetrying] = useState(false);
  const [isPausing, setIsPausing] = useState(false);
  const [isResuming, setIsResuming] = useState(false);
  const [jobErrorMessage, setJobErrorMessage] = useState<string | null>(null);
  const apiBaseUrl = useMemo(() => process.env.NEXT_PUBLIC_API_BASE_URL || "", []);
  const eventSourceRef = useRef<EventSource | null>(null);
  const sseRestartTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const [sseStatus, setSseStatus] = useState<SseStatus>("idle");
  const sseStatusRef = useRef<SseStatus>("idle");
  const [sseSessionId, setSseSessionId] = useState(0);
  const sseConnectedAnnouncementRef = useRef(false);

  const fileProgressEntries = useMemo(() => {
    return Object.values(fileProgressMap).sort((a, b) => {
      const aPosition = a.position ?? Number.MAX_SAFE_INTEGER;
      const bPosition = b.position ?? Number.MAX_SAFE_INTEGER;
      if (aPosition !== bPosition) {
        return aPosition - bPosition;
      }
      return a.name.localeCompare(b.name);
    });
  }, [fileProgressMap]);

  useEffect(() => {
    if (fileProgressEntries.length === 0) {
      setSelectedFileKey(null);
      return;
    }

    setSelectedFileKey((prev) => {
      if (prev && fileProgressEntries.some((entry) => entry.key === prev)) {
        return prev;
      }
      return fileProgressEntries[0]?.key ?? prev ?? null;
    });
  }, [fileProgressEntries]);

  const derivedTotalFiles = useMemo(() => {
    if (typeof totalFiles === "number") {
      return totalFiles;
    }
    const maxReported = fileProgressEntries.reduce((max, entry) => {
      const candidate = entry.total ?? entry.position ?? 0;
      return candidate > max ? candidate : max;
    }, 0);
    if (maxReported > 0) {
      return maxReported;
    }
    return fileProgressEntries.length > 0 ? fileProgressEntries.length : null;
  }, [fileProgressEntries, totalFiles]);

  const filesCompletedCount = useMemo(() => {
    return fileProgressEntries.filter((entry) => entry.status === "completed" || entry.status === "quarantined").length;
  }, [fileProgressEntries]);

  const filesInProgressCount = useMemo(() => {
    return fileProgressEntries.filter((entry) => entry.status === "processing").length;
  }, [fileProgressEntries]);

  const selectedFileEntry = useMemo(() => {
    if (!selectedFileKey) {
      return undefined;
    }
    return fileProgressEntries.find((entry) => entry.key === selectedFileKey);
  }, [fileProgressEntries, selectedFileKey]);

  const selectedPreview = selectedFileKey ? fileSummaries[selectedFileKey] : undefined;

  const selectedPreviewRedactions = useMemo(() => {
    if (!selectedPreview) {
      return 0;
    }
    return Object.values(selectedPreview.redactionCounts).reduce((total, value) => total + value, 0);
  }, [selectedPreview]);

  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, []);

  // Poll job status with exponential backoff and manual retry support.
  useEffect(() => {
    scrollToBottom();
  }, [logEntries, scrollToBottom]);

  useEffect(() => {
    if (progressBarRef.current) {
      progressBarRef.current.style.width = `${progressPercentage}%`;
    }
  }, [progressPercentage]);

  useEffect(() => {
    if (!jobStartTimeRef.current) {
      setElapsedSeconds(0);
      if (!jobId) {
        setEtaSeconds(null);
      }
      return;
    }

    const updateTimers = () => {
      if (!jobStartTimeRef.current) {
        return;
      }
      const now = new Date();
      const elapsed = Math.max(
        0,
        Math.floor((now.getTime() - jobStartTimeRef.current.getTime()) / 1000)
      );
      setElapsedSeconds(elapsed);

      if (status === "running") {
        const eta = estimateEtaSeconds(jobStartTimeRef.current, progressPercentage, now);
        setEtaSeconds(eta);
      } else if (["completed", "failed", "cancelled"].includes(status) || progressPercentage >= 100) {
        setEtaSeconds(0);
      } else {
        setEtaSeconds(null);
      }
    };

    updateTimers();

    if (["completed", "failed", "cancelled"].includes(status) || !jobId) {
      return;
    }

    const intervalId = window.setInterval(updateTimers, 1000);
    return () => {
      window.clearInterval(intervalId);
    };
  }, [jobId, progressPercentage, status]);

  const pushLog = useCallback(
    (content: string, variant: MessageVariant = "info", timestamp = new Date()) => {
      setLogEntries((prev) => {
        // Skip duplicate consecutive messages
        if (prev.length > 0 && prev[prev.length - 1].content === content) {
          return prev;
        }
        
        const next: LogEntry[] = [
          ...prev,
          {
            id: `${Date.now()}-${Math.random().toString(16).slice(2)}`,
            content,
            variant,
            timestamp,
          },
        ];
        if (next.length > MAX_LOG_ITEMS) {
          next.splice(0, next.length - MAX_LOG_ITEMS);
        }
        return next;
      });
    },
    []
  );

  const stopPolling = useCallback(() => {
    if (pollTimeoutRef.current) {
      clearTimeout(pollTimeoutRef.current);
      pollTimeoutRef.current = null;
    }
    pollingActiveRef.current = false;
  }, []);

  const syncFileSummaries = useCallback((rawSummaries: unknown) => {
    if (!Array.isArray(rawSummaries)) {
      return;
    }

    const normalized: FilePreviewSummary[] = [];
    rawSummaries.forEach((item) => {
      if (!item || typeof item !== "object") {
        return;
      }
      const summary = item as Record<string, unknown>;
      const fileId = typeof summary.file_id === "string" ? summary.file_id : undefined;
      if (!fileId) {
        return;
      }

      const rawHead = Array.isArray(summary.sample_head)
        ? summary.sample_head.map((value) => String(value))
        : [];
      const rawTail = Array.isArray(summary.sample_tail)
        ? summary.sample_tail.map((value) => String(value))
        : [];
      const rawKeywords = Array.isArray(summary.top_keywords)
        ? summary.top_keywords.map((value) => String(value))
        : [];
      const rawWarnings = Array.isArray(summary.redaction_validation_warnings)
        ? summary.redaction_validation_warnings.map((value) => String(value))
        : [];
      const counts: Record<string, number> = {};
      if (summary.redaction_counts && typeof summary.redaction_counts === "object") {
        Object.entries(summary.redaction_counts as Record<string, unknown>).forEach(([key, value]) => {
          if (typeof value === "number") {
            counts[key] = value;
          }
        });
      }

      normalized.push({
        fileId,
        filename: typeof summary.filename === "string" ? summary.filename : fileId,
        lineCount: typeof summary.line_count === "number" ? summary.line_count : 0,
        chunkCount: typeof summary.chunk_count === "number" ? summary.chunk_count : 0,
        sampleHead: rawHead,
        sampleTail: rawTail,
        topKeywords: rawKeywords,
        errorCount: typeof summary.error_count === "number" ? summary.error_count : 0,
        warningCount: typeof summary.warning_count === "number" ? summary.warning_count : 0,
        criticalCount: typeof summary.critical_count === "number" ? summary.critical_count : 0,
        infoCount: typeof summary.info_count === "number" ? summary.info_count : 0,
        redactionApplied: summary.redaction_applied === true,
        redactionCounts: counts,
        redactionFailsafeTriggered: summary.redaction_failsafe_triggered === true,
        redactionValidationWarnings: rawWarnings,
        checksum: typeof summary.checksum === "string" ? summary.checksum : undefined,
        fileSize: typeof summary.file_size === "number" ? summary.file_size : undefined,
        contentType: typeof summary.content_type === "string" ? summary.content_type : undefined,
      });
    });

    setFileSummaries((prev) => {
      if (normalized.length === 0) {
        return Object.keys(prev).length > 0 ? {} : prev;
      }

      const next: Record<string, FilePreviewSummary> = {};
      let changed = false;

      normalized.forEach((preview) => {
        const existing = prev[preview.fileId];
        if (hasSummaryChanged(existing, preview)) {
          changed = true;
          next[preview.fileId] = preview;
        } else if (existing) {
          next[preview.fileId] = existing;
        } else {
          next[preview.fileId] = preview;
          changed = true;
        }
      });

      if (!changed) {
        const prevKeys = Object.keys(prev).sort();
        const nextKeys = Object.keys(next).sort();
        if (prevKeys.length !== nextKeys.length) {
          changed = true;
        } else {
          for (let index = 0; index < prevKeys.length; index += 1) {
            if (prevKeys[index] !== nextKeys[index]) {
              changed = true;
              break;
            }
          }
        }
      }

      return changed ? next : prev;
    });
  }, []);

  const updateSseStatus = useCallback((next: SseStatus) => {
    sseStatusRef.current = next;
    setSseStatus(next);
  }, []);

  const closeEventSource = useCallback(() => {
    if (sseRestartTimeoutRef.current) {
      clearTimeout(sseRestartTimeoutRef.current);
      sseRestartTimeoutRef.current = null;
    }
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
    }
  }, []);

  const scheduleSseRestart = useCallback(
    (delayMs: number) => {
      if (sseRestartTimeoutRef.current) {
        clearTimeout(sseRestartTimeoutRef.current);
      }
      sseRestartTimeoutRef.current = setTimeout(() => {
        sseRestartTimeoutRef.current = null;
        setSseSessionId((prev) => prev + 1);
      }, delayMs);
    },
    [setSseSessionId]
  );

  const updateStep = useCallback(
    (
      stepId: string,
      nextStatus: StepStatus,
      options: {
        label?: string;
        message?: string;
        details?: Record<string, unknown>;
        timestamp?: Date;
      } = {}
    ) => {
      setSteps((prev) => {
        const timestamp = options.timestamp;
        let updated = false;

        const mapped = prev.map((step) => {
          if (step.id !== stepId) {
            return step;
          }

          updated = true;
          const currentPriority = STEP_STATUS_PRIORITY[step.status];
          const incomingPriority = STEP_STATUS_PRIORITY[nextStatus];
          let statusToApply = step.status;

          if (nextStatus === "failed") {
            statusToApply = "failed";
          } else if (incomingPriority > currentPriority) {
            statusToApply = nextStatus;
          } else if (nextStatus === "in-progress" && step.status === "pending") {
            statusToApply = "in-progress";
          }

          return {
            ...step,
            label: options.label ?? step.label,
            status: statusToApply,
            lastMessage: options.message ?? step.lastMessage,
            lastUpdated: options.message || timestamp ? timestamp ?? new Date() : step.lastUpdated,
            details: options.details ?? step.details,
          };
        });

        if (!updated) {
          mapped.push({
            id: stepId,
            label: options.label ?? stepId,
            description: "",
            status: nextStatus,
            lastMessage: options.message,
            lastUpdated: options.timestamp,
            details: options.details,
          });
        }

        return mapped;
      });
    },
    []
  );

  const handleStatusUpdate = useCallback(
    (nextStatus: string) => {
      statusRef.current = nextStatus;
      setStatus((prev) => (prev === nextStatus ? prev : nextStatus));
      onStatusChange?.(nextStatus);
      setIsPausing(false);
      setIsResuming(false);
      if (nextStatus === "running" || nextStatus === "queued" || nextStatus === "pending") {
        setJobErrorMessage(null);
      }
    },
    [onStatusChange]
  );

  const processJobEvent = useCallback(
    (payload: JobEventPayload) => {
      const timestamp = payload.created_at ? new Date(payload.created_at) : new Date();
      const data = (payload.data ?? {}) as Record<string, unknown>;

      switch (payload.event_type) {
        case "created": {
          handleStatusUpdate("queued");
          updateStep("classification", "pending", {
            message: "Files queued for analysis.",
            details: data,
            timestamp,
          });
          pushLog("Files queued for analysis.", "info", timestamp);
          setJobErrorMessage(null);
          break;
        }
        case "ready": {
          const readyMessage = typeof data.message === "string" ? data.message : "Job ready for processing.";
          pushLog(readyMessage, "info", timestamp);
          break;
        }
        case "running":
        case "started": {
          handleStatusUpdate("running");
          if (!jobStartTimeRef.current) {
            jobStartTimeRef.current = timestamp;
            setElapsedSeconds(0);
            setEtaSeconds(null);
          }
          updateStep("classification", "in-progress", { timestamp });
          pushLog("Analysis started.", "info", timestamp);
          setJobErrorMessage(null);
          setEtaSeconds(null);
          break;
        }
        case "analysis-progress": {
          const stepId = typeof data.step === "string" ? data.step : "unknown";
          const rawStatus = typeof data.status === "string" ? data.status : "started";
          const label = typeof data.label === "string" ? data.label : undefined;
          const details = (data.details && typeof data.details === "object")
            ? (data.details as Record<string, unknown>)
            : undefined;
          let stepStatus = normaliseProgressStatus(rawStatus);

          // Update progress percentage if available
          if (details && typeof details.progress === "number") {
            setProgressPercentage(details.progress);
          }

          // Special handling for completion event
          if (stepId === "completed" && stepStatus === "completed") {
            handleStatusUpdate("completed");
            setProgressPercentage(100);
          }

          // Check if this is a partial completion (more files to process)
          if (details) {
            const fileNumber = details.file_number;
            const totalFiles = details.total_files;
            if (
              stepStatus === "completed" &&
              typeof fileNumber === "number" &&
              typeof totalFiles === "number" &&
              totalFiles > 0 &&
              fileNumber < totalFiles
            ) {
              stepStatus = "in-progress";
            }
          }

          const message = typeof data.message === "string"
            ? data.message
            : `${label ?? stepId} ${
                stepStatus === "completed"
                  ? "completed."
                  : stepStatus === "failed"
                  ? "failed."
                  : "in progress..."
              }`;

          updateStep(stepId, stepStatus, {
            label,
            message,
            details,
            timestamp,
          });

          if (message) {
            pushLog(message, variantForStatus(stepStatus), timestamp);
          }
          if (stepStatus !== "failed") {
            setJobErrorMessage(null);
          }
          break;
        }
        case "file-processing-started": {
          const filename = typeof data.filename === "string" ? data.filename : "uploaded file";
          const fileNumber = typeof data.file_number === "number" ? data.file_number : undefined;
          const totalFiles = typeof data.total_files === "number" ? data.total_files : undefined;
          const prefix =
            fileNumber !== undefined && totalFiles !== undefined
              ? `${fileNumber}/${totalFiles} `
              : "";
          const fileIdValue = typeof data.file_id === "string" ? data.file_id : undefined;

          if (typeof totalFiles === "number" && totalFiles > 0) {
            setTotalFiles((prev) => (prev === null ? totalFiles : Math.max(prev, totalFiles)));
          }

          const fileKey = buildFileKey(data);
          const displayName = typeof data.filename === "string" ? data.filename : fileKey;
          setFileProgressMap((prev) => ({
            ...prev,
            [fileKey]: {
              key: fileKey,
              fileId: fileIdValue ?? prev[fileKey]?.fileId,
              name: displayName,
              status: "processing",
              position: fileNumber ?? prev[fileKey]?.position,
              total: totalFiles ?? prev[fileKey]?.total,
              startedAt: timestamp,
              completedAt: prev[fileKey]?.completedAt,
              chunks: prev[fileKey]?.chunks,
              redactionTotal: prev[fileKey]?.redactionTotal,
              warningCount: prev[fileKey]?.warningCount,
              errorCount: prev[fileKey]?.errorCount,
              securityState: prev[fileKey]?.securityState ?? "clear",
              validationWarnings: prev[fileKey]?.validationWarnings,
            },
          }));

          pushLog(`Processing ${prefix}${filename}...`, "info", timestamp);
          updateStep("redaction", "in-progress", { details: data, timestamp });
          
          // Track file scanned for PII
          setPiiStats(prev => ({ ...prev, filesScanned: prev.filesScanned + 1 }));
          break;
        }
        case "file-processing-completed": {
          const filename = typeof data.filename === "string" ? data.filename : "uploaded file";
          const chunks = typeof data.chunks === "number" ? data.chunks : undefined;
          const validationList = Array.isArray(data.validation_warnings)
            ? data.validation_warnings.map((item) => String(item))
            : [];
          const redactionTotal = extractRedactionTotal(data.redaction_hits) ?? 0;
          const totalFiles = typeof data.total_files === "number" ? data.total_files : undefined;
          const fileNumber = typeof data.file_number === "number" ? data.file_number : undefined;
          const errorCount = typeof data.errors === "number" ? data.errors : undefined;
          const warningCount = typeof data.warnings === "number" ? data.warnings : validationList.length;
          const failsafe = data.pii_failsafe_triggered === true || data.failsafe_triggered === true;
          const redactionApplied = data.pii_redacted === true || redactionTotal > 0;
          const fileIdValue = typeof data.file_id === "string" ? data.file_id : undefined;

          if (typeof totalFiles === "number" && totalFiles > 0) {
            setTotalFiles((prev) => (prev === null ? totalFiles : Math.max(prev, totalFiles)));
          }

          const fileKey = buildFileKey(data);
          const displayName = typeof data.filename === "string" ? data.filename : fileKey;
          const securityState: FileSecurityState = failsafe
            ? "quarantined"
            : validationList.length > 0
            ? "warnings"
            : redactionApplied
            ? "redacted"
            : "clear";
          const status: FileProgressStatus = failsafe ? "quarantined" : "completed";

          setFileProgressMap((prev) => ({
            ...prev,
            [fileKey]: {
              key: fileKey,
              fileId: fileIdValue ?? prev[fileKey]?.fileId,
              name: displayName,
              status,
              position: fileNumber ?? prev[fileKey]?.position,
              total: totalFiles ?? prev[fileKey]?.total,
              startedAt: prev[fileKey]?.startedAt ?? timestamp,
              completedAt: timestamp,
              chunks: chunks ?? prev[fileKey]?.chunks,
              redactionTotal: redactionTotal ?? prev[fileKey]?.redactionTotal,
              warningCount,
              errorCount,
              securityState,
              validationWarnings: validationList,
            },
          }));
          
          // Update PII stats
          if (redactionTotal > 0 || validationList.length > 0) {
            setPiiStats(prev => ({
              ...prev,
              totalRedacted: prev.totalRedacted + redactionTotal,
              validationWarnings: prev.validationWarnings + validationList.length
            }));
          }
          
          const message =
            chunks !== undefined
              ? `Finished ${filename} (${chunks} chunk${chunks === 1 ? "" : "s"}).`
              : `Finished ${filename}.`;
          pushLog(message, "success", timestamp);
          updateStep("storage", "in-progress", { details: data, timestamp });
          break;
        }
        case "analysis-phase": {
          const phase = typeof data.phase === "string" ? data.phase : "";
          const phaseStatus = typeof data.status === "string" ? data.status : "";
          if (phase === "llm") {
            updateStep("llm", normaliseProgressStatus(phaseStatus), { timestamp });
          }
          break;
        }
        case "completed":
        case "complete": {
          handleStatusUpdate("completed");
          if (jobStartTimeRef.current) {
            const elapsed = Math.max(
              0,
              Math.floor((timestamp.getTime() - jobStartTimeRef.current.getTime()) / 1000)
            );
            setElapsedSeconds(elapsed);
            setEtaSeconds(0);
          }
          updateStep("report", "completed", {
            message: "Analysis completed successfully.",
            timestamp,
            details: data,
          });
          pushLog("Analysis completed successfully.", "success", timestamp);
          setJobErrorMessage(null);
          setEtaSeconds(0);
          break;
        }
        case "failed":
        case "error": {
          handleStatusUpdate("failed");
          if (jobStartTimeRef.current) {
            const elapsed = Math.max(
              0,
              Math.floor((timestamp.getTime() - jobStartTimeRef.current.getTime()) / 1000)
            );
            setElapsedSeconds(elapsed);
            setEtaSeconds(0);
          }
          const errorMessage =
            typeof data.error === "string"
              ? data.error
              : typeof data.message === "string"
              ? data.message
              : "Analysis failed.";
          updateStep("report", "failed", {
            message: errorMessage,
            timestamp,
            details: data,
          });
          pushLog(errorMessage, "error", timestamp);
          setJobErrorMessage(errorMessage);
          setEtaSeconds(0);
          break;
        }
        case "cancelled": {
          handleStatusUpdate("cancelled");
          if (jobStartTimeRef.current) {
            const elapsed = Math.max(
              0,
              Math.floor((timestamp.getTime() - jobStartTimeRef.current.getTime()) / 1000)
            );
            setElapsedSeconds(elapsed);
            setEtaSeconds(0);
          }
          const reason =
            typeof data.reason === "string" ? data.reason : "Analysis cancelled.";
          updateStep("report", "failed", {
            message: reason,
            timestamp,
            details: data,
          });
          pushLog(reason, "warning", timestamp);
          setJobErrorMessage(reason);
          setEtaSeconds(0);
          break;
        }
        case "paused": {
          handleStatusUpdate("paused");
          const reason = typeof data.reason === "string" ? data.reason : "Analysis paused.";
          pushLog(reason, "warning", timestamp);
          setEtaSeconds(null);
          break;
        }
        case "resumed": {
          handleStatusUpdate("running");
          const resumeMessage =
            typeof data.message === "string" ? data.message : "Analysis resumed.";
          pushLog(resumeMessage, "info", timestamp);
          setJobErrorMessage(null);
          break;
        }
        default:
          break;
      }
    },
    [handleStatusUpdate, pushLog, updateStep]
  );

  const handleManualRetry = useCallback(() => {
    if (!jobId) {
      return;
    }

    stopPolling();
    closeEventSource();
    updateSseStatus("idle");
    sseConnectedAnnouncementRef.current = false;
    setSseSessionId((prev) => prev + 1);
    setPendingRetryDelay(null);
    setLastError(null);
    setPollingStatus("polling");
    setIsConnected(false);
    consecutiveFailuresRef.current = 0;
    reconnectNotifiedRef.current = false;
    pushLog("Retrying connection...", "info", new Date());
    setJobErrorMessage(null);
    setPollingSessionId((prev) => prev + 1);
  }, [
    closeEventSource,
    jobId,
    pushLog,
    setSseSessionId,
    stopPolling,
    updateSseStatus,
  ]);

  const resetForRequeue = useCallback(() => {
    setSteps(createInitialSteps());
    setProgressPercentage(0);
    setFileProgressMap({});
    setTotalFiles(null);
    setFileSummaries({});
    setSelectedFileKey(null);
    jobStartTimeRef.current = null;
    setElapsedSeconds(0);
    setEtaSeconds(null);
    setPiiStats({ totalRedacted: 0, filesScanned: 0, validationWarnings: 0 });
    lastEventTimestampRef.current = null;
    seenEventIdsRef.current.clear();
    statusRef.current = "pending";
    setStatus("pending");
    setIsConnected(false);
    setPollingStatus("polling");
    setLastError(null);
    setPendingRetryDelay(null);
    reconnectNotifiedRef.current = false;
    consecutiveFailuresRef.current = 0;
    closeEventSource();
    updateSseStatus("idle");
    sseConnectedAnnouncementRef.current = false;
    setSseSessionId((prev) => prev + 1);
    setJobErrorMessage(null);
    setIsPausing(false);
    setIsResuming(false);
  }, [closeEventSource, setSseSessionId, updateSseStatus]);

  const handlePauseJob = useCallback(async () => {
    if (!jobId || isPausing || status !== "running") {
      return;
    }

    setIsPausing(true);
    pushLog("Pausing live analysis...", "warning", new Date());

    try {
      const response = await fetch(`${apiBaseUrl}/api/jobs/${jobId}/pause`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ reason: "Paused from StreamingChat UI" }),
      });

      let payload: Record<string, unknown> | null = null;
      try {
        payload = await response.json();
      } catch {
        payload = null;
      }

      if (!response.ok) {
        const message =
          (payload?.detail as string) ||
          (payload?.message as string) ||
          `Pause failed (${response.status})`;
        throw new Error(message);
      }

      const confirmation =
        (payload?.message as string) || "Job paused.";
      pushLog(confirmation, "warning", new Date());
    } catch (error) {
      const message =
        error instanceof Error ? error.message : "Unable to pause job.";
      pushLog(`Pause failed: ${message}`, "error", new Date());
    } finally {
      setIsPausing(false);
    }
  }, [apiBaseUrl, isPausing, jobId, pushLog, status]);

  const handleResumeJob = useCallback(async () => {
    if (!jobId || isResuming || status !== "paused") {
      return;
    }

    setIsResuming(true);
    pushLog("Resuming live analysis...", "info", new Date());

    try {
      const response = await fetch(`${apiBaseUrl}/api/jobs/${jobId}/resume`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ note: "Resumed from StreamingChat UI" }),
      });

      let payload: Record<string, unknown> | null = null;
      try {
        payload = await response.json();
      } catch {
        payload = null;
      }

      if (!response.ok) {
        const message =
          (payload?.detail as string) ||
          (payload?.message as string) ||
          `Resume failed (${response.status})`;
        throw new Error(message);
      }

      const confirmation =
        (payload?.message as string) || "Job resumed.";
      pushLog(confirmation, "info", new Date());
    } catch (error) {
      const message =
        error instanceof Error ? error.message : "Unable to resume job.";
      pushLog(`Resume failed: ${message}`, "error", new Date());
    } finally {
      setIsResuming(false);
    }
  }, [apiBaseUrl, isResuming, jobId, pushLog, status]);

  const handleCancelJob = useCallback(async () => {
    if (!jobId || isCancelling) {
      return;
    }

    if (["completed", "failed", "cancelled"].includes(status)) {
      return;
    }

    setIsCancelling(true);
    pushLog("Requesting job cancellation...", "warning", new Date());

    try {
      const response = await fetch(`${apiBaseUrl}/api/jobs/${jobId}/cancel`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ reason: "Cancelled from StreamingChat UI" }),
      });

      let payload: Record<string, unknown> | null = null;
      try {
        payload = await response.json();
      } catch {
        payload = null;
      }

      if (!response.ok) {
        const message =
          (payload?.detail as string) ||
          (payload?.message as string) ||
          `Cancellation failed (${response.status})`;
        throw new Error(message);
      }

      const confirmation =
        (payload?.message as string) || "Cancellation request submitted.";
      pushLog(confirmation, "warning", new Date());
    } catch (error) {
      const message =
        error instanceof Error ? error.message : "Unable to cancel job.";
      pushLog(`Cancel failed: ${message}`, "error", new Date());
    } finally {
      setIsCancelling(false);
    }
  }, [apiBaseUrl, isCancelling, jobId, pushLog, status]);

  const handleRetryJob = useCallback(async () => {
    if (!jobId || isRetrying) {
      return;
    }

    if (!(["completed", "failed", "cancelled"].includes(status))) {
      return;
    }

    setIsRetrying(true);
    pushLog("Re-queuing analysis job...", "info", new Date());

    try {
      const response = await fetch(`${apiBaseUrl}/api/jobs/${jobId}/retry`, {
        method: "POST",
      });

      let payload: Record<string, unknown> | null = null;
      try {
        payload = await response.json();
      } catch {
        payload = null;
      }

      if (!response.ok) {
        const message =
          (payload?.detail as string) ||
          (payload?.message as string) ||
          `Retry failed (${response.status})`;
        throw new Error(message);
      }

      const confirmation =
        (payload?.message as string) || "Job queued for retry.";
      pushLog(confirmation, "success", new Date());
      resetForRequeue();
      pushLog("Waiting for new run to begin...", "info", new Date());
      previousJobIdRef.current = null;
      stopPolling();
      setPollingSessionId((prev) => prev + 1);
    } catch (error) {
      const message =
        error instanceof Error ? error.message : "Unable to retry job.";
      pushLog(`Retry failed: ${message}`, "error", new Date());
    } finally {
      setIsRetrying(false);
    }
  }, [apiBaseUrl, jobId, isRetrying, pushLog, resetForRequeue, status, stopPolling]);

  useEffect(() => {
    if (!jobId) {
      closeEventSource();
      updateSseStatus("idle");
      sseConnectedAnnouncementRef.current = false;
      return;
    }

    if (["completed", "failed", "cancelled"].includes(statusRef.current)) {
      return;
    }

    // Check if SSE is disabled via environment variable
    const sseDisabled = process.env.NEXT_PUBLIC_DISABLE_SSE === 'true';
    
    if (sseDisabled || typeof window === "undefined" || typeof window.EventSource === "undefined") {
      if (sseStatusRef.current !== "unsupported") {
        pushLog(
          sseDisabled ? "SSE disabled, using polling for updates." : "Browser does not support live updates. Falling back to polling updates.",
          "warning",
          new Date()
        );
        setPollingSessionId((prev) => prev + 1);
      }
      updateSseStatus("unsupported");
      return;
    }

    closeEventSource();

    const basePrefix = apiBaseUrl ? apiBaseUrl.replace(/\/$/, "") : "";
    const apiPrefix = basePrefix || "";
  const streamUrl = `${apiPrefix}/api/sse/jobs/${jobId}?session=${sseSessionId}`;

    updateSseStatus("connecting");
    setIsConnected(false);
    setPendingRetryDelay(null);
    setLastError(null);

    let source: EventSource;
    try {
      source = new window.EventSource(streamUrl, { withCredentials: true });
    } catch (error) {
      updateSseStatus("error");
      if (!reconnectNotifiedRef.current) {
        pushLog(
          "Unable to establish live stream. Falling back to polling updates.",
          "warning",
          new Date()
        );
        reconnectNotifiedRef.current = true;
      }
      setLastError("Unable to establish live stream.");
      scheduleSseRestart(2000);
      setPollingSessionId((prev) => prev + 1);
      return;
    }

    eventSourceRef.current = source;

    const handleOpen = () => {
      const previous = sseStatusRef.current;
      updateSseStatus("open");
      setIsConnected(true);
      setPendingRetryDelay(null);
      setLastError(null);
      setPollingStatus("polling");
      const now = new Date();
      setLastHeartbeat(now);
      stopPolling();
      reconnectNotifiedRef.current = false;
      if (previous === "error" || previous === "closed") {
        pushLog("Live event stream reconnected.", "success", now);
      }
      sseConnectedAnnouncementRef.current = true;

      const jobUrl = `${apiPrefix}/api/jobs/${jobId}`;
      void (async () => {
        try {
          const response = await fetch(jobUrl);
          if (!response.ok) {
            return;
          }
          const snapshot = await response.json();
          if (snapshot.status) {
            handleStatusUpdate(snapshot.status);
          }
          const startedAtIso = typeof snapshot.started_at === "string" ? snapshot.started_at : null;
          if (startedAtIso && !jobStartTimeRef.current) {
            const startedAt = new Date(startedAtIso);
            if (!Number.isNaN(startedAt.getTime())) {
              jobStartTimeRef.current = startedAt;
            }
          }
        } catch {
          // Ignore snapshot errors; polling fallback will cover missing data.
        }
      })();
    };

    const handleConnectionInfo = (event: MessageEvent<string>) => {
      try {
        const payload = JSON.parse(event.data || "{}") as Record<string, unknown>;
        if (typeof payload.status === "string") {
          handleStatusUpdate(payload.status);
        }
      } catch {
        // Ignore malformed payloads.
      }
      setIsConnected(true);
      setLastHeartbeat(new Date());
    };

    const handleJobEvent = (event: MessageEvent<string>) => {
      try {
        const payload = JSON.parse(event.data) as JobEventPayload;
        if (payload?.id && seenEventIdsRef.current.has(payload.id)) {
          return;
        }
        if (payload?.id) {
          seenEventIdsRef.current.add(payload.id);
        }
        if (payload?.created_at) {
          const createdAt = new Date(payload.created_at);
          if (!Number.isNaN(createdAt.getTime())) {
            const lastRecorded = lastEventTimestampRef.current ? new Date(lastEventTimestampRef.current) : null;
            if (!lastRecorded || createdAt > lastRecorded) {
              lastEventTimestampRef.current = payload.created_at;
            }
          }
        }
        processJobEvent(payload);
        setIsConnected(true);
        setLastHeartbeat(new Date());
        setPendingRetryDelay(null);
        setLastError(null);
      } catch (err) {
        console.warn("Failed to parse job-event payload", err);
      }
    };

    const handleHeartbeat = (event: MessageEvent<string>) => {
      let timestamp = new Date();
      try {
        const payload = JSON.parse(event.data || "{}") as Record<string, unknown>;
        if (typeof payload.timestamp === "string") {
          const parsed = new Date(payload.timestamp);
          if (!Number.isNaN(parsed.getTime())) {
            timestamp = parsed;
          }
        }
        if (typeof payload.status === "string") {
          handleStatusUpdate(payload.status);
        }
      } catch {
        // Ignore malformed heartbeat payloads.
      }
      setLastHeartbeat(timestamp);
      setIsConnected(true);
    };

    const handleConnectionReset = (event: MessageEvent<string>) => {
      let reason = "stream reset";
      try {
        const payload = JSON.parse(event.data || "{}") as Record<string, unknown>;
        if (typeof payload.reason === "string") {
          reason = payload.reason;
        }
      } catch {
        // Ignore malformed reset payloads.
      }
      pushLog(`Live event stream resetting (${reason}).`, "info", new Date());
      updateSseStatus("closed");
      setIsConnected(false);
      setLastError(null);
      closeEventSource();
      if (["completed", "failed", "cancelled"].includes(statusRef.current)) {
        return;
      }
      scheduleSseRestart(500);
      setPollingSessionId((prev) => prev + 1);
    };

    const handleServerError = (event: MessageEvent<string>) => {
      let message = "Live stream error";
      try {
        const payload = JSON.parse(event.data || "{}") as Record<string, unknown>;
        if (typeof payload.error === "string") {
          message = payload.error;
        }
      } catch {
        // Ignore malformed error payloads.
      }
      setLastError(message);
      if (!reconnectNotifiedRef.current) {
        pushLog(`Live stream issue: ${message}`, "warning", new Date());
        reconnectNotifiedRef.current = true;
      }
    };

    source.onopen = handleOpen;
    source.onerror = () => {
      if (source.readyState === EventSource.CLOSED) {
        setIsConnected(false);
        if (["completed", "failed", "cancelled"].includes(statusRef.current)) {
          updateSseStatus("closed");
          closeEventSource();
          return;
        }
        updateSseStatus("error");
        if (!reconnectNotifiedRef.current) {
          pushLog(
            "Live stream disconnected. Falling back to polling until it recovers.",
            "warning",
            new Date()
          );
          reconnectNotifiedRef.current = true;
        }
        setLastError("Live stream disconnected");
        closeEventSource();
        scheduleSseRestart(2000);
        setPollingStatus("error");
        setPendingRetryDelay(null);
        setPollingSessionId((prev) => prev + 1);
      } else {
        updateSseStatus("connecting");
        setIsConnected(false);
      }
    };

    source.addEventListener("connection-info", handleConnectionInfo);
    source.addEventListener("job-event", handleJobEvent);
    source.addEventListener("heartbeat", handleHeartbeat);
    source.addEventListener("connection-reset", handleConnectionReset);
    source.addEventListener("error", handleServerError);

    return () => {
      source.removeEventListener("connection-info", handleConnectionInfo);
      source.removeEventListener("job-event", handleJobEvent);
      source.removeEventListener("heartbeat", handleHeartbeat);
      source.removeEventListener("connection-reset", handleConnectionReset);
      source.removeEventListener("error", handleServerError);
      source.close();
      if (eventSourceRef.current === source) {
        eventSourceRef.current = null;
      }
      if (sseRestartTimeoutRef.current) {
        clearTimeout(sseRestartTimeoutRef.current);
        sseRestartTimeoutRef.current = null;
      }
    };
  }, [
    apiBaseUrl,
    closeEventSource,
    handleStatusUpdate,
    jobId,
    processJobEvent,
    pushLog,
    scheduleSseRestart,
    setPollingSessionId,
    sseSessionId,
    stopPolling,
    updateSseStatus,
  ]);

  useEffect(() => {
    return () => {
      closeEventSource();
      stopPolling();
    };
  }, [closeEventSource, stopPolling]);

  useEffect(() => {
    if (!jobId) {
      stopPolling();
      setSteps(createInitialSteps());
      setLogEntries([]);
      statusRef.current = "idle";
      setStatus("idle");
      setIsConnected(false);
      setLastHeartbeat(null);
      setProgressPercentage(0);
      setFileProgressMap({});
      setTotalFiles(null);
      setFileSummaries({});
      setSelectedFileKey(null);
      jobStartTimeRef.current = null;
      setElapsedSeconds(0);
      setEtaSeconds(null);
      setPiiStats({ totalRedacted: 0, filesScanned: 0, validationWarnings: 0 });
      setPollingStatus("idle");
      setLastError(null);
      setPendingRetryDelay(null);
      reconnectNotifiedRef.current = false;
      lastEventTimestampRef.current = null;
      seenEventIdsRef.current.clear();
      consecutiveFailuresRef.current = 0;
      previousJobIdRef.current = null;
      setJobErrorMessage(null);
      return;
    }

    const isNewJob = previousJobIdRef.current !== jobId;
    if (isNewJob && pollingSessionId !== 0) {
      setPollingSessionId(0);
      return;
    }
    previousJobIdRef.current = jobId;

    if (sseStatus === "open") {
      stopPolling();
      setPollingStatus((prev) => (prev === "completed" ? prev : "polling"));
      setPendingRetryDelay(null);
      setLastError(null);
      return () => {
        stopPolling();
      };
    }

    let cancelled = false;
    pollingActiveRef.current = true;
    const baseInterval = 500;
    const maxInterval = 8000;
    const maxPolls = 1200;
    let pollCount = 0;
    let isFirstPoll = true;

    if (isNewJob) {
      setSteps(createInitialSteps());
      setLogEntries([
        {
          id: "init",
          content: "Connecting to analysis stream...",
          timestamp: new Date(),
          variant: "info",
        },
      ]);
      statusRef.current = "idle";
      setStatus("idle");
      setProgressPercentage(0);
      setFileProgressMap({});
      setTotalFiles(null);
  setFileSummaries({});
  setSelectedFileKey(null);
      jobStartTimeRef.current = null;
      setElapsedSeconds(0);
      setEtaSeconds(null);
      setPiiStats({ totalRedacted: 0, filesScanned: 0, validationWarnings: 0 });
      lastEventTimestampRef.current = null;
      seenEventIdsRef.current.clear();
      setJobErrorMessage(null);
    }

    setPollingStatus("polling");
    setLastError(null);
    setPendingRetryDelay(null);
    consecutiveFailuresRef.current = 0;
    reconnectNotifiedRef.current = false;
    setIsConnected(false);
    setLastHeartbeat(null);

    const scheduleNextPoll = (delay: number) => {
      if (cancelled || !pollingActiveRef.current) {
        return;
      }
      if (pollTimeoutRef.current) {
        clearTimeout(pollTimeoutRef.current);
      }
      if (delay > baseInterval) {
        setPendingRetryDelay(delay);
      } else {
        setPendingRetryDelay(null);
      }
      pollTimeoutRef.current = setTimeout(() => {
        pollTimeoutRef.current = null;
        void pollJobStatus();
      }, delay);
    };

    const pollJobStatus = async () => {
      if (cancelled || !pollingActiveRef.current) {
        return;
      }

      try {
        pollCount += 1;

        const jobResponse = await fetch(`${apiBaseUrl}/api/jobs/${jobId}`);
        if (!jobResponse.ok) {
          throw new Error(`Job fetch failed: ${jobResponse.status}`);
        }
        const jobData = await jobResponse.json();

        if (jobData && typeof jobData === "object" && jobData.result_data && typeof jobData.result_data === "object") {
          const filesPayload = (jobData.result_data as { files?: unknown }).files;
          if (filesPayload) {
            syncFileSummaries(filesPayload);
          }
        }

        if (!jobStartTimeRef.current) {
          const startedAt = typeof jobData.started_at === "string" ? new Date(jobData.started_at) : null;
          if (startedAt && !Number.isNaN(startedAt.getTime())) {
            jobStartTimeRef.current = startedAt;
          }
        }

        if (jobData.status === "running" && !jobStartTimeRef.current) {
          jobStartTimeRef.current = new Date();
        }

        if (cancelled || !pollingActiveRef.current) {
          return;
        }

        if (isFirstPoll) {
          isFirstPoll = false;
          setIsConnected(true);
          pushLog("Connected to job status updates.", "success", new Date());
        } else {
          setIsConnected(true);
        }

        const now = new Date();
        setLastHeartbeat(now);
        setPollingStatus("polling");
        setLastError(null);
        setPendingRetryDelay(null);
        consecutiveFailuresRef.current = 0;
        reconnectNotifiedRef.current = false;

        if (jobStartTimeRef.current) {
          const elapsed = Math.max(
            0,
            Math.floor((now.getTime() - jobStartTimeRef.current.getTime()) / 1000)
          );
          setElapsedSeconds(elapsed);
        }

        const eventsResponse = await fetch(`${apiBaseUrl}/api/jobs/${jobId}/events?limit=100`);
        if (eventsResponse.ok) {
          const events = await eventsResponse.json();

          const newEvents = events.filter((event: JobEventPayload) => {
            if (event.id && seenEventIdsRef.current.has(event.id)) {
              return false;
            }

            if (lastEventTimestampRef.current && event.created_at) {
              return new Date(event.created_at) > new Date(lastEventTimestampRef.current);
            }

            return true;
          });

          if (newEvents.length > 0) {
            newEvents.reverse().forEach((event: JobEventPayload) => {
              processJobEvent(event);

              if (event.id) {
                seenEventIdsRef.current.add(event.id);
              }

              if (event.created_at) {
                if (
                  !lastEventTimestampRef.current ||
                  new Date(event.created_at) > new Date(lastEventTimestampRef.current)
                ) {
                  lastEventTimestampRef.current = event.created_at;
                }
              }
            });
          }
        }

        if (jobData.status) {
          handleStatusUpdate(jobData.status);
        }

        if (["completed", "failed", "cancelled"].includes(jobData.status)) {
          if (jobStartTimeRef.current) {
            const completedAt =
              typeof jobData.completed_at === "string"
                ? new Date(jobData.completed_at)
                : new Date();
            const elapsed = Math.max(
              0,
              Math.floor((completedAt.getTime() - jobStartTimeRef.current.getTime()) / 1000)
            );
            setElapsedSeconds(elapsed);
            setEtaSeconds(0);
          }
          stopPolling();
          setPollingStatus(jobData.status === "completed" ? "completed" : "stopped");
          if (jobData.status !== "completed") {
            setIsConnected(false);
          }
          setEtaSeconds(0);
          pushLog(
            `Job ${jobData.status}.`,
            jobData.status === "completed" ? "success" : "warning",
            new Date()
          );
          return;
        }

        if (pollCount >= maxPolls) {
          stopPolling();
          setPollingStatus("stopped");
          setIsConnected(false);
          pushLog("Polling timeout reached.", "warning", new Date());
          return;
        }

        scheduleNextPoll(baseInterval);
      } catch (error) {
        if (cancelled) {
          return;
        }

        setIsConnected(false);
        setPollingStatus("error");
        consecutiveFailuresRef.current += 1;
        const delay = Math.min(baseInterval * 2 ** consecutiveFailuresRef.current, maxInterval);
        setPendingRetryDelay(delay);
        const message =
          error instanceof Error ? error.message : "Unable to reach job status endpoint.";
        setLastError(message);

        if (!reconnectNotifiedRef.current) {
          reconnectNotifiedRef.current = true;
          pushLog("Connection error. Retrying...", "warning", new Date());
        } else if (consecutiveFailuresRef.current % 3 === 0) {
          pushLog("Still attempting to reconnect to analysis stream...", "warning", new Date());
        }

        scheduleNextPoll(delay);
      }
    };

    void pollJobStatus();

    return () => {
      cancelled = true;
      stopPolling();
    };
  }, [
    apiBaseUrl,
    handleStatusUpdate,
    jobId,
    pollingSessionId,
    processJobEvent,
    pushLog,
    syncFileSummaries,
    sseStatus,
    stopPolling,
  ]);

  const getStatusBadge = () => {
    const badges: Record<string, { label: string; color: string }> = {
      idle: { label: "Ready", color: "text-fluent-gray-400" },
      queued: { label: "Queued", color: "text-yellow-400" },
      running: { label: "Running", color: "text-fluent-blue-400 animate-pulse" },
      paused: { label: "Paused", color: "text-amber-300" },
      completed: { label: "Completed", color: "text-green-400" },
      failed: { label: "Failed", color: "text-red-400" },
      error: { label: "Error", color: "text-red-400" },
      cancelled: { label: "Cancelled", color: "text-yellow-400" },
    };

    const badge = badges[status] || badges.idle;
    return (
      <div className={`flex items-center gap-2 text-xs font-medium ${badge.color}`}>
        <div className="h-2 w-2 rounded-full bg-current" />
        {badge.label}
      </div>
    );
  };

  

  const isTerminalStatus = ["completed", "failed", "cancelled"].includes(status);
  const canPauseJob = Boolean(jobId) && status === "running";
  const canResumeJob = Boolean(jobId) && status === "paused";
  const canCancelJob = Boolean(jobId) && !isTerminalStatus && status !== "idle";
  const canRetryJob = Boolean(jobId) && isTerminalStatus;
  const isFailureState = status === "failed" || status === "cancelled";
  const autoRetrySeconds = pendingRetryDelay ? Math.max(1, Math.ceil(pendingRetryDelay / 1000)) : null;
  const streamingHealth = useMemo<StreamingHealthState>(() => {
    if (sseStatus === "open" && pollingStatus !== "error") {
      return "healthy" as const;
    }
    if (pollingStatus === "error" || sseStatus === "error") {
      return "error" as const;
    }
    if (sseStatus === "connecting" || pollingStatus === "polling") {
      return "warning" as const;
    }
    return "healthy" as const;
  }, [pollingStatus, sseStatus]);
  const elapsedLabel = jobStartTimeRef.current
    ? formatDuration(elapsedSeconds)
    : status === "running"
    ? "Starting..."
    : "—";
  const etaLabel = useMemo(() => {
    if (etaSeconds === null) {
      if (status === "running" && progressPercentage > 0) {
        return "Estimating...";
      }
      return status === "running" ? "Gathering data..." : "—";
    }
    if (etaSeconds === 0) {
      return isTerminalStatus || progressPercentage >= 100 ? "Complete" : "Wrapping up";
    }
    return formatDuration(etaSeconds);
  }, [etaSeconds, isTerminalStatus, progressPercentage, status]);
  const filesRemainingCount = derivedTotalFiles != null
    ? Math.max(derivedTotalFiles - filesCompletedCount, 0)
    : null;
  const canExportLogs = logEntries.length > 0;
  const fileProgressStats: FileProgressStats = useMemo(() => {
    const total = fileProgressEntries.length;
    const completed = fileProgressEntries.filter((entry) => entry.status === "completed").length;
    const quarantined = fileProgressEntries.filter((entry) => entry.status === "quarantined").length;
    const processing = fileProgressEntries.filter((entry) => entry.status === "processing").length;
    return {
      total,
      completed,
      processing,
      quarantined,
    };
  }, [fileProgressEntries]);

  const handleExportLogs = useCallback(() => {
    if (logEntries.length === 0) {
      return;
    }

    const safeJobId = jobId ?? "analysis";
    const generationStamp = new Date();
    const headerLines = [
      "# RCA Analysis Log Export",
      `Generated: ${generationStamp.toISOString()}`,
      `Job ID: ${safeJobId}`,
      `Status: ${statusRef.current}`,
      `Progress: ${progressPercentage}%`,
      `Files (completed/processing/quarantined/total): ${fileProgressStats.completed}/${fileProgressStats.processing}/${fileProgressStats.quarantined}/${fileProgressStats.total}`,
      `Stream Health: SSE=${sseStatusRef.current} | Polling=${pollingStatus}`,
      `PII Protection: scanned=${piiStats.filesScanned} redacted=${piiStats.totalRedacted} warnings=${piiStats.validationWarnings}`,
      "",
    ];

    const progressSection: string[] = [];
    if (fileProgressEntries.length > 0) {
      progressSection.push("## File Progress Snapshot");
      fileProgressEntries.forEach((entry) => {
        const summaryKey = entry.fileId ?? entry.key;
        const preview = fileSummaries[summaryKey];
        const statusLabel = FILE_STATUS_LABELS[entry.status];
        const parts = [
          `- ${entry.name} [${statusLabel}]`,
          entry.chunks != null ? `  chunks=${entry.chunks}` : null,
          entry.redactionTotal != null ? `  redactions=${entry.redactionTotal}` : null,
          entry.warningCount != null ? `  warnings=${entry.warningCount}` : null,
          entry.errorCount != null ? `  errors=${entry.errorCount}` : null,
          preview ? `  sampleHead=${preview.sampleHead.slice(0, 1).join(" | ") || "n/a"}` : null,
        ].filter(Boolean);
        progressSection.push(parts.join(" | "));

        if (preview) {
          const previewDetails = [
            `   • lines=${preview.lineCount} chunks=${preview.chunkCount}`,
            `   • size=${formatBytes(preview.fileSize)} contentType=${preview.contentType ?? "n/a"}`,
            `   • errors=${preview.errorCount} warnings=${preview.warningCount} critical=${preview.criticalCount}`,
            preview.topKeywords.length > 0
              ? `   • keywords=${preview.topKeywords.slice(0, 5).join(", ")}`
              : null,
            preview.redactionValidationWarnings.length > 0
              ? `   • validationWarnings=${preview.redactionValidationWarnings.join(" | ")}`
              : null,
            preview.redactionApplied
              ? `   • redactions=${Object.entries(preview.redactionCounts)
                  .map(([key, value]) => `${key}:${value}`)
                  .join(", ") || "true"}`
              : null,
            preview.redactionFailsafeTriggered ? "   • failsafeTriggered=true" : null,
          ].filter(Boolean);
          progressSection.push(...previewDetails);
        }
      });
      progressSection.push("");
    }

    const logLines = ["## Event Log", ""];
    logEntries.forEach((entry) => {
      const timestamp = entry.timestamp instanceof Date
        ? entry.timestamp.toISOString()
        : new Date(entry.timestamp).toISOString();
      logLines.push(`[${timestamp}] [${entry.variant.toUpperCase()}] ${entry.content}`);
    });

    const exportLines = [...headerLines, ...progressSection, ...logLines];
    const blob = new Blob([exportLines.join("\n")], { type: "text/plain;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    const stamp = generationStamp.toISOString().replace(/[:.]/g, "-");
    link.href = url;
    link.download = `rca-job-${safeJobId}-${stamp}.log`;

    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  }, [fileProgressEntries, fileProgressStats, fileSummaries, logEntries, pollingStatus, piiStats, progressPercentage, jobId]);

  return (
    <Card className="flex h-full flex-col">
      <div className="border-b border-dark-border p-4">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="section-title">Live Analysis Stream</h3>
            <p className="text-xs text-dark-text-tertiary">
              Real-time updates from the RCA engine
            </p>
          </div>
          <div className="flex flex-col items-end gap-2 text-right">
            <div className="flex items-center gap-3">
              {getStatusBadge()}
              {isConnected ? (
                <div className="flex items-center gap-1 text-xs text-green-400">
                  <div className="h-2 w-2 animate-pulse rounded-full bg-green-400" />
                  Live
                </div>
              ) : (
                <div className="flex items-center gap-1 text-xs text-dark-text-tertiary">
                  <div className="h-2 w-2 rounded-full bg-dark-text-tertiary" />
                  Offline
                </div>
              )}
            </div>
            {lastHeartbeat && (
              <p className="text-[10px] text-dark-text-tertiary">
                Last update {formatTime(lastHeartbeat)}
              </p>
            )}
            {pollingStatus === "polling" && !isConnected && (
              <p className="text-[10px] text-dark-text-tertiary">
                Reconnecting to analysis stream...
              </p>
            )}
            {pollingStatus === "error" && lastError && (
              <p className="text-[10px] text-red-400">
                Connection issue: {lastError}
              </p>
            )}
            {pollingStatus === "error" && autoRetrySeconds && (
              <p className="text-[10px] text-dark-text-tertiary">
                Auto-retry in ~{autoRetrySeconds}
                {autoRetrySeconds === 1 ? " second" : " seconds"}
              </p>
            )}
            {jobId && (
              <div className="flex flex-wrap items-center justify-end gap-2">
                {canPauseJob && (
                  <button
                    type="button"
                    onClick={handlePauseJob}
                    disabled={isPausing}
                    className="rounded-md border border-amber-400/40 bg-amber-400/10 px-3 py-1 text-[11px] font-semibold text-amber-200 transition-colors hover:bg-amber-400/20 disabled:cursor-not-allowed disabled:opacity-50"
                  >
                    {isPausing ? "Pausing..." : "Pause Job"}
                  </button>
                )}
                {canResumeJob && (
                  <button
                    type="button"
                    onClick={handleResumeJob}
                    disabled={isResuming}
                    className="rounded-md border border-green-400/40 bg-green-400/10 px-3 py-1 text-[11px] font-semibold text-green-200 transition-colors hover:bg-green-400/20 disabled:cursor-not-allowed disabled:opacity-50"
                  >
                    {isResuming ? "Resuming..." : "Resume Job"}
                  </button>
                )}
                {canCancelJob && (
                  <button
                    type="button"
                    onClick={handleCancelJob}
                    disabled={isCancelling}
                    className="rounded-md border border-red-500/40 bg-red-500/10 px-3 py-1 text-[11px] font-semibold text-red-300 transition-colors hover:bg-red-500/20 disabled:cursor-not-allowed disabled:opacity-50"
                  >
                    {isCancelling ? "Cancelling..." : "Cancel Job"}
                  </button>
                )}
                {canRetryJob && !isFailureState && (
                  <button
                    type="button"
                    onClick={handleRetryJob}
                    disabled={isRetrying}
                    className="rounded-md border border-fluent-blue-500/40 bg-fluent-blue-500/10 px-3 py-1 text-[11px] font-semibold text-fluent-blue-300 transition-colors hover:bg-fluent-blue-500/20 disabled:cursor-not-allowed disabled:opacity-50"
                  >
                    {isRetrying ? "Re-queuing..." : "Retry Job"}
                  </button>
                )}
              </div>
            )}
          </div>
        </div>

        {jobId && streamingHealth !== "healthy" && (
          <div
            className={`mt-3 rounded-lg border ${STREAMING_HEALTH_STATES[streamingHealth].border} ${STREAMING_HEALTH_STATES[streamingHealth].background} p-3 text-sm shadow-inner shadow-black/10`}
          >
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div className={`flex items-center gap-2 text-xs font-semibold ${STREAMING_HEALTH_STATES[streamingHealth].tone}`}>
                <span className="text-base">
                  {STREAMING_HEALTH_STATES[streamingHealth].icon}
                </span>
                {STREAMING_HEALTH_STATES[streamingHealth].message}
              </div>
              <div className="flex flex-wrap items-center gap-2">
                {pendingRetryDelay && (
                  <span className="text-[10px] text-dark-text-tertiary">
                    Retrying in ~{Math.max(1, Math.ceil(pendingRetryDelay / 1000))}s
                  </span>
                )}
                {!isTerminalStatus && (
                  <button
                    type="button"
                    onClick={handleManualRetry}
                    className="rounded-md border border-fluent-blue-500/40 bg-fluent-blue-500/10 px-3 py-1 text-[11px] font-semibold text-fluent-blue-200 transition-colors hover:bg-fluent-blue-500/20"
                  >
                    Retry Now
                  </button>
                )}
              </div>
            </div>
          </div>
        )}

        {jobId && isFailureState && jobErrorMessage && (
          <div className="mt-3 rounded-lg border border-red-500/40 bg-red-500/10 p-3 text-sm text-red-200 shadow-inner shadow-red-900/20">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div className="flex-1 min-w-0">
                <p className="text-sm font-semibold text-red-300">Analysis ended with issues</p>
                <p className="mt-1 text-xs leading-relaxed text-red-200/90">
                  {jobErrorMessage}
                </p>
              </div>
              {canRetryJob && (
                <button
                  type="button"
                  onClick={handleRetryJob}
                  disabled={isRetrying}
                  className="shrink-0 rounded-md border border-fluent-blue-500/40 bg-fluent-blue-500/10 px-3 py-1 text-[11px] font-semibold text-fluent-blue-200 transition-colors hover:bg-fluent-blue-500/20 disabled:cursor-not-allowed disabled:opacity-50"
                >
                  {isRetrying ? "Re-queuing..." : "Retry Analysis"}
                </button>
              )}
            </div>
          </div>
        )}
        
        {jobId && (
          <div className="mt-3 grid gap-2 text-xs sm:grid-cols-3">
            <div className="rounded-lg border border-dark-border/60 bg-dark-bg-tertiary/60 p-3">
              <p className="font-semibold uppercase tracking-wide text-[10px] text-dark-text-tertiary">
                Elapsed Time
              </p>
              <p className="mt-1 text-sm font-semibold text-dark-text-primary">
                {elapsedLabel}
              </p>
            </div>
            <div className="rounded-lg border border-dark-border/60 bg-dark-bg-tertiary/60 p-3">
              <p className="font-semibold uppercase tracking-wide text-[10px] text-dark-text-tertiary">
                Estimated Completion
              </p>
              <p className="mt-1 text-sm font-semibold text-dark-text-primary">
                {etaLabel}
              </p>
            </div>
            <div className="rounded-lg border border-dark-border/60 bg-dark-bg-tertiary/60 p-3">
              <p className="font-semibold uppercase tracking-wide text-[10px] text-dark-text-tertiary">
                File Throughput
              </p>
              <p className="mt-1 text-sm font-semibold text-dark-text-primary">
                {filesCompletedCount}
                {derivedTotalFiles != null ? ` / ${derivedTotalFiles}` : ""}
                {derivedTotalFiles == null ? " files" : " complete"}
              </p>
              <p className="mt-1 text-[10px] text-dark-text-tertiary">
                {filesInProgressCount > 0
                  ? `${filesInProgressCount} in progress`
                  : filesRemainingCount != null && filesRemainingCount > 0
                  ? `${filesRemainingCount} remaining`
                  : "Standing by"}
              </p>
            </div>
          </div>
        )}

        {/* Progress Bar */}
        {jobId && progressPercentage > 0 && (
          <div className="mt-4 animate-fade-in">
            <div className="mb-2 flex items-center justify-between text-xs">
              <span className="text-dark-text-secondary font-medium">Overall Progress</span>
              <span className="font-bold text-fluent-blue-400 text-sm">{progressPercentage}%</span>
            </div>
            <div className="h-2.5 w-full overflow-hidden rounded-full bg-dark-bg-tertiary ring-1 ring-dark-border/50">
              <div
                ref={progressBarRef}
                className="h-full rounded-full bg-gradient-to-r from-fluent-blue-500 via-fluent-blue-400 to-fluent-info transition-all duration-700 ease-out shadow-lg shadow-fluent-blue-500/20"
              />
            </div>
            {progressPercentage < 100 && (
              <p className="mt-2 text-[10px] text-dark-text-tertiary italic">
                {progressPercentage < 30 && "Starting analysis..."}
                {progressPercentage >= 30 && progressPercentage < 60 && "Processing files..."}
                {progressPercentage >= 60 && progressPercentage < 90 && "Running AI analysis..."}
                {progressPercentage >= 90 && progressPercentage < 100 && "Finalizing report..."}
              </p>
            )}
          </div>
        )}

        {jobId && fileProgressEntries.length > 0 && (
          <div className="mt-4 animate-fade-in rounded-lg border border-dark-border bg-dark-bg-secondary/80 p-4">
            <div className="flex items-center justify-between gap-2">
              <h4 className="text-sm font-semibold text-dark-text-primary flex items-center gap-2">
                <span className="text-lg">📁</span>
                File Progress
              </h4>
              <div className="flex flex-wrap items-center gap-3 text-[11px] text-dark-text-tertiary">
                <span className="rounded-full border border-dark-border/50 bg-dark-bg-tertiary/70 px-2 py-0.5 font-medium">
                  {fileProgressStats.completed} completed
                </span>
                {fileProgressStats.processing > 0 && (
                  <span className="rounded-full border border-fluent-blue-500/40 bg-fluent-blue-500/10 px-2 py-0.5 font-medium text-fluent-blue-200">
                    {fileProgressStats.processing} processing
                  </span>
                )}
                {fileProgressStats.quarantined > 0 && (
                  <span className="rounded-full border border-red-500/40 bg-red-500/10 px-2 py-0.5 font-medium text-red-300">
                    {fileProgressStats.quarantined} quarantined
                  </span>
                )}
                {filesRemainingCount != null && filesRemainingCount > 0 && (
                  <span className="rounded-full border border-dark-border/50 bg-dark-bg-tertiary/70 px-2 py-0.5 font-medium">
                    {filesRemainingCount} remaining
                  </span>
                )}
              </div>
            </div>
            {selectedFileEntry && (
              <div className="mt-3 rounded-md border border-dark-border/60 bg-dark-bg-tertiary/60 p-3">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div className="flex items-center gap-2 text-xs font-semibold text-dark-text-secondary">
                    <span className="text-base">🔎</span>
                    {selectedFileEntry.name}
                  </div>
                  <div className="flex flex-wrap items-center gap-2 text-[10px] text-dark-text-tertiary">
                    <span className="rounded-full border border-dark-border/40 bg-dark-bg-tertiary/70 px-2 py-0.5 font-medium">
                      {FILE_STATUS_LABELS[selectedFileEntry.status]}
                    </span>
                    {selectedPreview ? (
                      <>
                        <span className="rounded-full border border-dark-border/40 bg-dark-bg-tertiary/70 px-2 py-0.5 font-medium">
                          {selectedPreview.lineCount} lines
                        </span>
                        <span className="rounded-full border border-dark-border/40 bg-dark-bg-tertiary/70 px-2 py-0.5 font-medium">
                          {selectedPreview.chunkCount} chunk{selectedPreview.chunkCount === 1 ? "" : "s"}
                        </span>
                      </>
                    ) : (
                      <span className="rounded-full border border-dark-border/40 bg-dark-bg-tertiary/70 px-2 py-0.5 font-medium">
                        Preview pending
                      </span>
                    )}
                  </div>
                </div>
                {selectedPreview ? (
                  <div className="mt-3 space-y-3 text-xs text-dark-text-secondary">
                    <div className="grid gap-3 md:grid-cols-2">
                      <div className="rounded-md border border-dark-border/50 bg-dark-bg-secondary/70 p-3">
                        <p className="text-[10px] font-semibold uppercase tracking-wide text-dark-text-tertiary">
                          Sample (start)
                        </p>
                        <pre className="mt-2 max-h-40 overflow-auto rounded bg-dark-bg-tertiary/80 p-2 text-[11px] leading-relaxed text-dark-text-secondary">
                          {selectedPreview.sampleHead.length > 0
                            ? selectedPreview.sampleHead.join("\n")
                            : "No excerpt captured."}
                        </pre>
                      </div>
                      <div className="rounded-md border border-dark-border/50 bg-dark-bg-secondary/70 p-3">
                        <p className="text-[10px] font-semibold uppercase tracking-wide text-dark-text-tertiary">
                          Sample (end)
                        </p>
                        <pre className="mt-2 max-h-40 overflow-auto rounded bg-dark-bg-tertiary/80 p-2 text-[11px] leading-relaxed text-dark-text-secondary">
                          {selectedPreview.sampleTail.length > 0
                            ? selectedPreview.sampleTail.join("\n")
                            : "No excerpt captured."}
                        </pre>
                      </div>
                    </div>
                    <div className="flex flex-wrap items-center gap-2 text-[10px] text-dark-text-tertiary">
                      <span className="rounded-full border border-dark-border/40 bg-dark-bg-tertiary/70 px-2 py-0.5">
                        Size {formatBytes(selectedPreview.fileSize)}
                      </span>
                      {selectedPreview.contentType && (
                        <span className="rounded-full border border-dark-border/40 bg-dark-bg-tertiary/70 px-2 py-0.5">
                          {selectedPreview.contentType}
                        </span>
                      )}
                      <span className="rounded-full border border-dark-border/40 bg-dark-bg-tertiary/70 px-2 py-0.5">
                        Errors {selectedPreview.errorCount}
                      </span>
                      <span className="rounded-full border border-dark-border/40 bg-dark-bg-tertiary/70 px-2 py-0.5">
                        Warnings {selectedPreview.warningCount}
                      </span>
                      {selectedPreview.redactionApplied && (
                        <span className="rounded-full border border-fluent-blue-500/30 bg-fluent-blue-500/10 px-2 py-0.5 text-fluent-blue-200">
                          Redactions {selectedPreviewRedactions}
                        </span>
                      )}
                      {selectedPreview.redactionFailsafeTriggered && (
                        <span className="rounded-full border border-red-500/40 bg-red-500/10 px-2 py-0.5 text-red-300">
                          Quarantined
                        </span>
                      )}
                    </div>
                    {selectedPreview.topKeywords.length > 0 && (
                      <div>
                        <p className="text-[10px] font-semibold uppercase tracking-wide text-dark-text-tertiary">
                          Highlighted Keywords
                        </p>
                        <div className="mt-1 flex flex-wrap gap-1">
                          {selectedPreview.topKeywords.slice(0, 6).map((keyword) => (
                            <span
                              key={keyword}
                              className="rounded-md border border-dark-border/40 bg-dark-bg-tertiary/80 px-2 py-0.5 text-[11px] text-dark-text-secondary"
                            >
                              {keyword}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}
                    {selectedPreview.redactionValidationWarnings.length > 0 && (
                      <div className="rounded-md border border-yellow-500/40 bg-yellow-500/10 p-2 text-[11px] text-yellow-300">
                        {selectedPreview.redactionValidationWarnings[0]}
                        {selectedPreview.redactionValidationWarnings.length > 1
                          ? ` (+${selectedPreview.redactionValidationWarnings.length - 1} more)`
                          : ""}
                      </div>
                    )}
                  </div>
                ) : (
                  <p className="mt-3 text-xs text-dark-text-tertiary">
                    {selectedFileEntry.status === "completed" || selectedFileEntry.status === "quarantined"
                      ? "Final preview is populating. Check back shortly."
                      : "Preview unlocks once this file finishes processing."}
                  </p>
                )}
              </div>
            )}
            <div className="mt-3 max-h-48 space-y-2 overflow-y-auto pr-1">
              {fileProgressEntries.map((entry) => {
                const isSelected = entry.key === selectedFileKey;
                const entryClasses = isSelected
                  ? "border-fluent-blue-500/60 bg-fluent-blue-500/10 shadow-lg shadow-fluent-blue-500/10"
                  : "border-dark-border/60 bg-dark-bg-tertiary/60 hover:border-fluent-blue-500/40";

                return (
                  <div
                    key={entry.key}
                    role="button"
                    tabIndex={0}
                    onClick={() => setSelectedFileKey(entry.key)}
                    onKeyDown={(event: KeyboardEvent<HTMLDivElement>) => {
                      if (event.key === "Enter" || event.key === " ") {
                        event.preventDefault();
                        setSelectedFileKey(entry.key);
                      }
                    }}
                    className={`flex items-start justify-between gap-3 rounded-md border p-3 transition-colors duration-150 focus:outline-none focus:ring-2 focus:ring-fluent-blue-500/40 focus:ring-offset-0 cursor-pointer ${entryClasses}`}
                  >
                    <div className="flex-1 pr-2">
                      <p className="text-sm font-semibold text-dark-text-primary">{entry.name}</p>
                      <p className="text-[11px] text-dark-text-tertiary">
                        {entry.chunks != null
                          ? `${entry.chunks} chunk${entry.chunks === 1 ? "" : "s"}`
                          : "Awaiting summary"}
                        {entry.redactionTotal && entry.redactionTotal > 0
                          ? ` • ${entry.redactionTotal} redaction${entry.redactionTotal === 1 ? "" : "s"}`
                          : ""}
                        {entry.warningCount && entry.warningCount > 0
                          ? ` • ${entry.warningCount} warning${entry.warningCount === 1 ? "" : "s"}`
                          : ""}
                      </p>
                      {entry.validationWarnings && entry.validationWarnings.length > 0 && (
                        <p className="mt-1 text-[11px] text-yellow-300">
                          {entry.validationWarnings[0]}
                          {entry.validationWarnings.length > 1
                            ? ` (+${entry.validationWarnings.length - 1} more)`
                            : ""}
                        </p>
                      )}
                      {(entry.completedAt || entry.startedAt) && (
                        <p className="mt-1 text-[10px] text-dark-text-tertiary">
                          {entry.completedAt
                            ? `Completed ${formatTime(entry.completedAt)}`
                            : entry.startedAt
                            ? `Started ${formatTime(entry.startedAt)}`
                            : ""}
                        </p>
                      )}
                    </div>
                    <div className="flex flex-col items-end gap-1 text-right">
                      <span
                        className={`rounded-full px-2 py-0.5 text-[10px] font-semibold ${FILE_STATUS_CLASSES[entry.status]}`}
                      >
                        {FILE_STATUS_LABELS[entry.status]}
                      </span>
                      {entry.securityState && (
                        <span
                          className={`rounded-full px-2 py-0.5 text-[10px] font-semibold ${FILE_SECURITY_CLASSES[entry.securityState]}`}
                        >
                          {FILE_SECURITY_LABELS[entry.securityState]}
                        </span>
                      )}
                    </div>
                  </div>
                );
              })}
          </div>
          </div>
        )}
        
        {/* PII Protection Status - Highly Visible */}
        {jobId && piiStats.filesScanned > 0 && (
          <div className="mt-4 animate-fade-in rounded-lg border-2 border-green-500/40 bg-gradient-to-r from-green-500/10 via-green-600/5 to-green-500/10 p-4 shadow-lg shadow-green-500/10">
            <div className="flex items-center gap-3 mb-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-full border-2 border-green-500 bg-green-500/20 shadow-lg shadow-green-500/30">
                <svg className="h-6 w-6 text-green-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
                </svg>
              </div>
              <div className="flex-1">
                <h4 className="text-sm font-bold text-green-400 flex items-center gap-2">
                  🔒 PII Protection Active
                  <span className="inline-flex h-2 w-2 rounded-full bg-green-500 animate-pulse" />
                </h4>
                <p className="text-xs text-green-400/80 mt-0.5">Multi-pass scanning with strict validation</p>
              </div>
            </div>
            <div className="grid grid-cols-3 gap-3 text-center">
              <div className="rounded-md border border-green-500/30 bg-green-500/5 p-2">
                <div className="text-2xl font-bold text-green-400">{piiStats.filesScanned}</div>
                <div className="text-xs text-green-400/70 mt-1">Files Scanned</div>
              </div>
              <div className="rounded-md border border-green-500/30 bg-green-500/5 p-2">
                <div className="text-2xl font-bold text-green-400">{piiStats.totalRedacted}</div>
                <div className="text-xs text-green-400/70 mt-1">Items Redacted</div>
              </div>
              <div className={`rounded-md border p-2 ${piiStats.validationWarnings > 0 ? 'border-yellow-500/30 bg-yellow-500/5' : 'border-green-500/30 bg-green-500/5'}`}>
                <div className={`text-2xl font-bold ${piiStats.validationWarnings > 0 ? 'text-yellow-400' : 'text-green-400'}`}>
                  {piiStats.validationWarnings}
                </div>
                <div className={`text-xs mt-1 ${piiStats.validationWarnings > 0 ? 'text-yellow-400/70' : 'text-green-400/70'}`}>
                  Warnings
                </div>
              </div>
            </div>
            {piiStats.validationWarnings > 0 && (
              <div className="mt-3 flex items-start gap-2 rounded-md border border-yellow-500/30 bg-yellow-500/10 p-2 text-xs">
                <span className="text-yellow-400">⚠️</span>
                <p className="text-yellow-400/90">
                  Validation detected potential sensitive patterns. Review recommended.
                </p>
              </div>
            )}
          </div>
        )}
      </div>

      <div className="flex-1 overflow-hidden p-4">
        <div className="flex h-full flex-col gap-4">
          <section className="rounded-lg border border-dark-border bg-dark-bg-secondary p-4">
            <div className="flex items-center justify-between">
              <h4 className="text-sm font-semibold text-dark-text-primary">
                Analysis Progress
              </h4>
            </div>
            <ul className="mt-3 space-y-3">
              {steps.map((step) => (
                <li key={step.id} className="flex items-start gap-3">
                  <StepStatusIcon status={step.status} />
                  <div className="flex-1">
                    <p className="text-sm font-medium text-dark-text-primary">
                      {step.label}
                    </p>
                    <p className="text-xs text-dark-text-tertiary">
                      {step.lastMessage ?? step.description}
                    </p>
                    {step.lastUpdated && (
                      <p className="mt-1 text-[10px] text-dark-text-tertiary">
                        {formatTime(step.lastUpdated)}
                      </p>
                    )}
                  </div>
                </li>
              ))}
            </ul>
          </section>

          <section className="flex-1 overflow-hidden rounded-lg border border-dark-border bg-dark-bg-secondary">
            <div className="border-b border-dark-border bg-gradient-to-r from-dark-bg-tertiary to-dark-bg-secondary px-4 py-3 flex flex-wrap items-center justify-between gap-2">
              <h4 className="text-sm font-bold text-dark-text-primary flex items-center gap-2">
                <span className="text-lg">📋</span>
                Activity Log
                {logEntries.length > 0 && (
                  <span className="inline-flex h-2 w-2 rounded-full bg-green-500 animate-pulse ml-1" title="Live" />
                )}
              </h4>
              <div className="flex items-center gap-2">
                <span className="text-xs font-semibold text-fluent-blue-400 bg-fluent-blue-500/10 px-2.5 py-1 rounded-full border border-fluent-blue-500/20">
                  {logEntries.length} event{logEntries.length !== 1 ? 's' : ''}
                </span>
                <button
                  type="button"
                  onClick={handleExportLogs}
                  disabled={!canExportLogs}
                  className="rounded-md border border-dark-border/60 bg-dark-bg-tertiary/70 px-2.5 py-1 text-[11px] font-semibold text-dark-text-secondary transition-colors hover:bg-dark-bg-tertiary disabled:cursor-not-allowed disabled:opacity-40"
                >
                  Export Log
                </button>
              </div>
            </div>
            <div className="flex-1 overflow-y-auto px-4 py-3">
              {logEntries.length === 0 ? (
                <div className="flex flex-col items-center justify-center py-12 text-center animate-fade-in">
                  <div className="mb-3 h-16 w-16 rounded-full bg-gradient-to-br from-fluent-blue-500/20 to-fluent-info/20 flex items-center justify-center shadow-lg">
                    <span className="text-4xl">📭</span>
                  </div>
                  <p className="text-sm text-dark-text-secondary font-semibold">
                    Waiting for activity...
                  </p>
                  <p className="text-xs text-dark-text-tertiary mt-2 max-w-xs leading-relaxed">
                    Real-time events will stream here during analysis. You&apos;ll see file processing, AI insights, and progress updates.
                  </p>
                </div>
              ) : (
                <div className="space-y-2">
                  {logEntries.map((entry) => (
                    <div
                      key={entry.id}
                      className="flex items-start gap-3 text-xs p-2 rounded-md hover:bg-dark-bg-tertiary/50 transition-all duration-200 animate-fade-in"
                    >
                      <div
                        className={`mt-1 h-2 w-2 rounded-full shrink-0 ${
                          LOG_VARIANT_STYLES[entry.variant]
                        } ${entry.variant === 'info' ? 'animate-pulse' : ''}`}
                      />
                      <div className="flex-1 min-w-0">
                        <p className={`text-sm leading-relaxed ${LOG_TEXT_STYLES[entry.variant]}`}>
                          {entry.content}
                        </p>
                        <p className="mt-1 text-[10px] text-dark-text-tertiary">
                          {formatTime(entry.timestamp)}
                        </p>
                      </div>
                    </div>
                  ))}
                  <div ref={messagesEndRef} />
                </div>
              )}
            </div>
          </section>
        </div>
      </div>
    </Card>
  );
}
