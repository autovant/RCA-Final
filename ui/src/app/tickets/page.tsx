"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { Header } from "@/components/layout/Header";
import { CommandCenter } from "@/components/dashboard/CommandCenter";
import { ExperienceShowcase } from "@/components/dashboard/ExperienceShowcase";
import { TicketDashboard } from "@/components/tickets/TicketDashboard";
import { TicketCreationForm } from "@/components/tickets/TicketCreationForm";
import { TicketSettingsPanel } from "@/components/tickets/TicketSettingsPanel";
import { TemplatePreview } from "@/components/tickets/TemplatePreview";
import { Alert, Button, Card } from "@/components/ui";
import { useJobsPreview, pickLatestJobId } from "@/data/jobsPreview";
import { TemplateMetadata } from "@/types/tickets";

const EXPERIENCE_ACTIVITY: Array<{ id: string; title: string; description: string; time: string; status: "success" | "info" | "warning"; }> = [
  {
    id: "highlight-1",
    title: "Ticket triage automation executed",
    description: "Root cause summary drafted and synced to ServiceNow and Jira.",
    time: "4 minutes ago",
    status: "success" as const,
  },
  {
    id: "highlight-2",
    title: "Customer briefing generated",
    description: "Incident digest distributed to customer success with next steps.",
    time: "16 minutes ago",
    status: "info" as const,
  },
  {
    id: "highlight-3",
    title: "Knowledge base refresh",
    description: "Self-service troubleshooting article updated with latest RCA.",
    time: "24 minutes ago",
    status: "warning" as const,
  },
];

const TEMPLATE_SAMPLE: TemplateMetadata = {
  name: "Customer Narrative Brief",
  platform: "jira",
  description: "Generate a customer-ready talking points bundle anchored to the latest RCA job output.",
  required_variables: ["customer_name", "impact_window", "next_update_at"],
  field_count: 6,
};

const TEMPLATE_VARIABLES: Record<string, string> = {
  customer_name: "Northwind Retail",
  impact_window: "14:05 - 14:34 UTC",
  next_update_at: "16:00 UTC",
};

export default function TicketsPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { jobs, loading: jobsLoading, error: jobError, refresh } = useJobsPreview();
  const [selectedJobId, setSelectedJobId] = useState<string | null>(null);

  const isAuthenticated = true;
  const queryJobId = useMemo(() => searchParams.get("jobId"), [searchParams]);

  useEffect(() => {
    if (queryJobId && queryJobId !== selectedJobId) {
      setSelectedJobId(queryJobId);
      return;
    }

    if (!queryJobId && jobs.length > 0 && !selectedJobId) {
      const latest = pickLatestJobId(jobs);
      if (latest) {
        setSelectedJobId(latest);
        router.replace(`/tickets?jobId=${encodeURIComponent(latest)}`, { scroll: false });
      }
    }
  }, [jobs, queryJobId, router, selectedJobId]);

  const fallbackJobId = useMemo(() => pickLatestJobId(jobs), [jobs]);
  const effectiveJobId = selectedJobId ?? fallbackJobId ?? "demo-job";

  const selectedJob = useMemo(() => jobs.find((job) => job.id === effectiveJobId) ?? null, [jobs, effectiveJobId]);

  const handleSelectJob = (jobId: string) => {
    setSelectedJobId(jobId);
    router.replace(`/tickets?jobId=${encodeURIComponent(jobId)}`, { scroll: false });
  };

  const handleStartInvestigation = () => {
    router.push('/investigation');
  };

  return (
    <div className="min-h-screen bg-dark-bg-primary">
      <Header showAuthActions={false} />
      <main className="container mx-auto flex flex-col gap-8 px-4 py-10 sm:px-6 lg:px-8">
        <section className="space-y-4">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <h1 className="text-3xl font-semibold text-dark-text-primary">Ticket automation control center</h1>
              <p className="mt-1 text-sm text-dark-text-secondary">
                Inspect job output, orchestrate ticket syncs, and manage platform templates without leaving this workspace.
              </p>
            </div>
            <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
              <Button size="lg" onClick={() => router.push("/")}>Back to executive overview</Button>
              <Button size="lg" variant="secondary" onClick={() => router.push("/jobs")}>Review job history</Button>
            </div>
          </div>
          {jobError && <Alert variant="warning">{jobError}</Alert>}
        </section>

        <CommandCenter
          jobs={jobs}
          jobsLoading={jobsLoading}
          jobError={jobError}
          isAuthenticated={isAuthenticated}
          onRefresh={refresh}
          onCreateJob={handleStartInvestigation}
          onSelectJob={handleSelectJob}
        />

        <section className="grid gap-6 lg:grid-cols-[minmax(0,7fr)_minmax(0,5fr)]">
          <TicketDashboard jobId={effectiveJobId} autoRefresh={false} />
          <div className="space-y-6">
            <TicketSettingsPanel />
            <TemplatePreview template={TEMPLATE_SAMPLE} variables={TEMPLATE_VARIABLES} />
          </div>
        </section>

        <section id="ticket-creation" className="grid gap-6 xl:grid-cols-[minmax(0,3fr)_minmax(0,2fr)]">
          <TicketCreationForm jobId={effectiveJobId} />
          <Card className="p-6">
            <h2 className="section-title">Automation highlights</h2>
            <p className="mt-2 text-sm text-dark-text-secondary">
              Share the latest hands-off updates to align SRE, customer success, and leadership teams on the same signal.
            </p>
            <div className="mt-6">
              <ExperienceShowcase activity={EXPERIENCE_ACTIVITY} />
            </div>
            {!selectedJob && (
              <Alert className="mt-6" variant="info">
                Select a job to personalize the drafting payloads and template hints.
              </Alert>
            )}
          </Card>
        </section>
      </main>
    </div>
  );
}
