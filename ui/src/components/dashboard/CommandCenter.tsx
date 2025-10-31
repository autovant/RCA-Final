"use client";

import { useMemo } from "react";
import { Button, Alert, Spinner, Badge, Card } from "@/components/ui";
import { JobResponse } from "@/data/jobsPreview";

type CommandCenterProps = {
  jobs: JobResponse[];
  jobsLoading: boolean;
  jobError: string | null;
  isAuthenticated: boolean;
  onRefresh: () => void;
  onCreateJob: () => void;
  onSelectJob: (jobId: string) => void;
};

const statusBadgeVariant = (status: string): "success" | "warning" | "error" | "info" | "neutral" => {
  const normalized = status.toLowerCase();
  if (normalized === "completed") return "success";
  if (normalized === "running") return "info";
  if (normalized === "failed") return "error";
  if (normalized === "pending" || normalized === "queued") return "warning";
  return "neutral";
};

const statusCopy = (status: string) => {
  const normalized = status.toLowerCase();
  if (normalized === "completed") return "Completed";
  if (normalized === "running") return "In Progress";
  if (normalized === "failed") return "Needs Attention";
  if (normalized === "pending") return "Pending";
  if (normalized === "queued") return "Queued";
  return status;
};

export function CommandCenter({
  jobs,
  jobsLoading,
  jobError,
  isAuthenticated,
  onRefresh,
  onCreateJob,
  onSelectJob,
}: CommandCenterProps) {
  const recentJobs = useMemo(() => {
    const sorted = [...jobs].sort((a, b) => {
      const aDate = new Date(a.updated_at || a.created_at || 0).getTime();
      const bDate = new Date(b.updated_at || b.created_at || 0).getTime();
      return bDate - aDate;
    });
    return sorted.slice(0, 12);
  }, [jobs]);

  return (
    <section aria-labelledby="command-center-heading" className="space-y-5">
      <div className="grid gap-4 lg:grid-cols-12">
        <Card className="relative col-span-12 overflow-hidden rounded-3xl border border-dark-border/45 bg-dark-bg-secondary/80 p-7 shadow-[0_18px_42px_rgba(15,23,42,0.38)] backdrop-blur-2xl lg:col-span-6 xl:col-span-5">
          <div className="absolute inset-0 bg-gradient-to-br from-fluent-blue-500/22 via-transparent to-dark-bg-secondary/85" aria-hidden="true" />
          <div className="relative flex flex-col gap-6">
            <div className="flex items-start justify-between gap-4">
              <div>
                <span className="badge-pill">Launchpad</span>
                <h2 id="command-center-heading" className="mt-3 text-xl font-semibold text-dark-text-primary">
                  Operations Launchpad
                </h2>
                <p className="mt-2 text-sm text-dark-text-tertiary">
                  Initiate guided workflows, approvals, and telemetry refreshes from a single pane.
                </p>
              </div>
              <div className="hidden sm:flex -space-x-2">
                {[1, 2, 3].map((item) => (
                  <div
                    key={`operator-${item}`}
                    className="h-9 w-9 rounded-full border border-dark-border/45 bg-dark-bg-tertiary/70"
                  />
                ))}
              </div>
            </div>

            <div className="grid gap-3 sm:grid-cols-2">
              <Button
                onClick={onCreateJob}
                disabled={!isAuthenticated}
                size="lg"
                icon={
                  <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                  </svg>
                }
              >
                Start Guided Investigation
              </Button>
              <Button
                onClick={onRefresh}
                disabled={!isAuthenticated || jobsLoading}
                loading={jobsLoading}
                variant="secondary"
                size="lg"
                icon={
                  <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                  </svg>
                }
              >
                Refresh Activity
              </Button>
            </div>

            <ul className="grid gap-2 text-xs text-dark-text-tertiary sm:grid-cols-2">
              <li className="flex items-center gap-2 rounded-xl border border-dark-border/40 bg-dark-bg-tertiary/60 px-3 py-2">
                <span className="status-dot" />
                Orchestrates cross-system updates
              </li>
              <li className="flex items-center gap-2 rounded-xl border border-dark-border/40 bg-dark-bg-tertiary/60 px-3 py-2">
                <span className="status-dot" />
                Captures approvals before automation
              </li>
            </ul>

            {!isAuthenticated && (
              <p className="text-xs text-dark-text-tertiary">
                Sign in to unlock workflow setup and streaming telemetry.
              </p>
            )}
          </div>
        </Card>

        <Card className="col-span-12 rounded-3xl border border-dark-border/45 bg-dark-bg-secondary/75 p-7 shadow-[0_18px_42px_rgba(15,23,42,0.34)] backdrop-blur-2xl lg:col-span-6 xl:col-span-7">
          <div className="flex items-start justify-between">
            <div>
              <h3 className="section-title">Operations Timeline</h3>
              <p className="mt-1 text-xs text-dark-text-tertiary">
                Track the latest automations, validation checkpoints, and downstream updates.
              </p>
            </div>
            <Button
              onClick={onRefresh}
              disabled={!isAuthenticated || jobsLoading}
              loading={jobsLoading}
              size="sm"
              variant="ghost"
            >
              Sync
            </Button>
          </div>

          {jobError && (
            <Alert variant="error" className="mb-3">
              {jobError}
            </Alert>
          )}

          {jobsLoading ? (
            <div className="flex items-center justify-center py-12">
              <Spinner size="lg" />
            </div>
          ) : recentJobs.length === 0 ? (
            <div className="empty-state">
              <svg className="h-14 w-14 text-dark-text-tertiary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6 6 0 00-9.33-4.934" />
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 21h6" />
              </svg>
              <p className="mt-3 font-medium text-dark-text-secondary">No workflows yet</p>
              <p className="text-sm text-dark-text-tertiary">
                Initiate an automation to populate the activity stream.
              </p>
            </div>
          ) : (
            <div className="command-scroll">
              <ul className="space-y-3">
                {recentJobs.map((job) => {
                  const created = job.created_at ? new Date(job.created_at).toLocaleString() : "—";
                  const statusVariant = statusBadgeVariant(job.status);
                  const label = statusCopy(job.status);
                  const jobType = job.job_type.replace(/_/g, " ");

                  return (
                    <li key={job.id}>
                      <button
                        type="button"
                        onClick={() => onSelectJob(job.id)}
                        className="command-item"
                      >
                        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                          <div>
                            <p className="font-semibold capitalize text-dark-text-primary">
                              {jobType}
                            </p>
                            <p className="text-xs text-dark-text-tertiary">{created}</p>
                          </div>
                          <Badge variant={statusVariant} className="tracking-[0.24em]">
                            {label}
                          </Badge>
                        </div>
                        <div className="mt-3 flex items-center justify-between text-xs text-dark-text-tertiary">
                          <span className="font-mono uppercase">#{job.id.slice(0, 8)}</span>
                          <span className="inline-flex items-center gap-1 font-semibold text-dark-text-secondary">
                            Inspect
                            <svg className="h-3.5 w-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                            </svg>
                          </span>
                        </div>
                      </button>
                    </li>
                  );
                })}
              </ul>
            </div>
          )}
        </Card>
      </div>
    </section>
  );
}
