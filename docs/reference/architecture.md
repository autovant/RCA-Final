# Architecture Overview

```
┌───────────────┐    ┌───────────────┐    ┌──────────────┐
│ File Uploads  │    │ Watcher Events│    │ API Clients  │
└──────┬────────┘    └──────┬────────┘    └──────┬───────┘
       │                     │                   │
       ▼                     ▼                   ▼
┌────────────────────────────────────────────────────────┐
│                  FastAPI Application                    │
│  - Auth / Files / Jobs / Summary / Tickets / Watcher    │
│  - SSE streams for job + watcher events                 │
└────────┬───────────────────────────────┬───────────────┘
         │                               │
         │ enqueue jobs                  │ metrics/logging
         ▼                               ▼
┌───────────────────────┐        ┌────────────────────┐
│ Async Worker (Celery) │        │ Observability Stack │
│ - Chunk + embed files │        │ - Prometheus        │
│ - PII redaction       │        │ - Structured logs   │
│ - LLM orchestration   │        └────────────────────┘
│ - Ticket callbacks    │
└─────────┬─────────────┘
          │      ┌────────────────────┐
          │      │ LLM Providers      │
          │      │ (Ollama/OpenAI/etc)│
          │      └────────────────────┘
          ▼
┌──────────────────────────────────────────────┐
│ PostgreSQL (pgvector) + Optional Redis       │
│  - jobs / files / documents / conversation   │
│  - watcher config & events                   │
│  - ticket metadata                           │
└──────────────────────────────────────────────┘
```

## Key Components

- **apps/api/** – FastAPI project exposing REST and SSE endpoints, authentication, and ticket APIs.
- **apps/worker/** – Background worker handling ingestion, embeddings, LLM orchestration, and report generation.
- **core/** – Shared domain logic: configuration, database models, job processor, privacy utilities, LLM providers, and ticket services.
- **ui/** – Next.js frontend that renders the investigation workflow, exposes the live progress checklist, and handles artefact uploads.
- **deploy/** – Dockerfiles, compose stacks, and monitoring configuration for production.
- **scripts/** – Helper utilities for linting, tests, and operational automation.

## Data Flow Summary

1. Files or watcher events create job records via the API.
2. Jobs enqueue tasks processed by the worker, emitting `analysis-progress` events throughout the pipeline.
3. Processed artefacts, embeddings, and generated reports persist in Postgres (with pgvector) and optional Redis caches.
4. SSE streams broadcast progress to the UI, while Prometheus/Grafana capture operational metrics.
5. Optional ticket adapters push structured outputs into ServiceNow, Jira, or future platforms.
