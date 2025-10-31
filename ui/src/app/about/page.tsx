"use client";

import { HeroBanner } from "@/components/dashboard/HeroBanner";
import { WorkflowShowcase } from "@/components/dashboard/WorkflowShowcase";
import { ExperienceShowcase } from "@/components/dashboard/ExperienceShowcase";
import { WORKFLOW_STEPS } from "@/data/workflowSteps";
import { Header } from "@/components/layout/Header";

const ABOUT_STATS = {
  totalJobs: 128,
  completedJobs: 117,
  successRate: 92,
  lastJobAt: "Rolling 7-day window",
};

const ABOUT_ACTIVITY = [
  {
    id: "about-activity-1",
    title: "RAG evidence bundle created",
    description: "Retrieval copilots packaged log anomalies and timeline context for the runbook.",
    time: "Moments ago",
    status: "success" as const,
  },
  {
    id: "about-activity-2",
    title: "ServiceNow dual-mode sync",
    description: "Automation posted status updates to ServiceNow while mirroring Jira for engineering.",
    time: "3 mins ago",
    status: "info" as const,
  },
  {
    id: "about-activity-3",
    title: "🔒 PII Protection: 247 items redacted",
    description: "Multi-pass scanning caught AWS keys, JWT tokens, and DB credentials. Validation passed with zero warnings before executive summary distribution.",
    time: "12 mins ago",
    status: "success" as const,
  },
  {
    id: "about-activity-4",
    title: "Customer-ready digest exported",
    description: "Stakeholders received HTML + Markdown RCA packets in under 15 minutes.",
    time: "18 mins ago",
    status: "success" as const,
  },
];

const CAPABILITIES = [
  {
    title: "AI-guided triage",
    description:
      "Large language models triage incoming signals, clustering similar incidents while surfacing anomalies that need human judgement.",
  },
  {
    title: "Retrieval-augmented copilots",
    description:
      "Vector search over your logs, tickets, and runbooks feeds the copilots so every recommendation cites the evidence backing it.",
  },
  {
    title: "🔒 Enterprise PII Protection & Guardrails",
    description:
      "Military-grade multi-layer redaction with 30+ pattern types ensures zero sensitive data reaches LLMs. Real-time stats, multi-pass scanning, and strict validation protect cloud credentials, auth secrets, crypto keys, and personal data. Every RCA pass travels through security checkpoints and approval workflows.",
  },
  {
    title: "Multimodal outputs",
    description:
      "Generate Markdown, HTML, and structured JSON bundles that pipe into ITSM tools, executive dashboards, or briefing packs.",
  },
];

export default function AboutPage() {
  return (
    <div className="min-h-screen bg-dark-bg-primary">
      <Header />

      <main className="container mx-auto px-4 sm:px-6 lg:px-8 py-12 space-y-12">
      <HeroBanner
        isAuthenticated={false}
        onPrimaryAction={() => {}}
        onSecondaryAction={() => {}}
        onLogin={() => {}}
        onSignup={() => {}}
        stats={ABOUT_STATS}
        showActions={false}
        heading="RCA Engine orchestrates AI-guided automation for support teams"
        subtitle="Retrieval-augmented workflows collect the right evidence, AI copilots draft the narrative, and your humans stay in control of the outcome."
        talkingPoints={[
          "Purpose-built for automation support and SRE teams",
          "Retrieval pipelines keep every recommendation grounded in facts",
          "Enterprise-grade PII protection: 30+ pattern types, multi-pass scanning, zero data leakage",
          "Governed workflows respect compliance, redaction, and audit trails",
        ]}
        eyebrow="About RCA Engine"
      />

      <section className="grid gap-6 md:grid-cols-2">
        {CAPABILITIES.map((capability) => (
          <div
            key={capability.title}
            className="rounded-2xl border border-dark-border/60 bg-dark-bg-secondary/80 p-6 shadow-fluent"
          >
            <h3 className="text-lg font-semibold text-dark-text-primary">{capability.title}</h3>
            <p className="mt-2 text-sm text-dark-text-secondary">{capability.description}</p>
          </div>
        ))}
      </section>

      <WorkflowShowcase steps={WORKFLOW_STEPS} />

      <ExperienceShowcase activity={ABOUT_ACTIVITY} />
      </main>
    </div>
  );
}
