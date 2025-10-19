"use client";

import { Button } from "@/components/ui";

type HeroBannerProps = {
  isAuthenticated: boolean;
  onPrimaryAction: () => void;
  onSecondaryAction: () => void;
  onLogin: () => void;
  onSignup: () => void;
  stats: {
    totalJobs: number;
    completedJobs: number;
    successRate: number;
    lastJobAt: string | null;
  };
  heading?: string;
  subtitle?: string;
  talkingPoints?: string[];
  showActions?: boolean;
  showStats?: boolean;
  eyebrow?: string;
  className?: string;
};

export function HeroBanner({
  isAuthenticated,
  onPrimaryAction,
  onSecondaryAction,
  onLogin,
  onSignup,
  stats,
  heading,
  subtitle,
  talkingPoints,
  showActions = true,
  showStats = true,
  eyebrow,
  className = "",
}: HeroBannerProps) {
  const headline = heading ?? "Keeps incidents calm, customers confident, and teams aligned.";
  const supporting =
    subtitle ??
    "AI-guided, retrieval-augmented workflows accelerate investigations and maintain executive-ready communications.";
  const bullets =
    talkingPoints ?? [
      "Guided automation from signal to summary",
      "Retrieval-augmented copilots surface the right evidence",
      "Human-in-the-loop safeguards on every run",
    ];

  return (
    <section className={`hero-surface h-full animate-fade-in ${className}`} aria-labelledby="hero-heading">
      <div className="relative flex h-full flex-col overflow-hidden rounded-3xl border border-dark-border/50 bg-dark-bg-secondary/70 px-6 py-10 sm:px-10 sm:py-14">
        <div className="absolute inset-0 bg-gradient-to-br from-fluent-blue-500/15 via-transparent to-fluent-info/5" aria-hidden="true" />
        <div className="absolute -top-32 -left-20 h-72 w-72 rounded-full bg-fluent-blue-500/30 blur-3xl" aria-hidden="true" />
        <div className="absolute inset-y-0 right-[-8%] hidden w-1/2 max-w-md items-center justify-center lg:flex">
          <div className="hero-orb" />
        </div>

        <div className="relative z-10 flex h-full max-w-3xl flex-col space-y-6">
          <div className="space-y-4">
            {eyebrow && (
              <p className="inline-flex items-center rounded-full border border-fluent-blue-500/30 bg-fluent-blue-500/10 px-4 py-1 text-xs font-semibold uppercase tracking-[0.28em] text-dark-text-secondary">
                {eyebrow}
              </p>
            )}
            <h1 id="hero-heading" className="hero-title">
              {headline}
            </h1>
            <p className="hero-subtitle">{supporting}</p>
          </div>

          <ul className="grid gap-3 text-sm text-dark-text-secondary sm:grid-cols-2 lg:grid-cols-3">
            {bullets.map((point) => (
              <li key={point} className="flex items-start gap-3 rounded-2xl border border-dark-border/40 bg-dark-bg-tertiary/60 px-4 py-3 shadow-[0_10px_30px_rgba(15,23,42,0.35)]">
                <span className="hero-bullet mt-1.5" aria-hidden="true" />
                <p className="font-medium leading-relaxed text-dark-text-secondary">{point}</p>
              </li>
            ))}
          </ul>

          {showActions && (
            <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
              {isAuthenticated ? (
                <>
                  <Button size="lg" onClick={onPrimaryAction}>
                    Launch New Analysis
                  </Button>
                  <Button size="lg" variant="secondary" onClick={onSecondaryAction}>
                    Review Recent Jobs
                  </Button>
                </>
              ) : (
                <>
                  <Button size="lg" onClick={onLogin}>
                    Log In and Explore
                  </Button>
                  <Button size="lg" variant="secondary" onClick={onSignup}>
                    Create an Account
                  </Button>
                </>
              )}
            </div>
          )}

          {showStats && isAuthenticated && (
            <div className="mt-auto grid gap-6 pt-6 text-sm text-dark-text-tertiary sm:grid-cols-3">
              <div className="rounded-2xl border border-fluent-blue-500/20 bg-dark-bg-tertiary/60 p-4">
                <span className="hero-metric text-3xl">{stats.successRate}%</span>
                <p className="mt-1 text-xs uppercase tracking-[0.2em] text-dark-text-tertiary">Success Rate</p>
                <p className="mt-2 text-xs text-dark-text-tertiary">Across {stats.totalJobs} runs</p>
              </div>
              <div className="rounded-2xl border border-fluent-blue-500/20 bg-dark-bg-tertiary/60 p-4">
                <span className="hero-metric text-3xl">{stats.completedJobs}</span>
                <p className="mt-1 text-xs uppercase tracking-[0.2em] text-dark-text-tertiary">Completed</p>
                <p className="mt-2 text-xs text-dark-text-tertiary">Closed without escalation</p>
              </div>
              <div className="rounded-2xl border border-fluent-blue-500/20 bg-dark-bg-tertiary/60 p-4">
                <span className="hero-metric text-3xl">{stats.lastJobAt ? stats.lastJobAt : "—"}</span>
                <p className="mt-1 text-xs uppercase tracking-[0.2em] text-dark-text-tertiary">Last Execution</p>
                <p className="mt-2 text-xs text-dark-text-tertiary">Most recent completion time</p>
              </div>
            </div>
          )}
        </div>
      </div>
    </section>
  );
}
