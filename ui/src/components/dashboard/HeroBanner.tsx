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
      <div className="relative flex h-full flex-col overflow-hidden rounded-3xl border border-dark-border/45 bg-dark-bg-secondary/75 px-6 py-10 shadow-fluent-lg backdrop-blur-2xl sm:px-10 sm:py-14">
        <div className="absolute inset-0 bg-gradient-to-br from-fluent-blue-500/18 via-transparent to-fluent-info/8" aria-hidden="true" />
        <div className="absolute -top-36 -left-24 h-72 w-72 rounded-full bg-fluent-blue-500/30 blur-[120px]" aria-hidden="true" />
        <div className="absolute bottom-[-40%] right-[-10%] h-96 w-96 rounded-full bg-gradient-to-br from-fluent-info/18 via-transparent to-transparent blur-[140px]" aria-hidden="true" />

        <div className="relative z-10 flex h-full flex-col">
          <div className="space-y-5">
            {eyebrow && (
              <p className="inline-flex items-center rounded-full border border-fluent-blue-500/30 bg-dark-bg-primary/60 px-4 py-1 text-xs font-semibold uppercase tracking-[0.28em] text-fluent-info">
                {eyebrow}
              </p>
            )}
            <div className="space-y-4">
              <h1 id="hero-heading" className="hero-title max-w-3xl">
                {headline}
              </h1>
              <p className="hero-subtitle max-w-2xl">{supporting}</p>
            </div>
            <ul className="grid gap-3 text-sm text-dark-text-secondary sm:grid-cols-2 lg:grid-cols-3">
              {bullets.map((point) => (
                <li
                  key={point}
                  className="group flex items-start gap-3 rounded-2xl border border-dark-border/35 bg-dark-bg-tertiary/55 px-4 py-3 shadow-[0_14px_34px_rgba(15,23,42,0.32)] transition-all duration-200 hover:-translate-y-0.5 hover:border-fluent-blue-400/50 hover:shadow-[0_18px_40px_rgba(56,189,248,0.25)]"
                >
                  <span className="hero-bullet mt-1.5" aria-hidden="true" />
                  <p className="font-medium leading-relaxed text-dark-text-secondary">{point}</p>
                </li>
              ))}
            </ul>
          </div>

          {showActions && (
            <div className="mt-8 flex flex-col gap-3 sm:flex-row sm:items-center">
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
            <div className="mt-auto grid gap-4 pt-10 text-sm text-dark-text-tertiary sm:grid-cols-3">
              <div className="rounded-2xl border border-fluent-blue-500/25 bg-dark-bg-tertiary/65 p-5 backdrop-blur-xl">
                <span className="hero-metric text-3xl">{stats.successRate}%</span>
                <p className="mt-2 text-[0.6rem] font-semibold uppercase tracking-[0.24em] text-dark-text-tertiary">Success Rate</p>
                <p className="mt-3 text-xs text-dark-text-tertiary">Across {stats.totalJobs} runs</p>
              </div>
              <div className="rounded-2xl border border-fluent-blue-500/25 bg-dark-bg-tertiary/65 p-5 backdrop-blur-xl">
                <span className="hero-metric text-3xl">{stats.completedJobs}</span>
                <p className="mt-2 text-[0.6rem] font-semibold uppercase tracking-[0.24em] text-dark-text-tertiary">Completed</p>
                <p className="mt-3 text-xs text-dark-text-tertiary">Closed without escalation</p>
              </div>
              <div className="rounded-2xl border border-fluent-blue-500/25 bg-dark-bg-tertiary/65 p-5 backdrop-blur-xl">
                <span className="hero-metric text-3xl">{stats.lastJobAt ? stats.lastJobAt : "—"}</span>
                <p className="mt-2 text-[0.6rem] font-semibold uppercase tracking-[0.24em] text-dark-text-tertiary">Last Execution</p>
                <p className="mt-3 text-xs text-dark-text-tertiary">Most recent completion time</p>
              </div>
            </div>
          )}
        </div>
      </div>
    </section>
  );
}
