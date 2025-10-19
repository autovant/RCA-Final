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
  success: "bg-gradient-to-r from-fluent-success/25 via-transparent to-fluent-success/5 text-green-100 border border-fluent-success/30",
  warning: "bg-gradient-to-r from-fluent-warning/25 via-transparent to-fluent-warning/5 text-yellow-100 border border-fluent-warning/30",
  error: "bg-gradient-to-r from-fluent-error/25 via-transparent to-fluent-error/5 text-red-100 border border-fluent-error/30",
  info: "bg-gradient-to-r from-fluent-info/25 via-transparent to-fluent-info/5 text-cyan-100 border border-fluent-info/30",
};

export function ExperienceShowcase({ activity }: ExperienceShowcaseProps) {
  return (
    <section aria-labelledby="experience-heading" className="space-y-5">
      <div className="relative overflow-hidden rounded-3xl border border-dark-border/50 bg-dark-bg-secondary/75 p-6 shadow-fluent backdrop-blur-2xl">
        <div className="absolute inset-0 bg-gradient-to-br from-fluent-blue-500/15 via-transparent to-dark-bg-secondary/80" aria-hidden="true" />
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
                  className={`${statusAccent[item.status]} rounded-2xl px-4 py-4 text-sm text-dark-text-secondary transition-all duration-200 hover:-translate-y-0.5 hover:shadow-fluent-lg`}
                >
                  <div className="flex flex-wrap items-center justify-between gap-3">
                    <span className="inline-flex items-center gap-2 rounded-full bg-dark-bg-primary/60 px-3 py-1 text-xs font-semibold uppercase tracking-[0.24em] text-dark-text-secondary">
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
