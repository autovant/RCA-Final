# Implementation Plan: File Upload & RAG Pipeline Pragmatic Enhancements

**Branch**: `001-act-as-the` | **Date**: 2025-10-14 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/001-act-as-the/spec.md`

**Note**: This plan scopes backend and worker changes for telemetry, compressed ingestion, embedding cache, chunk quality, and hybrid retrieval guarded by feature flags.

## Summary

Implement staged enhancements to the RCA file upload and retrieval pipeline: first harden observability with Prometheus instrumentation, encoding smoke tests, and upload sampling; next add `.gz`/`.zip` ingestion plus an opt-in Postgres-backed embedding cache with documented migrations and eviction flows; finally roll out token-aware chunking, stack-trace preservation, chunk quality scoring, and hybrid BM25 + vector retrieval with citations and latency guardrails.

## Technical Context

**Language/Version**: Python 3.11 (repository standard per `setup.py`)  
**Primary Dependencies**: FastAPI, SQLAlchemy, pgvector, Redis, Prometheus client, httpx, python-magic, chardet, planned additions `tiktoken` (token awareness) and PostgreSQL full-text search extensions  
**Storage**: PostgreSQL (primary data store + new `embedding_cache` table + `tsvector` indexes), Redis (feature flag cache, async eviction coordination), Object storage on disk/S3 abstraction unchanged  
**Testing**: pytest with pytest-asyncio, smoke tests executed via existing CLI harness in `core/files/tests`, Prometheus metric assertions via test client  
**Target Platform**: Containerized Linux services (FastAPI API + async worker) deployed to existing RCA infrastructure  
**Project Type**: Multi-service backend (API + worker pipelines)  
**Performance Goals**: Maintain ≤4 minute ingest for ≤20 MB inputs, keep hybrid retrieval ≤1.5× current P95, sustain ≥40% embedding cache hit rate on pilot tenants, emit telemetry within 30 seconds  
**Constraints**: All new features behind tenant-scoped feature flags, asynchronous eviction must not block ingest threads, hybrid retrieval auto-disables if latency breaches threshold, ASCII-only code updates per spec  
**Scale/Scope**: Multi-tenant RCA platform handling hundreds of concurrent uploads/day, top 10 file types tracked for regression packs, LLM routes across GPT-4o and Anthropic Sonnet

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **I. Resilience by Design**: All new external calls (token counting, decompression utilities) will leverage existing retry-capable clients or run locally; hybrid retrieval continues to use Postgres-backed services with configurable timeouts—no gate violation.  
- **II. Schema-First Validation**: ITSM payload rules unaffected; new database interactions include explicit validation in domain services prior to persistence.  
- **III. Template-Driven Ticket Creation**: No ticket changes introduced; existing template workflows remain intact.  
- **IV. Metrics-First Integration**: Feature expands Prometheus metrics which aligns with the principle—ensure `/metrics` exposes new series.  
- **V. Test Coverage for Integration Paths**: Plan includes unit + smoke tests for instrumentation, decompression, cache, and retrieval toggles.  
- **Enterprise Integration Standards**: Timeout, error propagation, credential management untouched; ensure any LLM or storage client reuse existing configuration.  
✅ **Gate Result**: Proceed — no constitution blockers identified.

## Project Structure

### Documentation (this feature)

```
specs/[###-feature]/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)
<!--
  ACTION REQUIRED: Replace the placeholder tree below with the concrete layout
  for this feature. Delete unused options and expand the chosen structure with
  real paths (e.g., apps/admin, packages/something). The delivered plan must
  not include Option labels.
-->

```
apps/
├── api/
│   ├── routers/
│   ├── services/
│   └── telemetry/
├── worker/
│   ├── pipelines/
│   └── tasks/

core/
├── files/
├── ingestion/
├── retrieval/
├── metrics/
├── cache/
└── logging/

deploy/ops/
├── migrations/
└── runbooks/

tests/
├── api/
├── worker/
└── smoke/
```

**Structure Decision**: Enhance existing backend + worker layout. New code lives in `core/metrics`, `core/cache/embedding_cache_service.py`, `core/retrieval/hybrid.py`, with API control surfaces in `apps/api/routers/admin_feature_flags.py`. Supporting docs and migrations stored under `deploy/ops/` and tenant smoke suites under `tests/smoke/`.

## Phase 0 – Baseline Hardening

1. **Prometheus instrumentation**: Wrap ingest, embed, cache, storage stages with `MetricsCollector` helpers emitting counters/histograms; add partial upload warnings metric and persist telemetry via the canonical SQLAlchemy models in `core/db/models.py` (keeping `core/files/telemetry.py` as helper wrappers only). Update `/metrics` integration tests.
2. **Smoke tests**: Extend smoke suite with UTF-8, UTF-16LE/BE, malformed fixtures; add GitHub workflow job executing new smoke command.
3. **Upload snapshot script**: Implement CLI under `scripts/pipeline/` pulling top 10 file types via SQL; document usage in `quickstart.md` and add regression artifact update instructions.
4. **Docs/runbooks**: Publish telemetry dashboard checklist in `docs/telemetry/overview.md` and rollback procedures in `deploy/ops/telemetry.md`.
5. **Long-term retention**: Configure Prometheus remote-write to the managed Thanos bucket, verify downsampled rollups are queryable for 12 months, and document alerting for remote-write failures.

## Phase 1 – Compressed Ingestion & Embedding Cache

1. **Archive extraction**: Enhance `FileService.ingest_upload` to detect `.gz`/`.zip`, extract via streaming temp files, enforce 100 MB post-extraction + 30-second timeouts, introduce an ingest watchdog that aborts before the four-minute SLA would be exceeded, and surface partial-status telemetry when unsupported entries encountered.
2. **Embedding cache**: Create `core/cache/embedding_cache_service.py` backed by new Postgres table and Alembic migration; integrate with worker pipeline to read/write cache prior to embedding calls, verify scrub metadata before caching, and encrypt payloads with keys from managed secrets.
3. **Eviction job**: Add async task in worker pipeline triggered once hit rate ≥30% per tenant, obtaining advisory locks to avoid concurrent runs and recording eviction metrics.
4. **Feature toggles & docs**: Expose admin API endpoints defined in contracts, wire to existing feature flag store, and write operator guide in `deploy/ops/embedding-cache.md`.
5. **Testing**: Unit tests for archive parsing, cache hits/misses, asynchronous eviction scheduling; contract tests for admin endpoints; update smoke tests to cover `.zip` uploads.

## Phase 2 – Chunk Quality & Hybrid Retrieval

1. **Token-aware chunking**: Introduce `core/files/chunking_config.py` storing per-model budgets, integrate `tiktoken` and Anthropic tokenizer wrappers, and update chunk generator pipeline.
2. **Quality scoring**: Implement stack trace preservation heuristics, compute `chunk_quality_score`, persist via `ChunkQualityRecord`, and fail ingestion when uploads fall below threshold.
3. **Hybrid retrieval**: Build `core/retrieval/hybrid.py` merging pgvector similarity with Postgres BM25 ranking; add guard to auto-disable via feature flag when latency breaches 1.5× baseline and ensure fallback to vector-only on BM25 failure.
4. **Citations**: Extend API response schema to include `chunk_id`, `session_id`, and `line_range`; add preview trimming to manage prompt budgets and update UI contract docs if necessary.
5. **Monitoring & alerts**: Emit `hybrid_retrieval_auto_disable_total`, expose BM25 staleness gauges, log structured audit entries, and update Grafana dashboards.
6. **Testing**: Unit tests for chunk sizing, quality scoring, retrieval fusion, and auto-disable logic; integration tests verifying citations present and latency metrics accurate.

## Complexity Tracking

*Fill ONLY if Constitution Check has violations that must be justified*

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| *(none)* | *(n/a)* | *(n/a)* |

## Constitution Check (Post-Design Review)

- Revalidated Principles I–V after design artifacts: archive ingestion, embedding cache, and hybrid retrieval remain internal services with bounded retries; no external ITSM integrations introduced.
- Metrics-first requirements are strengthened with new Prometheus series and audit logs.
- Testing commitments cover retry, validation, and template pathways indirectly affected by pipeline changes.
- Enterprise integration standards (timeouts, credential handling) continue to rely on existing configuration modules without modification.
✅ **Result**: Still compliant — proceed to Phase 2 task decomposition next.
