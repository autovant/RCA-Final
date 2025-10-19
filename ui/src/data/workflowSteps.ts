import { WorkflowStep } from "@/components/dashboard/WorkflowShowcase";

export const WORKFLOW_STEPS: WorkflowStep[] = [
  {
    id: "capture",
    title: "Capture & classify",
    duration: "~60 seconds",
    description:
      "Pull structured context from incidents, logs, and observability feeds. RCA Engine maps signal-to-noise across every surface you connect.",
    highlight: "Inbound connectors: Opsgenie, PagerDuty, Prometheus, Splunk",
  },
  {
    id: "synthesize",
    title: "Synthesize hypotheses",
    duration: "~2 minutes",
    description:
      "AI copilots correlate failure patterns with recent changes, anomaly spikes, and known issues. Engineers can approve, reject, or enrich suggestions inline.",
    highlight: "Confidence scoring + human-in-the-loop",
  },
  {
    id: "coordinate",
    title: "Coordinate the response",
    duration: "~3 minutes",
    description:
      "Push curated action plans into Jira or ServiceNow without retyping. Dual-mode keeps business and engineering stakeholders synchronized.",
    highlight: "Automated ticket & comms orchestration",
  },
  {
    id: "communicate",
    title: "Communicate the why",
    duration: "~90 seconds",
    description:
      "Auto-generate executive-ready summaries and customer-facing updates. Export clean post-incident decks or embed into existing runbooks instantly.",
    highlight: "AI-authored narratives + redlining",
  },
];
