# Job Processor Operations Guide

The job processor coordinates ingestion for RCA analyses. This guide documents the execution flow, fingerprint indexing behaviour, operational telemetry, and troubleshooting steps introduced with the Unified Ingestion Enhancements workstream.

## Pipeline Overview

- `JobProcessor.process_rca_analysis` drives the full ingestion pipeline: classification → redaction → chunking → embedding → storage → correlation → LLM report assembly.
- `JobProcessor.process_log_analysis` runs a reduced version of the pipeline for lightweight log summarisation while reusing the same telemetry hooks.
- Progress is surfaced through `analysis-progress` job events, and pipeline stage telemetry is persisted via `UploadTelemetryEvent` records when feature flags enable enhanced metrics.

## Incident Fingerprint Indexing

Completed RCA jobs now create or refresh a fingerprint in the `incident_fingerprints` table so that related incidents are immediately discoverable.

### When indexing runs

- `_index_incident_fingerprint` executes at the tail of the RCA pipeline after LLM summarisation completes.
- Indexing is skipped when the job manifest lacks a resolvable tenant identifier; a debug log is emitted in that case.
- Summary text is trimmed to 4096 characters and a placeholder summary is generated when no LLM output is available.

### Visibility scope and relevance thresholds

- `JobProcessor._resolve_visibility_scope` resolves the fingerprint scope using job manifest hints (`fingerprint_visibility_scope`, `related_incidents_scope`) and falls back to the `RELATED_INCIDENTS_DEFAULT_SCOPE` configuration.
- Relevance thresholds default to `RELATED_INCIDENTS_MIN_RELEVANCE`, but can be overridden per job via `fingerprint_min_relevance` or `related_incidents_min_relevance` manifest keys.

### Guardrails and degraded states

- Embedding failures immediately transition the fingerprint to `DEGRADED` and attach canonical safeguard notes under the `fingerprint` key in `IncidentFingerprint.safeguard_notes`.
- Missing summaries result in placeholder text, an empty embedding vector, and a `MISSING` status with explanatory safeguard notes.
- Safeguard notes surface over the new admin endpoint `GET /api/v1/jobs/{job_id}/fingerprint`, enabling operators to debug degraded fingerprints quickly.

### Coordination with telemetry

- The worker publishes `fingerprint-status` events (and associated Prometheus metrics) using the DTO returned by `_index_incident_fingerprint`.
- Metrics collectors increment `rca_fingerprint_status_total` and record safeguard note counts via `rca_fingerprint_safeguard_notes`, allowing dashboards to highlight degraded or missing fingerprints.

## Operational Checks

1. **Verify fingerprint metadata** – Call `GET /api/v1/jobs/{job_id}/fingerprint` to inspect status, visibility scope, and guardrail notes.
2. **Review worker telemetry** – Monitor `fingerprint-status` events and Prometheus metrics for spikes in degraded/missing states.
3. **Validate embedding providers** – If many jobs degrade, confirm the embedding provider health (network connectivity, API limits).
4. **Inspect job summaries** – Placeholder summaries indicate upstream LLM analysis did not produce output; re-run the job after addressing LLM issues.

## Troubleshooting Quick Reference

| Symptom | Likely Cause | Actions |
| --- | --- | --- |
| Fingerprint status is `missing` with safeguard notes referencing summaries | LLM analysis produced no summary text | Re-run analysis after confirming LLM provider responses; ensure manifest overrides are not suppressing summaries |
| Fingerprint status is `degraded` and metrics show embedding errors | Embedding provider failed or returned empty vector | Check embedding provider logs/quotas; re-run job once the provider is healthy |
| Fingerprint missing entirely | Tenant ID absent from job manifest | Ensure ingestion sources populate `tenant_id` in the manifest before submitting jobs |

## Related Files

- `core/jobs/processor.py` – orchestrates the ingestion pipeline and fingerprint indexing logic.
- `core/jobs/fingerprint_service.py` – powers similarity search, guardrail notes, and degraded fingerprint handling.
- `core/jobs/models.py` – shared DTOs and enums used across the processor, worker, and API.
- `apps/worker/events.py` – emits fingerprint telemetry events consumed by monitoring systems.
- `apps/api/routers/jobs.py` – exposes the fingerprint metadata endpoint for operator debugging.
- `core/metrics/collectors.py` – captures fingerprint status metrics for dashboards.
