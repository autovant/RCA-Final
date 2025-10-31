"use client";

import { Badge } from "@/components/ui";

type TicketSettings = {
  servicenow_enabled: boolean;
  jira_enabled: boolean;
  dual_mode: boolean;
} | null;

type ReliabilityPanelProps = {
  isAuthenticated: boolean;
  ticketSettings: TicketSettings;
  className?: string;
};

const statusItems = [
  { label: "API", value: "Online" },
  { label: "Database", value: "Connected" },
  { label: "LLM Service", value: "Ready" },
];

export function ReliabilityPanel({
  isAuthenticated,
  ticketSettings,
  className = "",
}: ReliabilityPanelProps) {
  const integrationBadges = [
    { label: "ServiceNow", enabled: ticketSettings?.servicenow_enabled },
    { label: "Jira", enabled: ticketSettings?.jira_enabled },
  ];

  return (
    <aside className={`h-full w-full ${className}`}>
      <div className="relative flex h-full flex-col gap-6 overflow-hidden rounded-3xl border border-dark-border/45 bg-dark-bg-secondary/80 p-6 shadow-fluent-lg backdrop-blur-2xl lg:sticky lg:top-24">
        <div className="pointer-events-none absolute inset-0 bg-gradient-to-br from-fluent-info/18 via-transparent to-dark-bg-secondary/85" aria-hidden="true" />
        <header className="relative flex items-center justify-between">
          <div>
            <p className="text-[0.6rem] font-semibold uppercase tracking-[0.26em] text-dark-text-tertiary">Reliability &amp; Access</p>
            <h3 className="mt-2 text-xl font-semibold text-dark-text-primary">Control Surface</h3>
          </div>
          <span className="inline-flex items-center gap-2 rounded-full border border-fluent-success/45 bg-fluent-success/20 px-4 py-1.5 text-[0.62rem] font-semibold uppercase tracking-[0.26em] text-green-200">
            <span className="relative inline-flex h-2.5 w-2.5 items-center justify-center">
              <span className="absolute inline-flex h-full w-full rounded-full bg-fluent-success/60 blur-sm" aria-hidden="true" />
              <span className="relative inline-block h-2.5 w-2.5 rounded-full bg-fluent-success" />
            </span>
            Live
          </span>
        </header>

        <section className="relative space-y-3 text-sm">
          {statusItems.map((item) => (
            <div
              key={item.label}
              className="flex items-center justify-between rounded-2xl border border-dark-border/35 bg-dark-bg-tertiary/55 px-4 py-3 shadow-[0_12px_28px_rgba(15,23,42,0.32)] backdrop-blur-xl"
            >
              <p className="text-sm font-semibold text-dark-text-secondary">{item.label}</p>
              <span className="inline-flex items-center gap-2 text-[0.6rem] font-semibold uppercase tracking-[0.22em] text-green-200">
                <span className="status-dot" />
                {item.value}
              </span>
            </div>
          ))}
        </section>

        <section className="relative rounded-2xl border border-dark-border/35 bg-dark-bg-tertiary/55 p-5 shadow-[0_12px_28px_rgba(15,23,42,0.32)] backdrop-blur-xl">
          <p className="text-[0.6rem] font-semibold uppercase tracking-[0.26em] text-dark-text-tertiary">Integrations</p>
          <div className="mt-4 flex flex-wrap gap-2">
            {integrationBadges.map((integration) => (
              <Badge
                key={integration.label}
                variant={integration.enabled ? "success" : "neutral"}
                className="tracking-[0.26em]"
              >
                {integration.label}
              </Badge>
            ))}
          </div>
          {!isAuthenticated && (
            <p className="mt-3 text-xs text-dark-text-tertiary">
              Sign in to manage service integrations and guardrail settings.
            </p>
          )}
        </section>

        <section className="relative rounded-2xl border border-dark-border/35 bg-dark-bg-tertiary/55 p-5 shadow-[0_12px_28px_rgba(15,23,42,0.32)] backdrop-blur-xl">
          <p className="text-[0.6rem] font-semibold uppercase tracking-[0.26em] text-dark-text-tertiary">Guardrails</p>
          <ul className="mt-4 space-y-3 text-xs text-dark-text-secondary">
            <li className="flex items-center justify-between">
              <span>Dual mode approvals</span>
              <Badge variant={ticketSettings?.dual_mode ? "info" : "neutral"}>
                {ticketSettings?.dual_mode ? "Active" : "Off"}
              </Badge>
            </li>
            <li className="flex items-center justify-between">
              <span>Human checkpoints</span>
              <Badge variant="info">On</Badge>
            </li>
          </ul>
        </section>
      </div>
    </aside>
  );
}
