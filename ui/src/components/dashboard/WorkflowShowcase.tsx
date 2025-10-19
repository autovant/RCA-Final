"use client";

import { Button, Card } from "@/components/ui";

export type WorkflowStep = {
  id: string;
  title: string;
  description: string;
  duration?: string;
  highlight?: string;
};

type WorkflowShowcaseProps = {
  steps: WorkflowStep[];
  onStart?: () => void;
};

export function WorkflowShowcase({ steps, onStart }: WorkflowShowcaseProps) {
  return (
    <section aria-labelledby="workflow-heading" className="space-y-6">
      <div className="flex flex-col gap-5 lg:flex-row lg:items-end lg:justify-between">
        <div className="space-y-2 max-w-2xl">
          <h2 id="workflow-heading" className="section-title text-2xl">
            From signal to executive-ready insight in four orchestrated moves
          </h2>
          <p className="text-sm sm:text-base text-dark-text-tertiary">
            RCA Engine keeps humans in the loop while automating the repetitive lift. Each orbit completes in minutes, not hours.
          </p>
        </div>
        {onStart && (
          <Button size="lg" onClick={onStart} className="self-start lg:self-auto">
            Start a Guided Run
          </Button>
        )}
      </div>

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        {steps.map((step, index) => (
          <Card key={step.id} className="workflow-step">
            <span className="workflow-index" aria-hidden="true">
              {String(index + 1).padStart(2, "0")}
            </span>
            <div className="space-y-3">
              <div>
                <h3 className="text-base font-semibold text-dark-text-primary">
                  {step.title}
                </h3>
                {step.duration && (
                  <p className="text-xs text-fluent-blue-300 uppercase tracking-wide mt-1">
                    {step.duration}
                  </p>
                )}
              </div>
              <p className="text-sm text-dark-text-secondary leading-relaxed">
                {step.description}
              </p>
              {step.highlight && (
                <p className="text-xs font-medium text-dark-text-tertiary bg-dark-bg-tertiary/60 border border-dark-border/60 inline-flex px-3 py-1 rounded-full">
                  {step.highlight}
                </p>
              )}
            </div>
          </Card>
        ))}
      </div>
    </section>
  );
}
