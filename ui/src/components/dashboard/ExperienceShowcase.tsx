"use client";

type ActivityItem = {
  id: string;
  title: string;
  description: string;
  time: string;
  status: "success" | "warning" | "error" | "info";
};

type ExperienceShowcaseProps = {
  activity: ActivityItem[];
};

const statusAccent = {
  success: "from-fluent-success/28 to-fluent-success/5 text-green-100 border-fluent-success/30",
  warning: "from-fluent-warning/28 to-fluent-warning/5 text-yellow-100 border-fluent-warning/30",
  error: "from-fluent-error/28 to-fluent-error/5 text-red-100 border-fluent-error/30",
  info: "from-fluent-info/28 to-fluent-info/5 text-cyan-100 border-fluent-info/30",
};

export function ExperienceShowcase({ activity }: ExperienceShowcaseProps) {
  return (
    <section aria-labelledby="experience-heading" className="space-y-5">
      <div className="relative overflow-hidden rounded-3xl border border-dark-border/45 bg-dark-bg-secondary/80 p-6 shadow-[0_20px_46px_rgba(15,23,42,0.35)] backdrop-blur-2xl">
        <div className="absolute inset-0 bg-gradient-to-br from-fluent-blue-500/18 via-transparent to-dark-bg-secondary/85" aria-hidden="true" />
        <div className="relative flex flex-col gap-5 lg:flex-row lg:items-start lg:justify-between">
          <div className="max-w-sm space-y-3">
            <h3 id="experience-heading" className="text-xl font-semibold text-dark-text-primary">Highlights</h3>
            <p className="text-sm text-dark-text-tertiary">
              Surface the most impactful moments from recent operations to brief leadership quickly.
            </p>
          </div>
          <div className="grid gap-3 lg:w-1/2">
            {activity.length === 0 ? (
              <p className="text-sm text-dark-text-tertiary">
                Activity timeline will populate as workflows complete. Highlights will appear here once available.
              </p>
            ) : (
              activity.map((item) => (
                <div
                  key={item.id}
                  className={`rounded-2xl border bg-gradient-to-br ${statusAccent[item.status]} px-4 py-4 text-sm text-dark-text-secondary shadow-[0_14px_36px_rgba(15,23,42,0.32)] transition-all duration-200 hover:-translate-y-0.5 hover:shadow-[0_18px_44px_rgba(56,189,248,0.25)]`}
                >
                  <div className="flex flex-wrap items-center justify-between gap-3">
                    <span className="inline-flex items-center gap-2 rounded-full border border-white/20 bg-dark-bg-primary/60 px-3 py-1 text-[0.6rem] font-semibold uppercase tracking-[0.26em] text-dark-text-secondary">
                      {item.status.toUpperCase()}
                    </span>
                    <span className="text-xs text-dark-text-tertiary">{item.time}</span>
                  </div>
                  <p className="mt-3 text-base font-semibold text-dark-text-primary">{item.title}</p>
                  <p className="mt-1 text-sm text-dark-text-secondary">{item.description}</p>
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </section>
  );
}
