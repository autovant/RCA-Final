import React from 'react';

interface StatCardProps {
  title: string;
  value: string | number;
  icon: React.ReactNode;
  trend?: {
    value: number;
    isPositive: boolean;
  };
  color?: 'blue' | 'green' | 'yellow' | 'red' | 'cyan';
}

export const StatCard: React.FC<StatCardProps> = ({
  title,
  value,
  icon,
  trend,
  color = 'blue'
}) => {
  const gradientClasses = {
    blue: 'from-fluent-blue-500/25 via-transparent to-fluent-blue-500/5',
    green: 'from-fluent-success/25 via-transparent to-fluent-success/5',
    yellow: 'from-fluent-warning/25 via-transparent to-fluent-warning/5',
    red: 'from-fluent-error/25 via-transparent to-fluent-error/5',
    cyan: 'from-fluent-info/25 via-transparent to-fluent-info/5',
  };

  const borderClasses = {
    blue: "border-fluent-blue-500/40",
    green: "border-fluent-success/40",
    yellow: "border-fluent-warning/40",
    red: "border-fluent-error/40",
    cyan: "border-fluent-info/40",
  };

  const hoverBorderClasses = {
    blue: "hover:border-fluent-blue-500/45",
    green: "hover:border-fluent-success/45",
    yellow: "hover:border-fluent-warning/45",
    red: "hover:border-fluent-error/45",
    cyan: "hover:border-fluent-info/45",
  };

  const iconColorClasses = {
    blue: 'bg-fluent-blue-500/20 text-fluent-blue-200 border-fluent-blue-500/40',
    green: 'bg-fluent-success/20 text-green-200 border-fluent-success/40',
    yellow: 'bg-fluent-warning/20 text-yellow-200 border-fluent-warning/40',
    red: 'bg-fluent-error/20 text-red-200 border-fluent-error/40',
    cyan: 'bg-fluent-info/20 text-cyan-200 border-fluent-info/40',
  };

  return (
    <article
      className={`relative overflow-hidden rounded-2xl border border-dark-border/35 bg-dark-bg-tertiary/60 p-6 shadow-[0_16px_38px_rgba(15,23,42,0.32)] backdrop-blur-xl transition-all duration-200 hover:-translate-y-1 hover:shadow-[0_20px_44px_rgba(56,189,248,0.25)] ${borderClasses[color]} ${hoverBorderClasses[color]}`}
    >
      <div className={`absolute inset-0 bg-gradient-to-br ${gradientClasses[color]} opacity-90`} aria-hidden="true" />
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_top,rgba(255,255,255,0.06),transparent_55%)]" aria-hidden="true" />
      <div className="relative flex items-start justify-between gap-4">
        <div className="flex-1">
          <p className="text-[0.6rem] font-semibold uppercase tracking-[0.24em] text-dark-text-tertiary">{title}</p>
          <p className="mt-3 text-3xl font-semibold text-dark-text-primary">{value}</p>

          {trend && (
            <div
              className={`mt-3 inline-flex items-center gap-1 rounded-full border border-dark-border/40 bg-dark-bg-secondary/60 px-3 py-1 text-[0.6rem] font-semibold uppercase tracking-[0.22em] ${
                trend.isPositive ? "text-fluent-success" : "text-fluent-error"
              }`}
            >
              <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                {trend.isPositive ? (
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 10l7-7 7 7" />
                ) : (
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 14l-7 7-7-7" />
                )}
              </svg>
              {Math.abs(trend.value)}%
            </div>
          )}
        </div>

        <div className={`relative flex h-12 w-12 items-center justify-center rounded-xl border ${iconColorClasses[color]}`}>
          {icon}
        </div>
      </div>
    </article>
  );
};

interface ActivityItemProps {
  title: string;
  description: string;
  time: string;
  status: 'success' | 'warning' | 'error' | 'info';
  icon?: React.ReactNode;
}

export const ActivityItem: React.FC<ActivityItemProps> = ({
  title,
  description,
  time,
  status,
  icon
}) => {
  const statusColors = {
    success: 'bg-fluent-success',
    warning: 'bg-fluent-warning',
    error: 'bg-fluent-error',
    info: 'bg-fluent-info',
  };

  return (
    <div className="flex gap-4 p-4 hover:bg-dark-bg-elevated/50 rounded-lg transition-colors group">
      <div className="flex-shrink-0">
        <div className={`w-10 h-10 rounded-lg ${statusColors[status]} flex items-center justify-center text-white`}>
          {icon || (
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
            </svg>
          )}
        </div>
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium text-dark-text-primary group-hover:text-fluent-blue-400 transition-colors">
          {title}
        </p>
        <p className="text-sm text-dark-text-tertiary mt-1">
          {description}
        </p>
        <p className="text-xs text-dark-text-tertiary mt-2">
          {time}
        </p>
      </div>
    </div>
  );
};
