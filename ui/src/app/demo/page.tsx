"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Header } from "@/components/layout/Header";
import { Alert, Badge, Button, Card, Spinner } from "@/components/ui";

type PanelContent =
  | {
      type: "code";
      label: string;
      content: string;
      language?: string;
    }
  | {
      type: "insight";
      label: string;
      content: string;
    }
  | {
      type: "list";
      label: string;
      items: Array<{
        title: string;
        summary: string;
        timestamp: string;
        score?: number;
      }>;
    };

type Metric = {
  label: string;
  value: string;
  tone?: "success" | "warning" | "error" | "info" | "neutral";
  annotation?: string;
};

type TimelineEntry = {
  label: string;
  value: string;
};

type DemoLink = {
  label: string;
  href: string;
};

type DemoScenario = {
  id: string;
  title: string;
  tagline: string;
  summary: string;
  panels: {
    primary: PanelContent;
    secondary: PanelContent;
  };
  metrics: Metric[];
  talkingPoints: string[];
  timeline?: TimelineEntry[];
  links?: DemoLink[];
};

type ScenarioPayload = {
  updated?: string;
  scenarios?: DemoScenario[];
};

const toneMap: Record<string, "success" | "warning" | "error" | "info" | "neutral"> = {
  success: "success",
  warning: "warning",
  error: "error",
  info: "info",
  neutral: "neutral",
};

const renderPanel = (panel: PanelContent) => {
  if (panel.type === "code") {
    return (
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <span className="text-xs font-semibold uppercase tracking-[0.22em] text-dark-text-tertiary">
            {panel.label}
          </span>
          {panel.language && (
            <Badge variant="neutral" className="text-[0.65rem]">
              {panel.language.toUpperCase()}
            </Badge>
          )}
        </div>
        <pre className="rounded-xl border border-dark-border/50 bg-dark-bg-tertiary/60 p-4 text-xs leading-relaxed text-dark-text-secondary shadow-inner">
          <code>{panel.content}</code>
        </pre>
      </div>
    );
  }

  if (panel.type === "list") {
    return (
      <div className="space-y-3">
        <span className="text-xs font-semibold uppercase tracking-[0.22em] text-dark-text-tertiary">
          {panel.label}
        </span>
        <div className="space-y-3">
          {panel.items.map((item) => (
            <div
              key={`${panel.label}-${item.title}`}
              className="rounded-xl border border-dark-border/40 bg-dark-bg-tertiary/50 p-4"
            >
              <div className="flex flex-wrap items-center justify-between gap-2">
                <h4 className="text-sm font-semibold text-dark-text-primary">{item.title}</h4>
                {typeof item.score === "number" && (
                  <Badge variant="info" className="text-[0.65rem]">
                    Score {item.score.toFixed(2)}
                  </Badge>
                )}
              </div>
              <p className="mt-2 text-xs text-dark-text-secondary">{item.summary}</p>
              <p className="mt-3 text-[0.6rem] uppercase tracking-[0.24em] text-dark-text-tertiary">
                {item.timestamp}
              </p>
            </div>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      <span className="text-xs font-semibold uppercase tracking-[0.22em] text-dark-text-tertiary">
        {panel.label}
      </span>
      <div className="rounded-xl border border-dark-border/45 bg-dark-bg-tertiary/60 p-4 text-sm leading-relaxed text-dark-text-secondary">
        {panel.content.split("\n").map((line) => (
          <p key={`${panel.label}-${line}`} className="whitespace-pre-wrap">
            {line}
          </p>
        ))}
      </div>
    </div>
  );
};

export default function DemoPage() {
  const router = useRouter();
  const [scenarios, setScenarios] = useState<DemoScenario[]>([]);
  const [selectedScenarioId, setSelectedScenarioId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    const load = async () => {
      try {
        const response = await fetch("/demo/scenarios.json", { cache: "no-store" });
        if (!response.ok) {
          throw new Error(`Failed to load demo scenarios (${response.status})`);
        }
        const payload = (await response.json()) as ScenarioPayload;
        if (!cancelled) {
          const loaded = payload.scenarios ?? [];
          setScenarios(loaded);
          setSelectedScenarioId((prev) => prev ?? loaded[0]?.id ?? null);
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "Unable to load demo content");
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    };

    load();

    return () => {
      cancelled = true;
    };
  }, []);

  const selectedScenario = useMemo(
    () => scenarios.find((scenario) => scenario.id === selectedScenarioId) ?? null,
    [scenarios, selectedScenarioId]
  );

  return (
    <div className="relative min-h-screen bg-dark-bg-primary">
      <Header showAuthActions={false} />

      <main className="container mx-auto flex flex-col gap-12 px-4 pt-24 pb-16 sm:px-6 lg:px-8 lg:gap-16 lg:pt-28">
        <section className="space-y-6 lg:space-y-8">
          <div className="relative overflow-hidden rounded-3xl border border-fluent-blue-500/30 bg-gradient-to-br from-fluent-blue-500/15 via-dark-bg-secondary/70 to-dark-bg-primary p-8 shadow-[0_28px_64px_rgba(14,116,220,0.2)]">
            <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_left,rgba(56,189,248,0.25),transparent_55%)]" aria-hidden="true" />
            <div className="relative flex flex-col gap-6 lg:flex-row lg:items-end lg:justify-between">
              <div className="space-y-4">
                <p className="text-xs font-semibold uppercase tracking-[0.28em] text-fluent-blue-100">
                  Guided Experience
                </p>
                <h1 className="text-3xl font-bold leading-tight text-dark-text-primary sm:text-4xl">
                  Demo the RCA Engine in four minutes flat
                </h1>
                <p className="max-w-3xl text-sm text-dark-text-secondary sm:text-base">
                  Walk stakeholders through live redaction, semantic search, executive-ready classifications, and automatic platform detection without touching production data.
                </p>
              </div>
              <div className="flex flex-col gap-3 sm:flex-row">
                <Link href="/investigation" className="sm:w-auto">
                  <Button size="lg" className="w-full">
                    Start Live Investigation
                  </Button>
                </Link>
                <Button
                  size="lg"
                  variant="ghost"
                  className="w-full"
                  onClick={() => router.push("/features")}
                >
                  Review Feature Catalog
                </Button>
              </div>
            </div>
          </div>

          {loading && (
            <div className="flex items-center justify-center py-24">
              <Spinner size="lg" />
            </div>
          )}

          {error && !loading && (
            <Alert variant="error" title="Demo data unavailable">
              {error}
            </Alert>
          )}

          {!loading && !error && selectedScenario && (
            <div className="grid gap-6 lg:grid-cols-[minmax(0,280px)_minmax(0,1fr)] xl:gap-10">
              <aside className="space-y-4">
                <Card className="space-y-3 border-dark-border/50 bg-dark-bg-secondary/70 p-4">
                  <p className="text-xs font-semibold uppercase tracking-[0.24em] text-dark-text-tertiary">
                    Highlighted Scenarios
                  </p>
                  <div className="flex flex-col gap-2">
                    {scenarios.map((scenario) => {
                      const isActive = scenario.id === selectedScenarioId;
                      return (
                        <button
                          key={scenario.id}
                          type="button"
                          onClick={() => setSelectedScenarioId(scenario.id)}
                          className={`flex w-full items-start gap-3 rounded-2xl border px-3 py-3 text-left transition-all duration-200 ${
                            isActive
                              ? "border-fluent-blue-400/50 bg-fluent-blue-500/15 text-dark-text-primary shadow-[0_0_24px_rgba(56,189,248,0.2)]"
                              : "border-dark-border/40 bg-dark-bg-tertiary/50 text-dark-text-secondary hover:border-fluent-blue-400/30 hover:text-dark-text-primary"
                          }`}
                        >
                          <span className="mt-1 flex h-6 w-6 items-center justify-center rounded-xl border border-fluent-blue-400/40 bg-fluent-blue-500/15 text-[0.65rem] font-semibold text-fluent-blue-100">
                            {String(scenarios.indexOf(scenario) + 1).padStart(2, "0")}
                          </span>
                          <div className="space-y-1">
                            <p className="text-sm font-semibold leading-tight">{scenario.title}</p>
                            <p className="text-xs text-dark-text-tertiary">{scenario.tagline}</p>
                          </div>
                        </button>
                      );
                    })}
                  </div>
                </Card>
              </aside>

              <article className="space-y-6">
                <Card className="space-y-6 border-dark-border/45 bg-dark-bg-secondary/80 p-6">
                  <div className="space-y-2">
                    <Badge variant="info" className="text-[0.65rem] uppercase tracking-[0.24em]">
                      {selectedScenario.tagline}
                    </Badge>
                    <h2 className="text-2xl font-semibold text-dark-text-primary sm:text-3xl">
                      {selectedScenario.title}
                    </h2>
                    <p className="text-sm leading-relaxed text-dark-text-secondary">
                      {selectedScenario.summary}
                    </p>
                  </div>

                  {selectedScenario.metrics.length > 0 && (
                    <div className="grid gap-4 sm:grid-cols-2">
                      {selectedScenario.metrics.map((metric) => (
                        <div
                          key={`${selectedScenario.id}-${metric.label}`}
                          className="rounded-2xl border border-dark-border/40 bg-dark-bg-tertiary/60 p-4"
                        >
                          <p className="text-xs font-semibold uppercase tracking-[0.22em] text-dark-text-tertiary">
                            {metric.label}
                          </p>
                          <p className="mt-2 text-xl font-semibold text-dark-text-primary">
                            {metric.value}
                          </p>
                          {metric.annotation && (
                            <p className="mt-2 text-xs text-dark-text-secondary">{metric.annotation}</p>
                          )}
                          <Badge
                            variant={toneMap[metric.tone ?? "neutral"]}
                            className="mt-3 text-[0.65rem]"
                          >
                            {metric.tone ? metric.tone.toUpperCase() : "NEUTRAL"}
                          </Badge>
                        </div>
                      ))}
                    </div>
                  )}

                  <div className="grid gap-6 lg:grid-cols-2">
                    {renderPanel(selectedScenario.panels.primary)}
                    {renderPanel(selectedScenario.panels.secondary)}
                  </div>

                  {selectedScenario.talkingPoints.length > 0 && (
                    <div className="space-y-2">
                      <h3 className="text-sm font-semibold uppercase tracking-[0.22em] text-dark-text-tertiary">
                        Demo Script Highlights
                      </h3>
                      <ul className="space-y-2 text-sm text-dark-text-secondary">
                        {selectedScenario.talkingPoints.map((point) => (
                          <li key={`${selectedScenario.id}-${point}`} className="flex items-start gap-2">
                            <span className="mt-1 h-1.5 w-1.5 rounded-full bg-fluent-blue-400" aria-hidden="true" />
                            <span>{point}</span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {selectedScenario.timeline && selectedScenario.timeline.length > 0 && (
                    <div className="space-y-3">
                      <h3 className="text-sm font-semibold uppercase tracking-[0.22em] text-dark-text-tertiary">
                        Timeline Beats
                      </h3>
                      <div className="flex flex-wrap gap-3">
                        {selectedScenario.timeline.map((step) => (
                          <div
                            key={`${selectedScenario.id}-${step.label}`}
                            className="flex items-center gap-2 rounded-full border border-dark-border/40 bg-dark-bg-tertiary/60 px-4 py-2"
                          >
                            <span className="text-xs font-semibold uppercase tracking-[0.24em] text-dark-text-secondary">
                              {step.label}
                            </span>
                            <Badge variant="neutral" className="text-[0.65rem]">
                              {step.value}
                            </Badge>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {selectedScenario.links && selectedScenario.links.length > 0 && (
                    <div className="flex flex-wrap gap-3 pt-2">
                      {selectedScenario.links.map((link) => (
                        <Link key={`${selectedScenario.id}-${link.label}`} href={link.href}>
                          <Button variant="ghost" size="sm" className="uppercase tracking-[0.22em]">
                            {link.label}
                          </Button>
                        </Link>
                      ))}
                    </div>
                  )}
                </Card>
              </article>
            </div>
          )}
        </section>
      </main>
    </div>
  );
}
