"use client";

import { useState, useEffect, useRef, useCallback } from "react";
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

export function StreamingChat({ jobId, onStatusChange }: StreamingChatProps) {
  const [steps, setSteps] = useState<StepState[]>(createInitialSteps);
  const [logEntries, setLogEntries] = useState<LogEntry[]>([]);
  const [status, setStatus] = useState<string>("idle");
  const [isConnected, setIsConnected] = useState(false);
  const [lastHeartbeat, setLastHeartbeat] = useState<Date | null>(null);
  const [progressPercentage, setProgressPercentage] = useState<number>(0);
  
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

  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [logEntries, scrollToBottom]);

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
      setStatus((prev) => (prev === nextStatus ? prev : nextStatus));
      onStatusChange?.(nextStatus);
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
          updateStep("classification", "in-progress", { timestamp });
          pushLog("Analysis started.", "info", timestamp);
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
          pushLog(`Processing ${prefix}${filename}...`, "info", timestamp);
          updateStep("redaction", "in-progress", { details: data, timestamp });
          
          // Track file scanned for PII
          setPiiStats(prev => ({ ...prev, filesScanned: prev.filesScanned + 1 }));
          break;
        }
        case "file-processing-completed": {
          const filename = typeof data.filename === "string" ? data.filename : "uploaded file";
          const chunks = typeof data.chunks === "number" ? data.chunks : undefined;
          const redactionHits = typeof data.redaction_hits === "number" ? data.redaction_hits : 0;
          const validationWarnings = Array.isArray(data.validation_warnings) ? data.validation_warnings.length : 0;
          
          // Update PII stats
          if (redactionHits > 0 || validationWarnings > 0) {
            setPiiStats(prev => ({
              ...prev,
              totalRedacted: prev.totalRedacted + redactionHits,
              validationWarnings: prev.validationWarnings + validationWarnings
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
          updateStep("report", "completed", {
            message: "Analysis completed successfully.",
            timestamp,
            details: data,
          });
          pushLog("Analysis completed successfully.", "success", timestamp);
          break;
        }
        case "failed":
        case "error": {
          handleStatusUpdate("failed");
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
          break;
        }
        case "cancelled": {
          handleStatusUpdate("cancelled");
          const reason =
            typeof data.reason === "string" ? data.reason : "Analysis cancelled.";
          updateStep("report", "failed", {
            message: reason,
            timestamp,
            details: data,
          });
          pushLog(reason, "warning", timestamp);
          break;
        }
        default:
          break;
      }
    },
    [handleStatusUpdate, pushLog, updateStep]
  );

  useEffect(() => {
    if (!jobId) {
      setSteps(createInitialSteps());
      setLogEntries([]);
      setStatus("idle");
      setIsConnected(false);
      setLastHeartbeat(null);
      setProgressPercentage(0);
      pollingActiveRef.current = false;
      return;
    }

    // Prevent multiple polling instances
    if (pollingActiveRef.current) {
      console.warn("Polling already active, skipping new instance");
      return;
    }

    pollingActiveRef.current = true;
    setSteps(createInitialSteps());
    setLogEntries([
      {
        id: "init",
        content: "Connecting to analysis stream...",
        timestamp: new Date(),
        variant: "info",
      },
    ]);
    setStatus("idle");
    setIsConnected(false);
    setLastHeartbeat(null);
    setProgressPercentage(0);
    reconnectNotifiedRef.current = false;
    lastEventTimestampRef.current = null;
    seenEventIdsRef.current.clear();

      const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL || "";
      let pollCount = 0;
      const maxPolls = 1200; // 10 minutes max (500ms intervals = 120 polls/min)
      let isPolling = true;
      let isFirstPoll = true;

      const pollJobStatus = async () => {
        if (!isPolling) return;

        try {
          pollCount++;

          // Fetch current job status
          const jobResponse = await fetch(`${apiBaseUrl}/api/jobs/${jobId}`);
          if (!jobResponse.ok) {
            throw new Error(`Job fetch failed: ${jobResponse.status}`);
          }
          const jobData = await jobResponse.json();

          // Update connection status on first successful poll
          if (isFirstPoll && pollCount === 1) {
            isFirstPoll = false;
            setIsConnected(true);
            pushLog("Connected to job status updates.", "success", new Date());
          }

          // Update heartbeat
          setLastHeartbeat(new Date());

          // Fetch new events since last check
          const eventsResponse = await fetch(`${apiBaseUrl}/api/jobs/${jobId}/events?limit=100`);
          if (eventsResponse.ok) {
            const events = await eventsResponse.json();
            
            // Filter by both timestamp AND event ID to prevent duplicates
            const newEvents = events.filter((e: JobEventPayload) => {
              // Skip if we've already seen this event ID
              if (e.id && seenEventIdsRef.current.has(e.id)) {
                return false;
              }
              
              // Skip if event is older than last seen timestamp
              if (lastEventTimestampRef.current && e.created_at) {
                return new Date(e.created_at) > new Date(lastEventTimestampRef.current);
              }
              
              return true;
            });

            // Process new events in chronological order (oldest first)
            if (newEvents.length > 0) {
              console.log(`📥 Processing ${newEvents.length} new events (poll #${pollCount})`);
              newEvents.reverse().forEach((event: JobEventPayload) => {
                processJobEvent(event);
                
                // Track this event as seen
                if (event.id) {
                  seenEventIdsRef.current.add(event.id);
                }
                
                // Update last seen timestamp
                if (event.created_at) {
                  if (!lastEventTimestampRef.current || 
                      new Date(event.created_at) > new Date(lastEventTimestampRef.current)) {
                    lastEventTimestampRef.current = event.created_at;
                  }
                }
              });
            }
          }

          // Update status (always call onStatusChange, let parent decide if it changed)
          if (jobData.status) {
            onStatusChange?.(jobData.status);
          }

          // Stop polling if job is in terminal state
          if (jobData.status === 'completed' || jobData.status === 'failed' || jobData.status === 'cancelled') {
            isPolling = false;
            pushLog(`Job ${jobData.status}.`, jobData.status === 'completed' ? 'success' : 'warning', new Date());
          }

          // Stop polling if max polls reached
          if (pollCount >= maxPolls) {
            isPolling = false;
            pushLog("Polling timeout reached.", "warning", new Date());
          }
        } catch (error) {
          console.error("Poll error:", error);
          setIsConnected(false);
          if (!reconnectNotifiedRef.current) {
            reconnectNotifiedRef.current = true;
            pushLog("Connection error. Retrying...", "warning", new Date());
          }
        }
      };
    
    // Start polling immediately to catch early events
    pollJobStatus();

    // Poll frequently to catch rapid status changes during analysis
    // 500ms = 2x per second, ensures we don't miss intermediate steps
    const pollInterval = setInterval(pollJobStatus, 500);

    return () => {
      isPolling = false;
      pollingActiveRef.current = false;
      clearInterval(pollInterval);
      console.log("Polling stopped and cleaned up");
    };
  }, [jobId, processJobEvent, pushLog, onStatusChange]); // Re-run only when jobId or callbacks change

  const getStatusBadge = () => {
    const badges: Record<string, { label: string; color: string }> = {
      idle: { label: "Ready", color: "text-fluent-gray-400" },
      queued: { label: "Queued", color: "text-yellow-400" },
      running: { label: "Running", color: "text-fluent-blue-400 animate-pulse" },
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

  const logVariantStyles: Record<MessageVariant, string> = {
    info: "bg-dark-text-tertiary",
    success: "bg-green-400",
    warning: "bg-yellow-400",
    error: "bg-red-400",
  };

  const logTextStyles: Record<MessageVariant, string> = {
    info: "text-dark-text-secondary",
    success: "text-green-400",
    warning: "text-yellow-300",
    error: "text-red-400",
  };

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
          </div>
        </div>
        
        {/* Progress Bar */}
        {jobId && progressPercentage > 0 && (
          <div className="mt-4 animate-fade-in">
            <div className="mb-2 flex items-center justify-between text-xs">
              <span className="text-dark-text-secondary font-medium">Overall Progress</span>
              <span className="font-bold text-fluent-blue-400 text-sm">{progressPercentage}%</span>
            </div>
            <div className="h-2.5 w-full overflow-hidden rounded-full bg-dark-bg-tertiary ring-1 ring-dark-border/50">
              <div
                className="h-full rounded-full bg-gradient-to-r from-fluent-blue-500 via-fluent-blue-400 to-fluent-info transition-all duration-700 ease-out shadow-lg shadow-fluent-blue-500/20"
                style={{ width: `${progressPercentage}%` }}
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
            <div className="border-b border-dark-border bg-gradient-to-r from-dark-bg-tertiary to-dark-bg-secondary px-4 py-3 flex items-center justify-between">
              <h4 className="text-sm font-bold text-dark-text-primary flex items-center gap-2">
                <span className="text-lg">📋</span>
                Activity Log
                {logEntries.length > 0 && (
                  <span className="inline-flex h-2 w-2 rounded-full bg-green-500 animate-pulse ml-1" title="Live" />
                )}
              </h4>
              <span className="text-xs font-semibold text-fluent-blue-400 bg-fluent-blue-500/10 px-2.5 py-1 rounded-full border border-fluent-blue-500/20">
                {logEntries.length} event{logEntries.length !== 1 ? 's' : ''}
              </span>
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
                  {logEntries.map((entry, index) => (
                    <div 
                      key={entry.id} 
                      className="flex items-start gap-3 text-xs p-2 rounded-md hover:bg-dark-bg-tertiary/50 transition-all duration-200 animate-fade-in"
                      style={{ animationDelay: `${Math.min(index * 50, 500)}ms` }}
                    >
                      <div
                        className={`mt-1 h-2 w-2 rounded-full shrink-0 ${
                          logVariantStyles[entry.variant]
                        } ${entry.variant === 'info' ? 'animate-pulse' : ''}`}
                      />
                      <div className="flex-1 min-w-0">
                        <p className={`text-sm leading-relaxed ${logTextStyles[entry.variant]}`}>
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
