"use client";

import { useMemo } from "react";
import { useRouter } from "next/navigation";
import { Header } from "@/components/layout/Header";
import { HeroBanner } from "@/components/dashboard/HeroBanner";
import { StatCard } from "@/components/dashboard/StatsCards";
import { CommandCenter } from "@/components/dashboard/CommandCenter";
import { ReliabilityPanel } from "@/components/dashboard/ReliabilityPanel";
import { ExperienceShowcase } from "@/components/dashboard/ExperienceShowcase";
import { Button, Card } from "@/components/ui";
import { useTicketStore } from "@/store/ticketStore";
import { useJobsPreview } from "@/data/jobsPreview";

const EXPERIENCE_ACTIVITY = [
  {
    id: "highlight-1",
    title: "Executive briefing packaged",
    description:
      "Copilot drafted a stakeholder-ready update with timeline, customer impact, and next steps.",
    time: "Moments ago",
    status: "success" as const,
  },
  {
    id: "highlight-2",
    title: "Guardrail checkpoint",
    description:
      "Automation paused for human review before syncing redacted attachments to ServiceNow.",
    time: "7 mins ago",
    status: "warning" as const,
  },
  {
    id: "highlight-3",
    title: "RAG refresh completed",
    description:
      "Knowledge routing re-ranked log sources to prioritize the latest data plane anomalies.",
    time: "18 mins ago",
    status: "info" as const,
  },
];
export default function HomePage() {
  const router = useRouter();
  const { jobs, loading: jobsLoading, error: jobError, refresh, stats } = useJobsPreview();
  const isAuthenticated = true;
  const toggleState = useTicketStore((state) => state.toggleState);

  const heroStats = useMemo(
    () => ({
      totalJobs: stats.totalJobs,
      completedJobs: stats.completedJobs,
      successRate: stats.successRate,
      lastJobAt: stats.lastJobAt,
    }),
    [stats]
  );

  const handleNavigateToTickets = () => {
    router.push("/tickets");
  };

  const handleNavigateToJobs = () => {
    router.push("/jobs");
  };

  const handleStartInvestigation = () => {
    router.push("/investigation");
  };

  return (
    <div className="relative min-h-screen bg-dark-bg-primary">
      <Header showAuthActions={false} />

  <main className="container mx-auto flex flex-col gap-12 px-4 pt-24 pb-12 sm:px-6 lg:px-8 lg:gap-16 lg:pt-28">
        <section className="grid items-stretch gap-6 lg:grid-cols-[minmax(0,2fr)_minmax(0,1fr)] xl:gap-8">
          <HeroBanner
            className="h-full"
            isAuthenticated={isAuthenticated}
            onPrimaryAction={handleStartInvestigation}
            onSecondaryAction={handleNavigateToJobs}
            onLogin={handleStartInvestigation}
            onSignup={handleStartInvestigation}
            stats={heroStats}
            heading="Automation-led RCA, ready for every incident cadence."
            subtitle="Retrieval, copilots, and governed handoffs keep stakeholder updates, workflows, and executive readouts synchronized."
            talkingPoints={[
              "AI-guided triage accelerates investigations end-to-end",
              "Glassmorphic work surfaces keep focus on critical decisions",
              "Human checkpoints ensure automation stays in lockstep",
            ]}
            eyebrow="Executive Operations Control"
          />

          <ReliabilityPanel
            isAuthenticated={isAuthenticated}
            ticketSettings={toggleState}
            className="lg:max-w-sm lg:justify-self-end xl:max-w-md"
          />
        </section>

        <section className="space-y-5">
          <div className="flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
            <div>
              <h2 className="section-title">Incident Pulse</h2>
              <p className="text-sm text-dark-text-tertiary">
                Metrics refresh with every automation run to surface the real-time control-room picture.
              </p>
            </div>
            <span className="text-xs font-semibold uppercase tracking-[0.22em] text-dark-text-tertiary">
              Live Telemetry
            </span>
          </div>

          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
            <StatCard
              title="Total Runs"
              value={stats.totalJobs}
              color="blue"
              icon={
                <svg className="h-6 w-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2"
                  />
                </svg>
              }
            />
            <StatCard
              title="In Flight"
              value={stats.runningJobs}
              color="cyan"
              icon={
                <svg className="h-6 w-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                </svg>
              }
            />
            <StatCard
              title="Completed"
              value={stats.completedJobs}
              color="green"
              icon={
                <svg className="h-6 w-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                </svg>
              }
            />
            <StatCard
              title="Attention"
              value={stats.failedJobs}
              color="red"
              icon={
                <svg className="h-6 w-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              }
            />
          </div>
        </section>

        <CommandCenter
          jobs={jobs}
          jobsLoading={jobsLoading}
          jobError={jobError}
          isAuthenticated={isAuthenticated}
          onRefresh={refresh}
          onCreateJob={handleStartInvestigation}
          onSelectJob={(jobId) => router.push(`/tickets?jobId=${encodeURIComponent(jobId)}`)}
        />

        <section className="grid gap-6 lg:grid-cols-[minmax(0,3fr)_minmax(0,2fr)] xl:gap-8">
          <ExperienceShowcase activity={EXPERIENCE_ACTIVITY} />

          <div className="space-y-6">
            <Card className="relative flex h-full flex-col justify-between overflow-hidden p-6">
              <div className="absolute inset-0 bg-gradient-to-br from-fluent-info/20 via-transparent to-dark-bg-secondary/80" aria-hidden="true" />
              <div className="relative space-y-3">
                <h2 className="text-xl font-semibold text-dark-text-primary">Operations Toolkit</h2>
                <p className="text-sm text-dark-text-secondary">
                  Launch templated communications, sync job-linked documentation, and manage governance settings without leaving the console.
                </p>
                <ul className="space-y-2 text-xs text-dark-text-tertiary">
                  <li className="flex items-center gap-2">
                    <span className="hero-bullet" aria-hidden="true" />
                    Drafts orchestrated communications instantly
                  </li>
                  <li className="flex items-center gap-2">
                    <span className="hero-bullet" aria-hidden="true" />
                    Aligns ITSM updates with executive-ready narratives
                  </li>
                </ul>
              </div>
              <div className="relative mt-6 flex flex-col gap-2 sm:flex-row sm:items-center">
                <Button size="lg" onClick={handleNavigateToTickets}>
                  Open Control Center
                </Button>
                <Button size="lg" variant="ghost" onClick={handleNavigateToJobs}>
                  Review Job History
                </Button>
              </div>
            </Card>

            <Card className="relative overflow-hidden border border-fluent-blue-500/25 bg-gradient-to-br from-fluent-blue-500/10 via-transparent to-dark-bg-secondary p-6">
              <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_right,rgba(56,189,248,0.18),transparent_55%)]" aria-hidden="true" />
              <div className="relative space-y-3">
                <div className="flex items-center gap-3">
                  <div className="rounded-lg bg-fluent-blue-500/20 p-2 text-fluent-blue-300">
                    <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14.752 11.168l-5.197-3.028A1 1 0 008 9.028v5.944a1 1 0 001.555.832l5.197-2.916a1 1 0 000-1.72z" />
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                  </div>
                  <h3 className="text-lg font-semibold text-dark-text-primary">Launch the Guided Demo</h3>
                </div>
                <p className="text-sm text-dark-text-secondary">
                  Showcase redaction, semantic search, classification, and platform intelligence with a scripted tour that runs without live data.
                </p>
                <Button
                  variant="secondary"
                  className="w-full sm:w-auto"
                  onClick={() => router.push("/demo")}
                  icon={
                    <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14.752 11.168l-5.197-3.028A1 1 0 008 9.028v5.944a1 1 0 001.555.832l5.197-2.916a1 1 0 000-1.72z" />
                    </svg>
                  }
                >
                  Open Demo Tour
                </Button>
              </div>
            </Card>

            <Card className="relative overflow-hidden p-6 border-fluent-blue-500/30 bg-gradient-to-br from-fluent-blue-500/10 via-transparent to-dark-bg-secondary">
              <div className="absolute inset-0 bg-gradient-to-br from-fluent-blue-500/5 via-transparent to-transparent" aria-hidden="true" />
              <div className="relative space-y-3">
                <div className="flex items-center gap-3">
                  <div className="p-2 rounded-lg bg-fluent-blue-500/20 text-fluent-blue-400">
                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 3v4M3 5h4M6 17v4m-2-2h4m5-16l2.286 6.857L21 12l-5.714 2.143L13 21l-2.286-6.857L5 12l5.714-2.143L13 3z" />
                    </svg>
                  </div>
                  <h3 className="text-lg font-semibold text-dark-text-primary">Explore Platform Features</h3>
                </div>
                <p className="text-sm text-dark-text-secondary">
                  Discover the full capabilities of the RCA Engine—from intelligent automation to enterprise-grade security.
                </p>
                <Button 
                  variant="primary" 
                  className="w-full sm:w-auto"
                  onClick={() => router.push("/features")}
                  icon={
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7l5 5m0 0l-5 5m5-5H6" />
                    </svg>
                  }
                >
                  View All Features
                </Button>
              </div>
            </Card>
          </div>
        </section>
      </main>
    </div>
  );
}
