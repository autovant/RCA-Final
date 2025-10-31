"use client";

import { useMemo } from "react";
import Link from "next/link";
import { Header } from "@/components/layout/Header";
import { HeroBanner } from "@/components/dashboard/HeroBanner";
import { StatCard } from "@/components/dashboard/StatsCards";
import { Alert, Badge, Button, Card } from "@/components/ui";
import { formatTimestamp, useJobsPreview } from "@/data/jobsPreview";
import { FileText } from "lucide-react";

const statusMap: Record<string, { label: string; variant: "success" | "info" | "warning" | "error" | "neutral" }> = {
  completed: { label: "Completed", variant: "success" },
  running: { label: "Running", variant: "info" },
  queued: { label: "Queued", variant: "neutral" },
  pending: { label: "Pending", variant: "warning" },
  failed: { label: "Failed", variant: "error" },
};

export default function JobsPage() {
  const { jobs, loading, error, refresh, stats } = useJobsPreview();

  const { sortedJobs, breakdown } = useMemo(() => {
    const ordered = [...jobs].sort((a, b) => {
      const left = new Date(a.updated_at ?? a.created_at ?? 0).getTime();
      const right = new Date(b.updated_at ?? b.created_at ?? 0).getTime();
      return right - left;
    });

    return {
      sortedJobs: ordered,
      breakdown: {
        running: stats.runningJobs,
        failed: stats.failedJobs,
        queued: stats.queuedJobs,
      },
    };
  }, [jobs, stats.failedJobs, stats.queuedJobs, stats.runningJobs]);

  const recentHighlights = sortedJobs.slice(0, 3);

  return (
    <div className="min-h-screen bg-dark-bg-primary">
      <Header />

      <main className="container mx-auto px-4 sm:px-6 lg:px-8 py-10">
        <HeroBanner
          isAuthenticated={false}
          onPrimaryAction={() => undefined}
          onSecondaryAction={() => undefined}
          onLogin={() => undefined}
          onSignup={() => undefined}
          stats={stats}
          heading="Jobs keep pace with every incident rhythm."
          subtitle="Track automation momentum, surface the right evidence, and keep executives aligned even when live telemetry is unavailable."
          talkingPoints={[
            "Glassboard view of every automation run",
            "Retrieval-augmented insights attached to each job",
            "Review-ready context captured for customer narratives",
          ]}
          showActions={false}
          eyebrow="OPERATIONS OVERVIEW"
        />

        <section className="mt-10 grid gap-6 lg:grid-cols-[2fr,1fr]">
          <div className="space-y-6">
            <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
              <StatCard
                title="Total Jobs"
                value={stats.totalJobs}
                color="blue"
                icon={
                  <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
                  </svg>
                }
              />
              <StatCard
                title="Running"
                value={breakdown.running}
                color="cyan"
                icon={
                  <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                  </svg>
                }
              />
              <StatCard
                title="Queued"
                value={breakdown.queued}
                color="yellow"
                icon={
                  <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M4.93 4.93l14.14 14.14" />
                  </svg>
                }
              />
              <StatCard
                title="Failed"
                value={breakdown.failed}
                color="red"
                icon={
                  <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                }
              />
            </div>

            {error && (
              <Alert variant="warning" className="animate-fade-in">
                <div>
                  <p className="font-semibold">{error}</p>
                  <p className="text-sm text-dark-text-secondary mt-1">Refresh once your services reconnect to resume live updates.</p>
                </div>
              </Alert>
            )}

            <Card className="p-6">
              <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
                <div>
                  <h2 className="section-title">Job Ledger</h2>
                  <p className="text-sm text-dark-text-secondary">Search-ready record that aligns customer updates, SRE workflows, and executive comms.</p>
                </div>
                <div className="flex items-center gap-2">
                  <Button variant="secondary" onClick={() => void refresh()} loading={loading}>
                    Refresh data
                  </Button>
                  <Badge variant="info">Preview</Badge>
                </div>
              </div>

              <div className="table-container mt-6">
                <table className="table" aria-label="Automation jobs">
                  <thead>
                    <tr>
                      <th scope="col">Job ID</th>
                      <th scope="col">Type</th>
                      <th scope="col">Status</th>
                      <th scope="col">Owner</th>
                      <th scope="col">Created</th>
                      <th scope="col">Updated</th>
                      <th scope="col">Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {sortedJobs.map((job) => {
                      const key = job.status.toLowerCase();
                      const meta = statusMap[key] ?? { label: job.status, variant: "neutral" as const };

                      return (
                        <tr key={job.id}>
                          <td className="font-medium text-dark-text-primary">{job.id}</td>
                          <td className="text-dark-text-secondary">{job.job_type}</td>
                          <td>
                            <Badge variant={meta.variant}>{meta.label}</Badge>
                          </td>
                          <td className="text-dark-text-secondary">{job.user_id}</td>
                          <td className="text-dark-text-secondary">{formatTimestamp(job.created_at) ?? "—"}</td>
                          <td className="text-dark-text-secondary">{formatTimestamp(job.updated_at) ?? "—"}</td>
                          <td>
                            {job.status.toLowerCase() === 'completed' && (
                              <Link
                                href={`/jobs/${job.id}`}
                                className="inline-flex items-center gap-2 px-3 py-1.5 bg-fluent-blue-500 hover:bg-fluent-blue-400 text-white rounded-lg transition-colors text-sm font-medium"
                              >
                                <FileText className="w-4 h-4" />
                                View Report
                              </Link>
                            )}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </Card>
          </div>

          <aside className="space-y-6">
            <Card className="p-6">
              <h2 className="section-title">Guided handoffs</h2>
              <p className="text-sm text-dark-text-secondary">Each job ships with AI-authored talking points so ops, support, and leadership stay aligned.</p>
              <div className="divider" />
              <ul className="space-y-4">
                {recentHighlights.map((job) => (
                  <li key={job.id} className="rounded-xl border border-dark-border/70 bg-dark-bg-tertiary/60 p-4">
                    <div className="flex items-center justify-between">
                      <p className="text-sm font-semibold text-dark-text-primary">{job.job_type}</p>
                      <Badge variant={statusMap[job.status.toLowerCase()]?.variant ?? "neutral"}>{statusMap[job.status.toLowerCase()]?.label ?? job.status}</Badge>
                    </div>
                    <p className="mt-2 text-xs text-dark-text-secondary">Last touch {formatTimestamp(job.updated_at ?? job.created_at) ?? "—"}</p>
                    <p className="mt-3 text-sm text-dark-text-secondary">Copilot packs the timeline, RCA summary, and recommended outbound messaging into the associated ticket bundle.</p>
                  </li>
                ))}
              </ul>
            </Card>

            <Card className="p-6">
              <h2 className="section-title">Operational guardrails</h2>
              <ul className="mt-4 space-y-3 text-sm text-dark-text-secondary">
                <li className="flex items-start gap-3">
                  <span className="status-dot mt-1" aria-hidden="true" />
                  Dual review enforced before any customer-visible ticket is dispatched.
                </li>
                <li className="flex items-start gap-3">
                  <span className="status-dot mt-1" aria-hidden="true" />
                  RAG prompts automatically document the knowledge base sources consulted for each run.
                </li>
                <li className="flex items-start gap-3">
                  <span className="status-dot mt-1" aria-hidden="true" />
                  Failure cases generate an action item in the reliability backlog with context-rich repro steps.
                </li>
              </ul>
            </Card>
          </aside>
        </section>
      </main>
    </div>
  );
}
