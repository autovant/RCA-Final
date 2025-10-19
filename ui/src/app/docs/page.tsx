"use client";

import Link from "next/link";
import { Header } from "@/components/layout/Header";
import { HeroBanner } from "@/components/dashboard/HeroBanner";
import { Alert, Badge, Card } from "@/components/ui";

const heroStats = {
  totalJobs: 128,
  completedJobs: 117,
  successRate: 92,
  lastJobAt: null,
};

const docCollections = [
  {
    title: "Launch & Deployment",
    description: "Stand up RCA Engine confidently across staging and production with scripts, runbooks, and pre-flight validations.",
    items: [
      {
        label: "Deployment checklist",
        description: "Structured sequence from network prerequisites to smoke tests.",
        href: "https://github.com/autovant/RCA-Final/blob/master/DEPLOYMENT_CHECKLIST.md",
      },
      {
        label: "Docker deployment guide",
        description: "Hardened container path with scaling notes for multi-region installs.",
        href: "https://github.com/autovant/RCA-Final/blob/master/DOCKER_DEPLOYMENT_GUIDE.md",
      },
      {
        label: "Network access troubleshooting",
        description: "Resolve egress blockers, WSL port mirroring, and firewall drift fast.",
        href: "https://github.com/autovant/RCA-Final/blob/master/TROUBLESHOOTING_ACCESS.md",
      },
    ],
  },
  {
    title: "Authentication & Controls",
    description: "Secure the surface area with modern auth, observability, and review guardrails.",
    items: [
      {
        label: "Authentication quickstart",
        description: "SAML, OIDC, and service token flows mapped across personas.",
        href: "https://github.com/autovant/RCA-Final/blob/master/AUTHENTICATION_GUIDE.md",
      },
      {
        label: "Access posture brief",
        description: "How RCA Engine enforces dual-review and audit logging by default.",
        href: "https://github.com/autovant/RCA-Final/blob/master/PRD.md",
      },
      {
        label: "Reliability control surface",
        description: "Detailed sidebar reference covering health signals and integration toggles.",
        href: "https://github.com/autovant/RCA-Final/blob/master/BACKEND_ROUTING_RESOLVED.md",
      },
    ],
  },
  {
    title: "AI & RAG Playbooks",
    description: "Operationalize retrieval-augmented automation with source governance and human-in-the-loop checkpoints.",
    items: [
      {
        label: "Copilot orchestration",
        description: "Blend automation runs with human approvals and executive-ready narratives.",
        href: "https://github.com/autovant/RCA-Final/blob/master/IMPLEMENTATION_SUMMARY.md",
      },
      {
        label: "Knowledge routing",
        description: "Curating retrieval sets so every run cites trustworthy evidence.",
        href: "https://github.com/autovant/RCA-Final/blob/master/SOLUTION_WSL_IP_ACCESS.md",
      },
      {
        label: "Demo choreography",
        description: "Deliver rehearsed walkthroughs without exposing internal systems.",
        href: "https://github.com/autovant/RCA-Final/blob/master/README-SIMPLE.md",
      },
    ],
  },
];

const quickLinks = [
  {
    label: "API reference",
    href: "https://github.com/autovant/RCA-Final/blob/master/API_ROUTING_FIX_GUIDE.md",
    description: "Endpoints, payload contracts, and signature requirements.",
  },
  {
    label: "Integration toggles",
    href: "https://github.com/autovant/RCA-Final/blob/master/ISSUE_RESOLUTION_CREATE_ACCOUNT.md",
    description: "Enable ServiceNow or Jira dual-mode paths when ready for production.",
  },
  {
    label: "Incident communications",
    href: "https://github.com/autovant/RCA-Final/blob/master/IMPLEMENTATION_COMPLETE_SUMMARY.md",
    description: "Templates for executive updates and customer talking points.",
  },
];

const releaseHighlights = [
  {
    date: "October 2025",
    summary: "RCA Engine dashboard redesign delivers quicker cueing of AI copilots and a dedicated About narrative.",
  },
  {
    date: "September 2025",
    summary: "Dual-mode ITSM integrations reach GA with managed guardrails for ServiceNow and Jira.",
  },
];

export default function DocsPage() {
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
          stats={heroStats}
          heading="Documentation engineered for executive-ready delivery."
          subtitle="Preview our living library of runbooks, integrations, and AI governance so your rollout stays on pace."
          talkingPoints={[
            "Launch guides built with enterprise change management in mind",
            "Security and RAG policies paired with quick-reference visuals",
            "Demo-ready storytelling for customer and leadership sessions",
          ]}
          showActions={false}
          showStats={false}
          eyebrow="KNOWLEDGE CENTER"
        />

        <section className="mt-10 grid gap-6 lg:grid-cols-[2fr,1fr]">
          <div className="space-y-6">
            {docCollections.map((collection) => (
              <Card key={collection.title} className="p-6">
                <div className="flex items-start justify-between gap-4">
                  <div>
                    <h2 className="section-title">{collection.title}</h2>
                    <p className="mt-2 text-sm text-dark-text-secondary">{collection.description}</p>
                  </div>
                  <Badge variant="info">Updated</Badge>
                </div>
                <ul className="mt-6 space-y-4">
                  {collection.items.map((item) => (
                    <li key={item.label} className="rounded-xl border border-dark-border/70 bg-dark-bg-tertiary/60 p-4 transition-all duration-200 hover:border-fluent-blue-400/60 hover:-translate-y-0.5">
                      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                        <div>
                          <p className="text-sm font-semibold text-dark-text-primary">{item.label}</p>
                          <p className="mt-1 text-sm text-dark-text-secondary">{item.description}</p>
                        </div>
                        <Link
                          href={item.href}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="btn-secondary whitespace-nowrap"
                        >
                          Open guide
                        </Link>
                      </div>
                    </li>
                  ))}
                </ul>
              </Card>
            ))}
          </div>

          <aside className="space-y-6">
            <Card className="p-6">
              <h2 className="section-title">Quick links</h2>
              <ul className="mt-4 space-y-4 text-sm text-dark-text-secondary">
                {quickLinks.map((link) => (
                  <li key={link.label} className="group">
                    <Link
                      href={link.href}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="flex flex-col rounded-lg border border-transparent px-3 py-2 transition-all duration-200 group-hover:border-fluent-blue-400/60 group-hover:bg-dark-bg-tertiary/60"
                    >
                      <span className="text-dark-text-primary font-medium">{link.label}</span>
                      <span className="mt-1 text-xs text-dark-text-secondary">{link.description}</span>
                    </Link>
                  </li>
                ))}
              </ul>
            </Card>

            <Card className="p-6">
              <h2 className="section-title">Release highlights</h2>
              <ul className="mt-4 space-y-4 text-sm text-dark-text-secondary">
                {releaseHighlights.map((entry) => (
                  <li key={entry.date} className="rounded-lg border border-dark-border/70 bg-dark-bg-tertiary/60 p-4">
                    <p className="text-xs uppercase tracking-[0.2em] text-dark-text-tertiary">{entry.date}</p>
                    <p className="mt-2 text-dark-text-primary">{entry.summary}</p>
                  </li>
                ))}
              </ul>
            </Card>

            <Alert variant="info">
              <div>
                <p className="font-semibold">Living documentation</p>
                <p className="text-sm text-dark-text-secondary mt-1">
                  Every guide is authored by our product and operations leads. Expect weekly refreshes as new workflows or integrations reach preview.
                </p>
              </div>
            </Alert>
          </aside>
        </section>
      </main>
    </div>
  );
}
