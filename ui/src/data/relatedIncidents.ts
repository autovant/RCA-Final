"use client";

import axios from "axios";
import type { RelatedIncident } from "@/components/related/RelatedIncidentList";

export const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8001";

export type RelatedIncidentResponse = {
  results: RelatedIncident[];
  audit_token?: string | null;
};

export type RelatedIncidentQueryParams = {
  minRelevance?: number;
  limit?: number;
  platform?: string;
};

export type RelatedIncidentSearchScope = "authorized_workspaces" | "current_workspace";

export type RelatedIncidentSearchPayload = {
  query: string;
  scope?: RelatedIncidentSearchScope;
  minRelevance?: number;
  limit?: number;
  platform?: string;
  workspaceId?: string;
};

export const SAMPLE_RELATED_INCIDENTS: RelatedIncident[] = [
  {
    session_id: "sess-4521",
    tenant_id: "blue-harvest",
    relevance: 0.82,
    summary: "Automation flaked after orchestrator patch rollout",
    detected_platform: "UiPath",
    occurred_at: "2025-09-18T18:22:00Z",
    fingerprint_status: "ready",
    safeguards: ["CROSS_WORKSPACE", "AUDIT_TRAIL"],
  },
  {
    session_id: "sess-4319",
    tenant_id: "tailwind-labs",
    relevance: 0.74,
    summary: "AI summariser misrouted approvals during spike",
    detected_platform: "Automation Anywhere",
    occurred_at: "2025-08-02T05:14:00Z",
    fingerprint_status: "degraded",
    safeguards: ["HUMAN_REVIEW"],
  },
  {
    session_id: "sess-3982",
    tenant_id: "northwind",
    relevance: 0.69,
    summary: "Tenant-wide timeout cascade during batch import",
    detected_platform: "Blue Prism",
    occurred_at: "2025-05-27T23:41:00Z",
    fingerprint_status: "available",
    safeguards: [],
  },
];

export async function fetchRelatedForSession(
  sessionId: string,
  params: RelatedIncidentQueryParams = {},
): Promise<RelatedIncidentResponse> {
  try {
    const response = await axios.get<RelatedIncidentResponse>(
      `${API_BASE}/api/v1/incidents/${encodeURIComponent(sessionId)}/related`,
      {
        params: {
          min_relevance: params.minRelevance,
          limit: params.limit,
          platform: params.platform,
        },
      },
    );
    return response.data;
  } catch (error) {
    const message = error instanceof Error ? error.message : "Failed to load related incidents";
    throw new Error(message);
  }
}

export async function searchRelatedIncidents(
  payload: RelatedIncidentSearchPayload,
): Promise<RelatedIncidentResponse> {
  try {
    const response = await axios.post<RelatedIncidentResponse>(
      `${API_BASE}/api/v1/incidents/search`,
      {
        query: payload.query,
        scope: payload.scope ?? "authorized_workspaces",
        min_relevance: payload.minRelevance,
        limit: payload.limit,
        platform: payload.platform,
        workspace_id: payload.workspaceId,
      },
    );
    return response.data;
  } catch (error) {
    const message = error instanceof Error ? error.message : "Failed to search related incidents";
    throw new Error(message);
  }
}
