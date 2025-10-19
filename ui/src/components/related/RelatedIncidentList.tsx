"use client";

import { useMemo } from "react";
import { Badge, Card, Spinner } from "@/components/ui";

export type RelatedIncident = {
  session_id: string;
  tenant_id: string;
  relevance: number;
  summary: string;
  detected_platform: string;
  occurred_at?: string | null;
  fingerprint_status: string;
  safeguards: string[];
};

const platformVariant = (platform: string | undefined): "info" | "success" | "warning" | "error" | "neutral" => {
  if (!platform) {
    return "neutral";
  }

  const normalized = platform.toLowerCase();
  if (normalized.includes("uipath")) {
    return "info";
  }
  if (normalized.includes("blue") || normalized.includes("prism")) {
    return "success";
  }
  if (normalized.includes("automation anywhere")) {
    return "warning";
  }
  if (normalized.includes("pega")) {
    return "info";
  }
  if (normalized.includes("appian")) {
    return "success";
  }
  return "neutral";
};

const fingerprintVariant = (status: string | undefined): "success" | "info" | "warning" | "error" | "neutral" => {
  if (!status) {
    return "neutral";
  }
  const normalized = status.toLowerCase();
  if (normalized.includes("ready") || normalized.includes("available")) {
    return "success";
  }
  if (normalized.includes("degraded")) {
    return "warning";
  }
  if (normalized.includes("unavailable") || normalized.includes("missing")) {
    return "error";
  }
  return "info";
};

const formatDateTime = (value?: string | null) => {
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

interface RelatedIncidentListProps {
  results: RelatedIncident[];
  loading?: boolean;
  auditToken?: string | null;
}

export function RelatedIncidentList({ results, loading = false, auditToken }: RelatedIncidentListProps) {
  const sortedResults = useMemo(() => {
    return [...results].sort((a, b) => b.relevance - a.relevance);
  }, [results]);

  if (loading) {
    return (
      <div className="flex h-48 items-center justify-center">
        <Spinner size="lg" />
      </div>
    );
  }

  if (sortedResults.length === 0) {
    return (
      <Card className="p-8 text-center">
        <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-full border border-dashed border-dark-border/60 text-dark-text-tertiary">
          <svg className="h-8 w-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 14l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
        </div>
        <h3 className="mt-4 text-lg font-semibold text-dark-text-primary">No related incidents yet</h3>
        <p className="mt-2 text-sm text-dark-text-secondary">Adjust your filters or broaden the search scope to surface additional precedents.</p>
      </Card>
    );
  }

  return (
    <div className="space-y-4">
      {sortedResults.map((item, index) => {
        const occurredAt = formatDateTime(item.occurred_at);
        const displayRelevance = Math.round(item.relevance * 100);
        const platform = item.detected_platform || "Unknown";
        const fingerprintStatus = item.fingerprint_status || "unknown";

        return (
          <div 
            key={`${item.session_id}-${item.tenant_id}`} 
            className="animate-fade-in"
            style={{ animationDelay: `${index * 50}ms` }}
          >
            <Card className="relative overflow-hidden p-6">
            <div className="absolute inset-0 bg-gradient-to-br from-fluent-blue-500/10 via-transparent to-dark-bg-secondary/60" aria-hidden="true" />
            <div className="relative space-y-4">
              <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                <div>
                  <p className="text-xs font-semibold uppercase tracking-[0.25em] text-dark-text-tertiary">Session {item.session_id}</p>
                  <h3 className="mt-1 text-lg font-semibold text-dark-text-primary">{item.summary || "Similarity match"}</h3>
                  <p className="mt-2 text-sm text-dark-text-secondary">Tenant: <span className="font-mono text-xs">{item.tenant_id}</span></p>
                </div>
                <div className="flex flex-col items-start gap-2 sm:items-end">
                  <Badge variant="info">Relevance {displayRelevance}%</Badge>
                  {occurredAt && <p className="text-xs text-dark-text-tertiary">Occurred {occurredAt}</p>}
                </div>
              </div>

              <div className="flex flex-wrap items-center gap-2 text-xs font-medium text-dark-text-secondary">
                <Badge variant={platformVariant(platform)}>Platform {platform}</Badge>
                <Badge variant={fingerprintVariant(fingerprintStatus)}>Fingerprint {fingerprintStatus}</Badge>
                {item.safeguards.map((label) => (
                  <span key={label} className="rounded-full border border-dark-border/60 bg-dark-bg-tertiary/60 px-3 py-1 text-[0.7rem] uppercase tracking-[0.15em] text-dark-text-tertiary">
                    {label}
                  </span>
                ))}
              </div>
            </div>
            </Card>
          </div>
        );
      })}

      {auditToken && (
        <p className="text-right text-xs text-dark-text-tertiary">
          Audit token <span className="font-mono">{auditToken}</span>
        </p>
      )}
    </div>
  );
}
