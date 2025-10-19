# Platform Features

The RCA Engine provides an end-to-end workflow for automated incident investigations. Highlights below mirror the latest backend and UI capabilities.

## Investigation Pipeline

- **Conversational RCA** – FastAPI orchestrates redaction, chunking, embeddings (pgvector), retrieval, and multi-turn LLM reasoning with job-scoped context.
- **Friendly progress signals** – Jobs emit structured `analysis-progress` events consumed by the UI checklist and activity log.
- **Structured deliverables** – Each run outputs Markdown, HTML, and JSON reports with severity, recommended actions, and ticket metadata.

## LLM Integrations

- **Provider abstraction** – Switch between GitHub Copilot, OpenAI, AWS Bedrock, Anthropic, LM Studio, or vLLM via configuration.
- **Per-job overrides** – Select models per investigation, store conversation history, and support dry-run ticketing.

## Privacy & Compliance

- **🔒 Enterprise PII Protection** – Military-grade multi-layer redaction system with 30+ pattern types (AWS/Azure/GCP credentials, JWT tokens, passwords, database connections, private keys, SSH keys, network identifiers). Multi-pass scanning (up to 3 passes) catches nested patterns. Strict validation mode with 6 security checks ensures zero data leakage to LLMs. Real-time visibility with security badges and live redaction stats in the UI. Enabled by default.
- **Audit trail** – Complete redaction audit logs, job events, and conversation transcripts persisted for compliance (GDPR, PCI DSS, HIPAA, SOC 2).

## UI & Streaming

- **Next.js dashboard** – Upload artefacts, configure watchers, monitor live analysis, and review results.
- **SSE streams** – Unified `/api/sse/jobs/{id}` channel for live progress with heartbeat timestamps.

## ITSM Automation

- **Ticket services** – Modular integrations for ServiceNow, Jira, and dry-run preview flows.
- **Template library** – JSON-configurable templates in `config/itsm_config.json` with Grafana dashboards for operational insight.

## Observability

- **Prometheus metrics** – Exported at `/metrics`; monitoring stack includes optional Prometheus + Grafana profile.
- **Structured logging** – JSON logs for backend and worker, ready for aggregation.

## Extensibility

- **Providers** – Add new LLM providers by implementing `BaseLLMProvider` in `core/llm/providers/`.
- **Watcher framework** – File watcher events feed into the job processor and UI for near real-time ingestion dashboards.
- **Ticket adapters** – Extend `core/tickets/service.py` to support additional ITSM platforms or webhooks.

See [Architecture Overview](architecture.md) for a diagram and component layout.
