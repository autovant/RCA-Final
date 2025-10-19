# Feature Specification: File Upload & RAG Pipeline Pragmatic Enhancements

**Feature Branch**: `001-act-as-the`  
**Created**: 2025-10-13  
**Status**: Draft  
**Input**: User description: "Act as the lead engineer implementing the 'File Upload & RAG Pipeline - Pragmatic Enhancement Plan' in F.md. Apply it in three phases: (1) add telemetry instrumentation (Prometheus metrics for ingest/embed/cache/storage) plus smoke tests for UTF-8/UTF-16/malformed inputs and a script that snapshots top 10 observed upload types; (2) extend ingestion to handle .gz/.zip by reusing existing text pipeline post-extraction, introduce an opt-in embedding cache (new embedding_cache table with migrations, async eviction after 30% hit rate) with documentation/rollback steps; (3) wire chunking to use configurable token-aware sizing per active LLM, add stack-trace preservation heuristics, enforce chunk_quality_score validation, and surface hybrid BM25+vector retrieval with optional citation metadata while monitoring p95 latency. Ensure feature flags guard each capability, add tests and docs under docs or deploy/ops/ as appropriate, and keep changes ASCII-only. Return a summary of files touched and any verification steps (e.g., tests, lint) needed."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Observable ingestion guardrails (Priority: P1)

Site reliability engineers need immediate visibility into ingestion, embedding, caching, and storage steps so they can catch regressions before they breach the four-minute SLA for uploads up to 20 MB.

**Why this priority**: Without baseline instrumentation and smoke coverage, later phases cannot be evaluated safely, so this is the enabling slice for the rest of the roadmap.

**Independent Test**: Enable the telemetry feature flag in staging, trigger controlled uploads across supported encodings, and confirm dashboards and smoke tests report status without enabling other feature flags.

**Acceptance Scenarios**:

1. **Given** telemetry is enabled for a tenant, **When** an analyst uploads a 20 MB UTF-8 log file, **Then** Prometheus exposes counts and latency histograms for each pipeline stage within 30 seconds of completion.
2. **Given** smoke tests run in CI, **When** a malformed file that previously caused silent failures is processed, **Then** the smoke suite fails with a clear diagnostic before release approval.

---

### User Story 2 - Compressed ingestion pilot with caching (Priority: P2)

Pilot tenants want to upload .gz and .zip archives and benefit from an opt-in embedding cache that reduces redundant embedding costs while protecting reliability.

**Why this priority**: Supporting compressed uploads and caching delivers immediate tenant value and measurable cost savings once instrumentation proves stability.

**Independent Test**: Toggle the compressed-upload and embedding-cache flags for a staging tenant, run archive uploads that re-use identical chunks, and verify cache hit tracking, rollback steps, and eviction behavior without enabling chunk-quality changes.

**Acceptance Scenarios**:

1. **Given** the compressed-upload flag is active, **When** a .zip file containing mixed supported text files is uploaded, **Then** each file is extracted, processed through the existing text pipeline, and completes within the four-minute SLA.
2. **Given** the embedding cache is enabled for a tenant, **When** identical text appears in successive uploads, **Then** at least 30% of embedding lookups resolve via the cache during pilot testing and eviction runs asynchronously without blocking ingestion.

---

### User Story 3 - Quality-aware retrieval rollout (Priority: P3)

RCA analysts need higher-quality chunks and trustworthy retrieval with citations so they can resolve incidents faster without losing confidence in automated responses.

**Why this priority**: Chunk quality improvements and hybrid retrieval build on earlier observability and caching investments to drive the long-term user-facing outcome of faster, more accurate RCA responses.

**Independent Test**: Enable the quality-and-retrieval flag for a pilot tenant, configure token-aware chunking for two LLM providers, run regression searches, and confirm chunk quality metrics and citation metadata meet thresholds with acceptable latency.

**Acceptance Scenarios**:

1. **Given** token-aware chunking is enabled, **When** an analyst routes an incident summary through the pipeline, **Then** chunks respect the configured token budgets per active model and maintain stack traces with a printable-character ratio of at least 90%.
2. **Given** hybrid retrieval is active, **When** an analyst queries the system, **Then** responses reference chunk IDs and line ranges while keeping query latency within 1.5 times the current P95 baseline, otherwise the feature flag disables hybrid retrieval automatically.

---

### Edge Cases

- When a compressed archive mixes encrypted or unsupported files with supported text, the ingest flow processes supported members, marks the upload as partial, and emits warnings plus telemetry for skipped items.
- When a `.zip` archive contains multiple candidate log files, the system extracts the first supported file, records the choice, and emits a warning about remaining members.
- Corrupted or malicious compressed files fail extraction gracefully with descriptive errors while protecting the pipeline from crashes.
- Upload telemetry outages (e.g., Prometheus endpoint unavailable) must not block ingest; the system queues metrics for retry and flags observability gaps.
- If Prometheus remote-write to Thanos becomes unavailable, the system buffers rollups locally, alerts operators, and documents the gap while preserving the 30-day Prometheus window.
- Cache warm-up periods with prolonged hit rates below 30% trigger monitoring alerts but do not activate eviction jobs until thresholds are met.
- If ingest processing time drops below a 30-second SLA buffer, a watchdog cancels remaining archive work, marks the upload partial, and emits telemetry for the proactive abort.
- Logs lacking clear line boundaries (e.g., minified JSON) fall back to fixed-character chunking with a warning for analyst awareness.
- Missing model-specific chunk budgets default to safe baseline sizing while logging the need for configuration.
- If chunk_quality_score falls below the acceptance threshold for an entire upload batch, the system marks the upload partial, suppresses low-quality chunks from retrieval, and alerts operators.
- If the BM25 index is unavailable or stale, hybrid retrieval falls back to vector-only search and surfaces a degraded-state flag to analysts.
- When citation metadata would exceed allowed prompt size, the response trims citations to the top contributors and notes that additional sources are available on demand.

## Requirements *(mandatory)*

### Functional Requirements

#### Phase 0 – Baseline Hardening

- **FR-001**: The system MUST emit Prometheus counters and latency histograms for ingest, chunk, embed, cache, and storage stages per upload, scoped by tenant and feature flag state.
- **FR-002**: Stage metrics MUST include labels for platform (e.g., blue_prism, uipath, appian), file_type (.log, .txt, .csv), size_category (tiny through xlarge), and status (success, partial, failure).
- **FR-003**: Metric retention MUST preserve 30 days of high-resolution data in Prometheus and stream aggregated rollups to the managed Thanos bucket for at least 12 months to support operational analysis and compliance reviews.
- **FR-004**: The platform MUST provide automated smoke tests that validate UTF-8, UTF-16LE, UTF-16BE, and malformed file handling across the ingest-to-storage flow before deployment approvals.
- **FR-005**: The team MUST deliver a repeatable script that snapshots the top 10 observed upload file types and size distributions using recent production-like telemetry for validation runs.
- **FR-006**: The pipeline MUST continue to meet the four-minute SLA for uploads up to 20 MB even when archives expand individual files by monitoring cumulative processing time and declining or aborting work before the limit would be breached (e.g., cancel with at least a 30-second safety margin).

#### Phase 1 – Format & Cost Quick Wins

- **FR-007**: When the compressed-upload flag is enabled, the ingest service MUST accept `.gz` files, extract supported text contents, and route them through the existing text pipeline without altering downstream contract behaviors.
- **FR-008**: The ingest service MUST accept `.zip` archives, extract the first supported log or text file, and document the selection for observability.
- **FR-009**: The system MUST emit operator-visible warnings when a `.zip` archive contains multiple supported files, indicating that only the first was processed.
- **FR-010**: Compressed file extraction MUST enforce a maximum cumulative extracted size of 100 MB and a 30-second processing timeout to mitigate resource exhaustion attacks.
- **FR-011**: Extractions that exceed the size or timeout limits MUST fail gracefully with clear error messaging and structured telemetry describing the violation.
- **FR-012**: If an archive includes encrypted, unsupported, or malformed members, the system MUST continue processing supported files, mark the upload as partial, and surface warnings plus telemetry about skipped content.
- **FR-013**: Corrupted archive inputs MUST not crash the pipeline; the ingest service MUST return a retriable failure response and capture diagnostic details for operators.
- **FR-014**: The embedding cache feature MUST remain opt-in, backed by a new `embedding_cache` data store defined with forward and rollback migrations stored under `deploy/ops/`.
- **FR-015**: Prior to caching, the system MUST confirm that upstream PII scrubbing metadata is present; uploads lacking confirmation MUST be rejected or routed for manual review.
- **FR-016**: Cached embeddings MUST be encrypted at rest using AES-256 (or higher) with tenant isolation respected.
- **FR-017**: Encryption keys for cached embeddings MUST be stored outside the primary database (e.g., environment variables or managed key service) and rotated per security policy.
- **FR-018**: The pipeline MUST check the embedding cache by tenant, model, and SHA-256 content hash before calling any external embedding API.
- **FR-019**: Cache hits MUST increment hit counters, update last-accessed timestamps, and record per-tenant hit rate metrics.
- **FR-020**: The system MUST expose cache hit, miss, and eviction metrics (e.g., `embedding_cache_hits_total`, `embedding_cache_requests_total`) labeled by tenant and model.
- **FR-021**: Embedding cache participation MUST be controlled via tenant-scoped feature flags with secure defaults (disabled in production until approved).
- **FR-022**: Once a tenant sustains a cache hit rate of 30% or higher, the system MUST schedule an asynchronous eviction job that never blocks ingest threads.
- **FR-023**: Eviction jobs MUST obtain a database advisory lock to prevent concurrent execution across workers; only the lock holder runs the job.
- **FR-024**: When the advisory lock cannot be acquired, the eviction job MUST exit gracefully with an informational log indicating another worker is in progress.
- **FR-025**: Eviction jobs MUST remove cache entries meeting policy (e.g., hit_count = 0 and older than 90 days) and emit audit metrics for removed counts.
- **FR-026**: All schema changes and rollbacks for compressed ingestion and caching MUST be documented with tested scripts in `deploy/ops/migrations/`.
- **FR-027**: Operator runbooks for enabling, monitoring, and rolling back compressed ingestion and caching MUST be published under `deploy/ops/docs/` before rollout.

#### Phase 2 – Chunk Quality Improvements

- **FR-028**: Administrators MUST be able to configure token-aware chunk budgets per active LLM (e.g., GPT-4o, Claude Sonnet, GPT-5) with safe defaults applied when overrides are absent.
- **FR-029**: Token-aware chunking MUST be gated by a tenant feature flag that defaults to disabled for production tenants.
- **FR-030**: The chunking logic MUST detect multi-line stack traces using patterns such as `^\s+at\s+`, `^\s+File\s+"`, and `^\s+in\s+<module>`.
- **FR-031**: Detected stack traces MUST remain within a single chunk to preserve diagnostic context.
- **FR-032**: The system MUST calculate a `printable_ratio` for each chunk representing printable characters over total characters.
- **FR-033**: Chunks with a printable ratio below 0.90 MUST be rejected, logged, and excluded from retrieval.
- **FR-034**: Empty chunks (content stripped length equals zero) MUST be rejected and logged for investigation.
- **FR-035**: Each chunk MUST record a `chunk_quality_score`, printable ratio, detection flags, and related warnings for auditing.
- **FR-036**: The pipeline MUST emit average tokens-per-chunk metrics segmented by tenant and model to validate efficiency gains.
- **FR-037**: When semantic chunking is disabled or configuration is missing, the system MUST fall back to the existing fixed-character strategy and log the fallback.

#### Phase 3 – Retrieval Enhancements

- **FR-038**: The retrieval layer MUST combine BM25 keyword ranking (30% weight) with vector similarity (70% weight) when hybrid search is enabled.
- **FR-039**: Hybrid retrieval MUST be controllable via a tenant feature flag that defaults to the current vector-only behavior.
- **FR-040**: RCA responses MUST optionally include citation metadata containing chunk ID, session ID, line range, and a short content preview when the citation flag is enabled.
- **FR-041**: Citation metadata MUST be suppressible per tenant or per request to manage prompt size, with truncation applied when payload budgets would be exceeded.
- **FR-042**: The retrieval service MUST monitor tenant-specific P95 query latency and automatically disable hybrid mode if latency exceeds 1.5× baseline for three consecutive minutes.
- **FR-043**: When BM25 infrastructure is unavailable or degrades, the system MUST log a warning, fall back to vector-only search, and expose a degraded-state flag in responses and metrics.
- **FR-044**: Operators MUST have a BM25 index rebuild utility to refresh historical content without downtime.
- **FR-045**: New chunks MUST be indexed into the BM25 keyword index asynchronously within five minutes of storage, with status visible in metrics.
- **FR-046**: The system MUST expose BM25 index staleness metrics (e.g., `bm25_index_age_seconds` and `bm25_chunks_pending_index`) to support alerting and dashboards.

### Key Entities *(include if feature involves data)*

- **UploadTelemetryEvent**: Captures per-stage metrics (ingest, embed, cache, storage) with tenant, file type, duration, and outcome fields for Prometheus export.
- **UploadSampleSnapshot**: Represents the curated set of top 10 upload file types and sizes used for regression validation and smoke testing.
- **EmbeddingCacheEntry**: Stores normalized text signatures, associated vector metadata, cache hit counters, and eviction timestamps scoped by tenant.
- **ChunkQualityRecord**: Tracks chunk identifiers, associated token budgets, printable ratios, stack trace preservation flags, and chunk_quality_score values for auditing.
- **HybridRetrievalAudit**: Logs hybrid search executions with latency components, weighting inputs, citation coverage, and auto-disable decisions to monitor guardrails.
- **CitationMetadata**: Encapsulates chunk provenance (chunk ID, session ID, line range, preview) attached to RCA findings for analyst trust and traceability.
- **FeatureFlagSettings**: Maintains per-tenant feature toggles and chunk budget overrides, including audit metadata for changes.
- **MetricsSnapshot**: Stores dataset sampling results (top file types, size percentiles, capture metadata) that drive smoke pack updates and regression evidence.

## Success Criteria *(mandatory)*

### Measurable Outcomes

#### Phase 0 – Baseline Hardening

- **SC-001**: At least 95% of uploads under 20 MB complete end-to-end within four minutes while emitting ingest, chunk, embed, cache, and storage telemetry within 30 seconds of completion.
- **SC-002**: Grafana dashboards surface P50, P95, and P99 latencies plus error rates for each pipeline stage within two navigation clicks for operations users, and operators can query 12-month rollups served from Thanos without manual data export.
- **SC-003**: The smoke suite (UTF-8, UTF-16LE/BE, malformed) blocks deployments unless all scenarios pass, sustaining a 0% escape rate for encoding regressions over a rolling quarter.
- **SC-004**: The upload snapshot script produces a dataset of at least 1,000 recent uploads and completes within five minutes of invocation.

#### Phase 1 – Format & Cost Quick Wins

- **SC-005**: Compressed uploads (.gz/.zip) complete within 10% of equivalent uncompressed processing time while remaining inside the four-minute SLA.
- **SC-006**: Pilot tenants with embedding cache enabled achieve a ≥40% hit rate within two weeks and keep ingest failure rates within ±2% of baseline.
- **SC-007**: Embedding API spend decreases by at least 30% for cache-enabled tenants over a four-week observation window.
- **SC-008**: Cache eviction jobs execute without overlapping runs and maintain the cache footprint below the allocated storage budget for each tenant.

#### Phase 2 – Chunk Quality Improvements

- **SC-009**: 95% of sampled multi-line stack traces remain intact within a single chunk after ingestion.
- **SC-010**: Average LLM prompt tokens per RCA incident decrease by at least 15% while fewer than 5% of generated chunks are rejected for quality violations.
- **SC-011**: Analyst satisfaction scores attributed to RCA quality improve by at least 10% compared to the pre-feature baseline (N ≥ 30 responses).

#### Phase 3 – Retrieval Enhancements

- **SC-012**: Hybrid retrieval delivers at least 20% higher precision on a curated 100-incident benchmark relative to vector-only search.
- **SC-013**: Tenant-specific hybrid retrieval P95 latency stays ≤1.5× baseline and under three seconds for 95% of requests, with auto-disable events limited to fewer than one per week per tenant.
- **SC-014**: 90% of sampled RCA responses include citation metadata covering at least one contributing chunk, and average response payload size increases by no more than 10%.
- **SC-015**: At least 70% of analyst feedback submissions cite improved confidence in RCA results due to citation provenance.

### Non-Functional Outcomes

- **NF-001**: Each phase deploys without causing downtime or breaching existing SLAs, verified via deployment post-mortems.
- **NF-002**: Feature flags allow per-tenant enablement and rollback within one hour using documented runbooks.
- **NF-003**: Database migrations associated with the feature complete in under five minutes on datasets containing up to one million chunks.
- **NF-004**: Documentation updates enable new on-call engineers to operate enhanced pipeline features after one business day of onboarding.

## Assumptions

- Prometheus infrastructure and alerting pipelines already exist and can ingest new metrics without additional provisioning.
- Existing text processing components can be reused for extracted archive contents without schema or API changes.
- Pilot tenants can be onboarded to new feature flags incrementally and provide feedback on cache performance and retrieval quality within a sprint.
- Analyst satisfaction will be captured via the current qualitative survey process, which can accommodate an additional question about chunk quality.
- Upstream log ingestion continues to apply PII scrubbing before files reach the pipeline, allowing embeddings to satisfy encryption-at-rest policies.
- The primary Postgres cluster has capacity to accommodate an embedding cache that may grow toward 10 GB over six months before eviction routines balance utilization.
- The existing feature flag system supports tenant-level toggles; if unavailable, rollout order adjusts to use environment-wide flags as an interim control.
- Hybrid retrieval enhancements rely on Postgres full-text search (BM25-style ranking) rather than introducing a new external search service.
- Model provider token limits (e.g., GPT-4o, Claude Sonnet) remain stable; configuration files allow rapid adjustment without redeploying services.
- At least 20% of production uploads are expected to be compressed (.gz/.zip), making the ingestion enhancements impactful; telemetry will validate or adjust this expectation.

## Out of Scope

- Binary log formats such as `.evtx` and other proprietary encodings—captured as future research items.
- Native JSON/XML parsing and schema-aware structured ingestion—deferred until telemetry confirms sufficient demand.
- Streaming uploads exceeding 100 MB—requires additional infrastructure study before commitment.
- Cross-encoder reranking or external search services—postponed until hybrid retrieval baselines performance and cost.
- On-the-fly cache invalidation triggered by upstream content edits—current policy retains entries for 90 days unless evicted by job.
- Automatic incident tagging or temporal analytics—planned only after telemetry highlights repetitive analyst workflows.

## Dependencies

- Prometheus and Grafana stacks for telemetry ingestion and dashboard visualization.
- Postgres with `pgvector` and full-text search extensions enabled for embedding storage and BM25 ranking.
- Alembic (or equivalent) database migration tooling to apply and rollback schema changes.
- Existing feature flag service for tenant-scoped rollout; environment variables serve as contingency controls.
- Python libraries already in use (chardet, python-magic) plus planned additions (`tiktoken`, tokenizer support, BM25 ranking utilities).
- Staging environment that mirrors production scale sufficiently to validate performance and migration impacts.

## Risks

- **Cache warm-up lag**: Hit rates may remain low for initial weeks; mitigation involves expectation setting and monitoring.
- **Database growth**: Embedding cache could exceed projections; eviction thresholds and storage alerts mitigate.
- **Hybrid latency drift**: BM25 and vector combination may breach latency guardrails; feature flags and auto-disable provide rollback.
- **Token configuration drift**: Provider token limits may change; configuration-driven overrides keep updates lightweight.
- **Archive abuse**: Malicious archives (zip bombs) could stress resources; size and timeout policies reduce exposure.
- **Semantic chunking regressions**: Heuristics could misclassify content; robust testing and fallback mode mitigate impact.
- **Citation payload bloat**: Additional metadata may exceed prompt budgets; truncation logic and optional flag address risk.
- **Migration failure**: Schema updates might fail on large datasets; staging rehearsals and documented rollbacks provide safety net.

## Feature Flags

All new capabilities are controlled per tenant to enable safe, incremental rollout:

1. `telemetry_enhanced_metrics_enabled` – exposes expanded stage metrics (default: false in production until verified).
2. `compressed_ingestion_enabled` – activates `.gz`/`.zip` support (default: false).
3. `embedding_cache_enabled` – enables cache lookup and writes (default: false).
4. `embedding_cache_eviction_enabled` – permits background eviction (default: false until hit rate ≥30%).
5. `semantic_chunking_enabled` – turns on token-aware chunking (default: false).
6. `hybrid_retrieval_enabled` – toggles BM25 + vector fusion (default: false).
7. `citation_metadata_enabled` – includes citation payloads in responses (default: false, per-tenant override).

## Rollback Procedures

- **Phase 0**: Disable enhanced telemetry flags; remove metric collectors via configuration without schema changes.
- **Phase 1**: Disable `compressed_ingestion_enabled` and `embedding_cache_enabled`, run documented rollback scripts to drop or archive cache tables, and restore legacy upload extensions list.
- **Phase 2**: Disable `semantic_chunking_enabled`; system automatically reverts to fixed-character chunking with no schema changes required.
- **Phase 3**: Disable `hybrid_retrieval_enabled` and `citation_metadata_enabled`; hybrid search reverts to vector-only and BM25 indexes can be left dormant or cleaned up via runbook.

## Clarifications

### Session 2025-10-14

- Q: How should the system behave when a compressed archive contains encrypted or unsupported files alongside supported text content? → A: Process supported files, mark upload partial, emit warning/telemetry.
- Q: What limits prevent resource exhaustion during compressed archive extraction? → A: Enforce a 100 MB post-extraction cap and 30-second timeout with user-facing errors when exceeded.
- Q: How long should stage-level Prometheus metrics be retained? → A: Maintain 30 days of detailed samples and one year of aggregated rollups for compliance and trend analysis.
- Q: How frequently must the BM25 keyword index refresh? → A: Index asynchronously within five minutes of chunk storage and track status via metrics.
- Q: Do cached embeddings require additional protection? → A: Treat embeddings as sensitive data—only store PII-scrubbed content and encrypt at rest with separate key management.
- Q: How are eviction race conditions avoided? → A: Guard eviction jobs with database advisory locks so that only the first worker proceeds and others exit cleanly.
