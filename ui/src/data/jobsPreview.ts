"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import axios from "axios";

export const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8001";

export type JobResponse = {
  id: string;
  job_type: string;
  status: "completed" | "running" | "failed" | "queued" | "pending" | string;
  user_id: string;
  created_at?: string;
  updated_at?: string;
};

export const SAMPLE_JOBS: JobResponse[] = [
  {
    id: "demo-job",
    job_type: "rca_automation",
    status: "completed",
    user_id: "automation-lab",
    created_at: "2025-10-12T21:02:00Z",
    updated_at: "2025-10-12T21:15:00Z",
  },
  {
    id: "ops-2729",
    job_type: "incident_timeline",
    status: "running",
    user_id: "global-oncall",
    created_at: "2025-10-12T20:22:00Z",
    updated_at: "2025-10-12T20:29:00Z",
  },
  {
    id: "ops-2726",
    job_type: "customer_digest",
    status: "queued",
    user_id: "customer-success",
    created_at: "2025-10-12T19:48:00Z",
    updated_at: "2025-10-12T19:48:00Z",
  },
  {
    id: "ops-2721",
    job_type: "knowledge_refresh",
    status: "failed",
    user_id: "reliability-lab",
    created_at: "2025-10-12T18:20:00Z",
    updated_at: "2025-10-12T18:25:00Z",
  },
];

export type JobStats = {
  totalJobs: number;
  completedJobs: number;
  runningJobs: number;
  failedJobs: number;
  queuedJobs: number;
  successRate: number;
  lastJobAt: string | null;
};

export const formatTimestamp = (value?: string) => {
  if (!value) {
    return null;
  }

  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return null;
  }

  return parsed.toLocaleString([], {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
};

export const deriveJobStats = (jobs: JobResponse[]): JobStats => {
  if (jobs.length === 0) {
    return {
      totalJobs: 0,
      completedJobs: 0,
      runningJobs: 0,
      failedJobs: 0,
      queuedJobs: 0,
      successRate: 0,
      lastJobAt: null,
    };
  }

  const completedJobs = jobs.filter((job) => job.status.toLowerCase() === "completed").length;
  const runningJobs = jobs.filter((job) => job.status.toLowerCase() === "running").length;
  const failedJobs = jobs.filter((job) => job.status.toLowerCase() === "failed").length;
  const queuedJobs = jobs.filter((job) => {
    const status = job.status.toLowerCase();
    return status === "queued" || status === "pending";
  }).length;
  const successRate = Math.round((completedJobs / jobs.length) * 100);
  const latest = jobs
    .map((job) => job.updated_at ?? job.created_at ?? null)
    .filter((value): value is string => Boolean(value))
    .sort((a, b) => new Date(b).getTime() - new Date(a).getTime())[0];

  return {
    totalJobs: jobs.length,
    completedJobs,
    runningJobs,
    failedJobs,
    queuedJobs,
    successRate: Number.isFinite(successRate) ? successRate : 0,
    lastJobAt: formatTimestamp(latest),
  };
};

export const pickLatestJobId = (jobs: JobResponse[]): string | null => {
  if (jobs.length === 0) {
    return null;
  }

  const [latest] = [...jobs].sort((a, b) => {
    const aDate = new Date(a.updated_at ?? a.created_at ?? 0).getTime();
    const bDate = new Date(b.updated_at ?? b.created_at ?? 0).getTime();
    return bDate - aDate;
  });

  return latest?.id ?? null;
};

export function useJobsPreview(initialJobs: JobResponse[] = SAMPLE_JOBS) {
  const [jobs, setJobs] = useState<JobResponse[]>(initialJobs);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      const response = await axios.get<JobResponse[]>(`${API_BASE}/api/jobs`);
      const payload = Array.isArray(response.data) && response.data.length > 0 ? response.data : initialJobs;
      setJobs(payload);
      setError(null);
    } catch (requestError) {
      setJobs(initialJobs);
      setError("Live job telemetry is offline. Displaying curated preview data.");
    } finally {
      setLoading(false);
    }
  }, [initialJobs]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const stats = useMemo(() => deriveJobStats(jobs), [jobs]);

  return {
    jobs,
    loading,
    error,
    refresh,
    stats,
  } as const;
}
