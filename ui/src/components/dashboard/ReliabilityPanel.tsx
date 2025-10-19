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
      <div className="relative flex h-full flex-col gap-5 overflow-hidden rounded-3xl border border-dark-border/50 bg-dark-bg-secondary/75 p-6 shadow-fluent backdrop-blur-2xl lg:sticky lg:top-24">
        <div className="pointer-events-none absolute inset-0 bg-gradient-to-br from-fluent-info/15 via-transparent to-dark-bg-secondary/80" aria-hidden="true" />
        <header className="relative flex items-center justify-between">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.26em] text-dark-text-tertiary">Reliability &amp; Access</p>
            <h3 className="mt-2 text-xl font-semibold text-dark-text-primary">Control Surface</h3>
          </div>
          <span className="inline-flex items-center gap-2 rounded-full border border-dark-border/40 bg-dark-bg-tertiary/70 px-4 py-1.5 text-xs font-semibold uppercase tracking-[0.24em] text-fluent-success">
            <span className="relative inline-flex h-2 w-2 items-center justify-center">
              <span className="absolute inline-flex h-full w-full rounded-full bg-fluent-success/60 blur-sm" aria-hidden="true" />
              <span className="relative inline-block h-2 w-2 rounded-full bg-fluent-success" />
            </span>
            Live
          </span>
        </header>

        <section className="relative space-y-3 text-sm">
          {statusItems.map((item) => (
            <div key={item.label} className="flex items-center justify-between rounded-2xl border border-dark-border/40 bg-dark-bg-tertiary/60 px-4 py-3">
              <p className="text-sm font-semibold text-dark-text-secondary">{item.label}</p>
              <span className="inline-flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.18em] text-fluent-success">
                <span className="status-dot" />
                {item.value}
              </span>
            </div>
          ))}
        </section>

        <section className="relative">
          <p className="text-xs font-semibold uppercase tracking-[0.24em] text-dark-text-tertiary">Integrations</p>
          <div className="mt-3 flex flex-wrap gap-2">
            {integrationBadges.map((integration) => (
              <Badge
                key={integration.label}
                variant={integration.enabled ? "success" : "neutral"}
              >
                {integration.label}
              </Badge>
            ))}
          </div>
          {!isAuthenticated && (
            <p className="mt-3 text-xs text-dark-text-tertiary">
              Connect service integrations after signing in to enable automation.
            </p>
          )}
        </section>

        <section className="relative rounded-2xl border border-dark-border/40 bg-dark-bg-tertiary/55 p-4">
          <p className="text-xs font-semibold uppercase tracking-[0.24em] text-dark-text-tertiary">Guardrails</p>
          <ul className="mt-3 space-y-2 text-xs text-dark-text-secondary">
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
