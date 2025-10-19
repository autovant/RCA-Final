"use client";

import { FormEvent, useMemo, useState } from "react";
import { Header } from "@/components/layout/Header";
import { Alert, Button, Card, Input } from "@/components/ui";
import { RelatedIncidentList, RelatedIncident } from "@/components/related/RelatedIncidentList";
import {
  SAMPLE_RELATED_INCIDENTS,
  fetchRelatedForSession,
  searchRelatedIncidents,
  RelatedIncidentSearchPayload,
  RelatedIncidentSearchScope,
} from "@/data/relatedIncidents";

const PLATFORM_OPTIONS = ["", "UiPath", "Blue Prism", "Automation Anywhere", "Appian", "Pega"];

type Mode = "session" | "search";

export default function RelatedIncidentsPage() {
  const [mode, setMode] = useState<Mode>("session");
  const [sessionId, setSessionId] = useState("");
  const [query, setQuery] = useState("");
  const [platform, setPlatform] = useState("");
  const [scope, setScope] = useState<RelatedIncidentSearchScope>("authorized_workspaces");
  const [workspaceId, setWorkspaceId] = useState("");
  const [minRelevance, setMinRelevance] = useState(0.6);
  const [limit, setLimit] = useState(10);

  const [results, setResults] = useState<RelatedIncident[]>(SAMPLE_RELATED_INCIDENTS);
  const [auditToken, setAuditToken] = useState<string | null>(null);
  const [lastContext, setLastContext] = useState<string | null>("Preview dataset");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const effectiveScope = useMemo<RelatedIncidentSearchScope>(() => {
    if (workspaceId.trim().length > 0) {
      return "current_workspace";
    }
    return scope;
  }, [scope, workspaceId]);

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError(null);

    if (mode === "session" && sessionId.trim().length === 0) {
      setError("Enter a session identifier to look up related incidents.");
      return;
    }

    if (mode === "search" && query.trim().length === 0) {
      setError("Provide a short description or excerpt to run a similarity search.");
      return;
    }

    setLoading(true);
    const fallback = SAMPLE_RELATED_INCIDENTS;
    const safeLimit = Math.min(50, Math.max(1, Math.round(limit)));

    try {
      if (mode === "session") {
        const response = await fetchRelatedForSession(sessionId.trim(), {
          minRelevance,
          limit: safeLimit,
          platform: platform || undefined,
        });
        setResults(response.results ?? fallback);
        setAuditToken(response.audit_token ?? null);
        setLastContext(`Session ${sessionId.trim()}`);
        if (!response.results || response.results.length === 0) {
          setError("Live lookup returned no matches. Showing curated examples while you adjust filters.");
          setResults(fallback);
          setAuditToken(null);
          setLastContext((previous) => (previous ? `${previous} • preview` : "Preview dataset"));
        }
      } else {
        const payload: RelatedIncidentSearchPayload = {
          query: query.trim(),
          scope: effectiveScope,
          minRelevance,
          limit: safeLimit,
          platform: platform || undefined,
          workspaceId: workspaceId.trim() || undefined,
        };
        const response = await searchRelatedIncidents(payload);
        setResults(response.results ?? fallback);
        setAuditToken(response.audit_token ?? null);
        setLastContext(`Query \"${query.trim()}\"`);
        if (!response.results || response.results.length === 0) {
          setError("Live search returned no matches. Showing curated examples while you adjust filters.");
          setResults(fallback);
          setAuditToken(null);
          setLastContext((previous) => (previous ? `${previous} • preview` : "Preview dataset"));
        }
      }
    } catch (requestError) {
      const message = requestError instanceof Error ? requestError.message : "Unable to load related incidents.";
      setError(`${message} Displaying curated preview data while connectivity is restored.`);
      setResults(fallback);
      setAuditToken(null);
      setLastContext("Preview dataset");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-dark-bg-primary">
      <Header />
      <main className="container mx-auto flex flex-col gap-8 px-4 py-10 sm:px-6 lg:px-8">
        <section className="space-y-2">
          <span className="badge-pill">Similarity Insights</span>
          <h1 className="text-3xl font-semibold text-dark-text-primary">Discover related incidents in moments</h1>
          <p className="max-w-3xl text-sm text-dark-text-secondary">
            Compare a completed RCA session or free-form description against the knowledge base to surface precedents, guardrail notes, and platform fingerprints without leaving the console.
          </p>
        </section>

        <section className="grid gap-6 lg:grid-cols-[minmax(0,1.1fr)_minmax(0,1.9fr)]">
          <Card className="p-6">
            <form className="space-y-6" onSubmit={handleSubmit}>
              <div className="flex items-center gap-2 rounded-xl border border-dark-border/60 bg-dark-bg-tertiary/60 p-1">
                <button
                  type="button"
                  onClick={() => setMode("session")}
                  className={`flex-1 rounded-lg px-4 py-2 text-sm font-semibold transition ${
                    mode === "session" ? "bg-dark-bg-secondary text-dark-text-primary" : "text-dark-text-secondary hover:text-dark-text-primary"
                  }`}
                >
                  Lookup by session
                </button>
                <button
                  type="button"
                  onClick={() => setMode("search")}
                  className={`flex-1 rounded-lg px-4 py-2 text-sm font-semibold transition ${
                    mode === "search" ? "bg-dark-bg-secondary text-dark-text-primary" : "text-dark-text-secondary hover:text-dark-text-primary"
                  }`}
                >
                  Search by description
                </button>
              </div>

              {mode === "session" ? (
                <Input
                  label="Session identifier"
                  placeholder="rca-session-id"
                  value={sessionId}
                  onChange={(event) => setSessionId(event.target.value)}
                />
              ) : (
                <Input
                  label="Describe the incident context"
                  placeholder="Customer login failures after workflow deploy"
                  value={query}
                  onChange={(event) => setQuery(event.target.value)}
                />
              )}

              <div className="grid gap-4 sm:grid-cols-2">
                <div>
                  <label htmlFor="related-min-relevance" className="block text-sm font-medium text-dark-text-secondary mb-2">Minimum relevance: {Math.round(minRelevance * 100)}%</label>
                  <input
                    id="related-min-relevance"
                    type="range"
                    min={0}
                    max={1}
                    step={0.05}
                    value={minRelevance}
                    onChange={(event) => setMinRelevance(Number(event.target.value))}
                    className="w-full"
                  />
                </div>
                <Input
                  label="Limit"
                  type="number"
                  min={1}
                  max={50}
                  value={limit}
                  onChange={(event) => {
                    const next = Number(event.target.value);
                    if (Number.isNaN(next)) {
                      setLimit(1);
                      return;
                    }
                    setLimit(Math.min(50, Math.max(1, next)));
                  }}
                />
              </div>

              <div className="grid gap-4 sm:grid-cols-2">
                <div>
                  <label htmlFor="related-platform" className="block text-sm font-medium text-dark-text-secondary mb-2">Platform filter</label>
                  <select
                    id="related-platform"
                    value={platform}
                    onChange={(event) => setPlatform(event.target.value)}
                    className="input"
                  >
                    {PLATFORM_OPTIONS.map((option) => (
                      <option key={option || "any"} value={option}>
                        {option === "" ? "Any platform" : option}
                      </option>
                    ))}
                  </select>
                </div>
                {mode === "search" && (
                  <div>
                    <label htmlFor="related-scope" className="block text-sm font-medium text-dark-text-secondary mb-2">Workspace scope</label>
                    <div className="flex gap-2">
                      <select
                        id="related-scope"
                        value={scope}
                        onChange={(event) => setScope(event.target.value as RelatedIncidentSearchScope)}
                        className="input"
                        disabled={workspaceId.trim().length > 0}
                      >
                        <option value="authorized_workspaces">Authorized workspaces</option>
                        <option value="current_workspace">Current workspace</option>
                      </select>
                    </div>
                  </div>
                )}
              </div>

              {mode === "search" && (
                <Input
                  label="Workspace ID (optional)"
                  placeholder="workspace-123"
                  value={workspaceId}
                  onChange={(event) => setWorkspaceId(event.target.value)}
                />
              )}

              <Button type="submit" loading={loading} disabled={loading} className="w-full">
                Run similarity lookup
              </Button>

              {error && <Alert variant="warning">{error}</Alert>}
            </form>
          </Card>

          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="section-title">Suggested precedents</h2>
                <p className="text-sm text-dark-text-secondary">
                  Matches ranked by similarity score. Guardrails indicate cross-workspace visibility and review requirements.
                </p>
              </div>
              {lastContext && (
                <span className="text-xs font-semibold uppercase tracking-[0.2em] text-dark-text-tertiary">{lastContext}</span>
              )}
            </div>
            <RelatedIncidentList results={results} auditToken={auditToken} loading={loading} />
          </div>
        </section>
      </main>
    </div>
  );
}
