# Tasks: File Upload & RAG Pipeline Pragmatic Enhancements

**Input**: Design documents from `/specs/001-act-as-the/`
**Prerequisites**: plan.md (complete), spec.md (complete), research.md (complete), data-model.md (complete), contracts/ (complete)

**Organization**: Tasks are grouped by user story/phase to enable independent implementation and testing of each capability.

## Format: `[ID] [P?] [Phase/Story] Description`
- **[P]**: Can run in parallel (different files, no dependencies)
- **[Phase/Story]**: Which phase or user story this task belongs to (e.g., P0, P1, P2)
- Include exact file paths in descriptions

## Path Conventions
- Multi-service backend: `apps/api/`, `apps/worker/`, `core/`, `tests/`
- Adjust paths based on plan.md structure

---

## Phase 0: Baseline Hardening (Observable Ingestion Guardrails - Priority P1)

**Goal**: Establish telemetry instrumentation, smoke test coverage, and upload sampling to safely monitor and evaluate all future enhancements.

**Independent Test**: Enable telemetry feature flag, trigger test uploads across encodings, verify Prometheus metrics and smoke suite detect regressions without other flags enabled.

### Setup & Infrastructure

- [x] T001 [P] [P0] Create `core/metrics/pipeline_metrics.py` with stage-specific MetricsCollector wrappers for ingest, chunk, embed, cache, storage
- [x] T002 [P] [P0] Define Prometheus metric schemas: counters (`rca_pipeline_stage_total`) and histograms (`rca_pipeline_stage_duration_seconds`) with labels (tenant, stage, file_type, size_category, status, feature_flags)
- [x] T003 [P] [P0] Extend `core/db/models.py` with the `UploadTelemetryEvent` SQLAlchemy model (id, tenant_id, job_id, upload_id, stage, feature_flags, status, duration_ms, started_at, completed_at, metadata); keep `core/files/telemetry.py` as thin helper wrappers only
- [x] T004 [P0] Add Alembic migration for `upload_telemetry_events` table in `alembic/versions/` with indexes on (tenant_id, stage, status, created_at)
- [x] T005 [P] [P0] Create `core/config/feature_flags.py` extending existing flag system with `telemetry_enhanced_metrics_enabled` flag (default: false)

### Instrumentation

- [x] T006 [P0] Instrument `FileService.ingest_upload` in `core/files/service.py` to emit ingest stage metrics and persist telemetry events
- [x] T007 [P0] Instrument chunking stage in `core/files/chunker.py` (or equivalent) to emit chunk metrics and log durations
- [x] T008 [P0] Instrument embedding calls in `apps/worker/pipelines/` to emit embed stage metrics with cache hit/miss context
- [x] T009 [P0] Instrument storage operations to emit storage stage metrics with success/failure outcomes
- [x] T010 [P0] Add telemetry collection to partial upload scenarios (skipped files, warnings) with structured metadata logging

### Smoke Tests

- [x] T011 [P] [P0] Create `tests/smoke/files/` directory with curated fixtures: UTF-8, UTF-16LE, UTF-16BE, malformed samples (each ~1-5 MB)
- [x] T012 [P] [P0] Implement `tests/smoke/test_file_encoding.py` with test cases for each encoding fixture validating end-to-end processing
- [x] T013 [P] [P0] Extend existing test harness to detect silent failures and fail CI when encoding regressions occur
- [x] T014 [P] [P0] Add GitHub Actions workflow step in `.github/workflows/` to execute smoke suite on every deployment

### Upload Sampling

- [x] T015 [P] [P0] Create `scripts/pipeline/snapshot_upload_distribution.py` CLI using SQL queries against `upload_telemetry_events` to export top 10 file types and size percentiles
- [x] T016 [P] [P0] Add JSON/CSV output support to snapshot script with configurable tenant scope and date ranges
- [x] T017 [P] [P0] Document snapshot script usage in `quickstart.md` with examples for refreshing smoke fixtures

### Documentation & Monitoring

- [x] T018 [P] [P0] Create `docs/telemetry/overview.md` documenting metric schemas, labels, retention policies, and dashboard access
- [x] T019 [P] [P0] Create `deploy/ops/telemetry.md` runbook covering feature flag enablement, metric validation, and rollback procedures
- [x] T020 [P] [P0] Update Grafana dashboards (or provide dashboard JSON) to visualize P50/P95/P99 latencies, error rates, throughput by stage and tenant
- [x] T021 [P] [P0] Configure Prometheus retention by keeping 30-day detailed samples locally and enabling remote-write to the managed Thanos bucket with 12-month downsampled rollups and alerting on replication failures

### Testing & Validation

- [x] T022 [P] [P0] Unit test `core/metrics/pipeline_metrics.py` wrappers verifying correct label application and metric emission
- [x] T023 [P] [P0] Unit test `UploadTelemetryEvent` model validation rules (duration_ms ≥ 0, completed_at ≥ started_at, metadata structure)
- [x] T024 [P] [P0] Integration test: upload 20 MB file, verify all stage metrics appear in Prometheus within 30 seconds, and confirm the Thanos endpoint exposes aggregated rollups for the same upload
- [x] T025 [P] [P0] Integration test: upload malformed file, verify smoke suite detects regression and fails deployment gate

**Checkpoint Phase 0**: Telemetry instrumented, smoke coverage complete, sampling script functional. Metrics visible in dashboards. Ready for Phase 1.

---

## Phase 1: Compressed Ingestion & Embedding Cache (Priority P2)

**Goal**: Support `.gz`/`.zip` uploads with partial handling and introduce opt-in embedding cache with eviction strategy to reduce costs.

**Independent Test**: Toggle compressed-upload and embedding-cache flags for staging tenant, upload archives with mixed content, verify cache hits and eviction behavior.

### Compressed File Support - Infrastructure

- [x] T026 [P] [P1] Create `core/files/extraction.py` with `ArchiveExtractor` class supporting `.gz` and `.zip` formats using stdlib `gzip` and `zipfile`
- [x] T027 [P] [P1] Implement extraction size limit enforcement (100 MB cumulative) and timeout enforcement (30 seconds) in `ArchiveExtractor`
- [x] T028 [P] [P1] Add `core/files/validation.py` with extraction policy checks and clear error message generation for limit violations
- [x] T029 [P] [P1] Extend `core/config/feature_flags.py` with `compressed_ingestion_enabled` flag (default: false)

### Compressed File Support - Integration

- [x] T030 [P1] Update `FileService.ingest_upload` in `core/files/service.py` to detect `.gz`/`.zip` extensions, delegate to `ArchiveExtractor`, and track cumulative processing time so work aborts with partial status before the four-minute SLA is breached
- [x] T031 [P1] Implement first-supported-file selection logic for `.zip` archives and emit warnings to telemetry when multiple files present
- [x] T032 [P1] Add partial upload status handling: continue processing supported members, mark upload partial, emit structured warnings and skipped_count metadata
- [x] T033 [P1] Handle corrupted archive gracefully: catch extraction exceptions, return retriable error responses, capture diagnostics in telemetry
- [x] T034 [P1] Update `apps/api/routers/files.py` to accept `.gz`/`.zip` in allowed_types when feature flag enabled

### Embedding Cache - Data Model & Migration

- [x] T035 [P] [P1] Create `core/cache/embedding_cache_service.py` with `EmbeddingCacheEntry` model (id, tenant_id, content_sha256, model, embedding_vector_id, hit_count, last_accessed_at, created_at, expires_at)
- [x] T036 [P] [P1] Add Alembic migration for `embedding_cache` table in `alembic/versions/` with unique constraint on (tenant_id, content_sha256, model) and indexes on last_accessed_at
- [x] T037 [P] [P1] Implement forward migration DDL and rollback script documented in `deploy/ops/migrations/embedding_cache_migration.py`
- [x] T038 [P] [P1] Add AES-256 encryption-at-rest configuration in `core/config/settings.py` with keys loaded from environment/managed secrets
- [x] T039 [P] [P1] Implement PII scrubbing metadata validation in cache service: reject cache writes lacking upstream scrub confirmation

### Embedding Cache - Service Layer

- [x] T040 [P1] Implement `EmbeddingCacheService.lookup(tenant_id, content_hash, model)` checking cache before external API calls
- [x] T041 [P1] Implement `EmbeddingCacheService.store(tenant_id, content_hash, model, embedding)` with encrypted payload persistence
- [x] T042 [P1] Implement cache hit tracking: increment `hit_count`, update `last_accessed_at`, emit `embedding_cache_hits_total` metric
- [x] T043 [P1] Add cache miss metric emission: `embedding_cache_requests_total` labeled by tenant and model
- [x] T044 [P1] Integrate cache service into worker embedding pipeline in `apps/worker/pipelines/` wrapping LLM API calls

### Embedding Cache - Eviction Job

- [ ] T045 [P] [P1] Create `apps/worker/tasks/cache_eviction.py` async task acquiring Postgres advisory lock before eviction execution
- [ ] T046 [P1] Implement eviction policy: remove entries with hit_count=0 AND created_at > 90 days, emit eviction count metrics
- [ ] T047 [P1] Add cache hit rate calculation logic: only schedule eviction when tenant hit rate ≥30%
- [ ] T048 [P1] Implement graceful lock failure handling: exit with INFO log "Eviction already in progress" when lock unavailable
- [ ] T049 [P1] Integrate eviction task into existing worker job queue with configurable scheduling (daily/weekly)

### Feature Flags & Admin API

- [ ] T050 [P] [P1] Extend `core/config/feature_flags.py` with `embedding_cache_enabled` and `embedding_cache_eviction_enabled` flags (defaults: false)
- [ ] T051 [P] [P1] Create `apps/api/routers/admin_feature_flags.py` implementing GET/PUT `/admin/tenants/{tenant_id}/feature-flags` per contracts/pipeline.yaml
- [ ] T052 [P] [P1] Implement POST `/admin/embedding-cache/tenants/{tenant_id}/evict` endpoint with TTL parameter validation
- [ ] T053 [P] [P1] Add authorization middleware ensuring only admin users can modify feature flags and trigger eviction

### Documentation & Runbooks

- [ ] T054 [P] [P1] Create `deploy/ops/docs/compressed-ingestion.md` documenting extraction limits, error handling, partial upload behavior
- [ ] T055 [P] [P1] Create `deploy/ops/docs/embedding-cache.md` covering cache architecture, encryption, eviction policies, monitoring, rollback
- [ ] T056 [P] [P1] Update `quickstart.md` with Phase 1 setup steps: migration commands, feature flag examples, cache configuration
- [ ] T057 [P] [P1] Document rollback procedures: disable flags, run rollback migration script, restore legacy upload whitelist

### Testing & Validation

- [ ] T058 [P] [P1] Unit test `ArchiveExtractor` with valid `.gz`, `.zip`, corrupted, oversized, and timeout scenarios
- [ ] T059 [P] [P1] Unit test first-file selection logic for multi-file `.zip` archives
- [ ] T060 [P] [P1] Unit test `EmbeddingCacheService.lookup()` and `.store()` with encryption validation
- [ ] T061 [P] [P1] Unit test cache eviction policy logic (hit_count, age thresholds) without database
- [ ] T062 [P] [P1] Unit test advisory lock acquisition and graceful failure handling
- [ ] T063 [P] [P1] Integration test: upload `.zip` with mixed content, verify partial status, warnings, telemetry
- [ ] T064 [P] [P1] Integration test: cache hit scenario - upload duplicate content, verify cache metrics increment, no external API call
- [ ] T065 [P] [P1] Integration test: eviction job runs successfully, removes stale entries, emits correct metrics
- [ ] T066 [P] [P1] Contract test: admin feature flag endpoints match OpenAPI spec in contracts/pipeline.yaml
- [ ] T067 [P] [P1] Update smoke tests in `tests/smoke/` to cover `.zip` upload scenarios

**Checkpoint Phase 1**: Compressed ingestion functional, embedding cache operational with eviction, admin controls exposed. Cache hit rate tracking validates 30%+ threshold. Ready for Phase 2.

---

## Phase 2: Chunk Quality Improvements (Priority P2)

**Goal**: Implement token-aware chunking per model, stack trace preservation, quality scoring, and rejection of low-quality chunks.

**Independent Test**: Enable quality-and-retrieval flag, configure token budgets for two models, upload logs with stack traces, verify chunk quality metrics and rejection behavior.

### Token-Aware Chunking - Infrastructure

- [ ] T068 [P] [P2] Create `core/files/chunking_config.py` with per-model token budget configuration (GPT-4o: 8000, Claude Sonnet: 10000, GPT-5: 12000)
- [ ] T069 [P] [P2] Add `tiktoken` dependency to `requirements.txt` and integrate tokenizer for OpenAI models
- [ ] T070 [P] [P2] Integrate Anthropic tokenizer via SDK for Claude models
- [ ] T071 [P] [P2] Implement `TokenAwareChunker` class in `core/files/chunker.py` with model-specific sizing logic
- [ ] T072 [P] [P2] Add fallback to fixed-character chunking when model config missing or tokenizer unavailable, log warning

### Stack Trace Preservation

- [ ] T073 [P] [P2] Create `core/files/heuristics.py` with stack trace detection patterns (regex: `^\s+at\s+`, `^\s+File\s+"`, `^\s+in\s+<module>`)
- [ ] T074 [P] [P2] Implement stack trace boundary detection in `TokenAwareChunker` to prevent splitting multi-line traces across chunks
- [ ] T075 [P] [P2] Add integration tests validating stack traces remain intact within single chunks for common languages (Python, Java, JavaScript)

### Chunk Quality Scoring

- [ ] T076 [P] [P2] Create `core/files/quality.py` with `ChunkQualityValidator` class computing printable_ratio (printable_chars / total_chars)
- [ ] T077 [P] [P2] Implement chunk rejection logic: reject if printable_ratio < 0.90 or content.strip() empty, log detailed rejection reasons
- [ ] T078 [P] [P2] Create `ChunkQualityRecord` model in `core/db/models.py` (id, tenant_id, chunk_id, model, token_budget, printable_ratio, stack_trace_preserved, chunk_quality_score, warnings, created_at)
- [ ] T079 [P] [P2] Add Alembic migration for `chunk_quality_records` table with foreign key to chunks table, cascade on delete
- [ ] T080 [P2] Compute and store `chunk_quality_score` (0-1 scale) combining printable ratio, token efficiency, metadata completeness
- [ ] T081 [P2] Integrate quality validation into worker chunking pipeline: persist `ChunkQualityRecord`, suppress low-quality chunks from retrieval
- [ ] T082 [P2] Emit `average_tokens_per_chunk` metric per model and tenant to Prometheus for efficiency tracking

### Feature Flags & Admin Configuration

- [ ] T083 [P] [P2] Extend `core/config/feature_flags.py` with `semantic_chunking_enabled` flag (default: false)
- [ ] T084 [P] [P2] Create GET/PUT `/admin/tenants/{tenant_id}/chunking` endpoints in `apps/api/routers/admin_feature_flags.py` per contracts/pipeline.yaml
- [ ] T085 [P] [P2] Implement runtime chunk budget override system: read per-tenant overrides from database, apply without service restart
- [ ] T086 [P] [P2] Add validation ensuring token budgets are positive integers, reject invalid configurations with clear errors

### Documentation & Monitoring

- [ ] T087 [P] [P2] Create `docs/chunking/token-aware-chunking.md` explaining model-specific sizing, stack trace preservation, quality scoring
- [ ] T088 [P] [P2] Update `deploy/ops/docs/` with chunking configuration guide, fallback behavior, troubleshooting
- [ ] T089 [P] [P2] Add Grafana panels for chunk quality metrics: average tokens, quality scores, rejection rates by model and tenant
- [ ] T090 [P] [P2] Document rollback: disable `semantic_chunking_enabled` flag, system auto-reverts to fixed-character chunking

### Testing & Validation

- [ ] T091 [P] [P2] Unit test `TokenAwareChunker` with various models ensuring token budgets respected
- [ ] T092 [P] [P2] Unit test stack trace detection patterns with real-world log samples (Python, Java, JS, C# traces)
- [ ] T093 [P] [P2] Unit test `ChunkQualityValidator.compute_printable_ratio()` with edge cases (empty, binary, unicode)
- [ ] T094 [P] [P2] Unit test chunk rejection logic: verify chunks <0.90 ratio excluded, warnings logged
- [ ] T095 [P] [P2] Integration test: upload log with multi-line stack trace, verify preserved in single chunk, quality record persisted
- [ ] T096 [P] [P2] Integration test: configure different token budgets for two models, verify chunk sizes adapt correctly
- [ ] T097 [P] [P2] Integration test: upload batch with low-quality chunks, verify rejection, partial upload status, telemetry
- [ ] T098 [P] [P2] Contract test: chunking configuration endpoints match OpenAPI spec

**Checkpoint Phase 2**: Token-aware chunking operational, stack traces preserved, quality scoring functional. Chunk rejection and fallback mechanisms validated. Ready for Phase 3.

---

## Phase 3: Retrieval Enhancements (Hybrid Search & Citations - Priority P3)

**Goal**: Implement hybrid BM25+vector retrieval with automatic latency guardrails and citation metadata for analyst trust.

**Independent Test**: Enable hybrid retrieval flag, perform queries, verify combined ranking, citations present, P95 latency monitored, auto-disable triggers when threshold exceeded.

### BM25 Infrastructure

- [ ] T099 [P] [P3] Create `core/retrieval/bm25_index.py` with Postgres full-text search setup using `tsvector` and `ts_rank_cd`
- [ ] T100 [P] [P3] Add Alembic migration creating `tsvector` columns and GIN indexes on chunk content in chunks table
- [ ] T101 [P] [P3] Implement asynchronous BM25 indexing worker task in `apps/worker/tasks/bm25_indexer.py` processing new chunks within 5 minutes
- [ ] T102 [P] [P3] Add `bm25_chunks_pending_index` gauge metric and `bm25_index_age_seconds` histogram for staleness tracking
- [ ] T103 [P] [P3] Create `core/retrieval/bm25_rebuild.py` utility for full index rebuild on historical chunks (runbook-documented)

### Hybrid Retrieval - Core Logic

- [ ] T104 [P] [P3] Create `core/retrieval/hybrid.py` with `HybridSearchService` class combining BM25 (30%) and vector similarity (70%)
- [ ] T105 [P3] Implement score normalization and weighted fusion logic in `HybridSearchService.search(query, limit, weights)`
- [ ] T106 [P3] Add fallback to vector-only search when BM25 index unavailable, set degraded-state flag in response metadata
- [ ] T107 [P3] Integrate `HybridSearchService` into existing retrieval pipeline in `core/retrieval/service.py` guarded by feature flag

### Citation Metadata

- [ ] T108 [P] [P3] Create `core/retrieval/citations.py` with `CitationMetadata` model (chunk_id, session_id, line_range, content_preview)
- [ ] T109 [P3] Extend RCA response schema in `apps/api/routers/conversation.py` to include optional `citations` array per finding
- [ ] T110 [P3] Implement citation truncation logic: when payload exceeds budget, keep top N contributors and note "additional sources available"
- [ ] T111 [P3] Add per-request citation flag control: allow clients to suppress citations via query parameter when managing prompt size

### Latency Monitoring & Auto-Disable

- [ ] T112 [P] [P3] Create `HybridRetrievalAudit` model in `core/db/models.py` (id, tenant_id, query_id, vector_latency_ms, bm25_latency_ms, combined_latency_ms, result_count, citations_returned, auto_disabled, created_at)
- [ ] T113 [P] [P3] Add Alembic migration for `hybrid_retrieval_audit` table with indexes on (tenant_id, created_at)
- [ ] T114 [P3] Implement P95 latency monitoring in `HybridSearchService`: calculate rolling P95 per tenant, compare against baseline
- [ ] T115 [P3] Implement auto-disable logic: if P95 > 1.5× baseline for 3 consecutive minutes, disable hybrid flag for tenant, emit alert
- [ ] T116 [P3] Add `hybrid_retrieval_auto_disable_total` counter metric labeled by tenant and reason
- [ ] T117 [P3] Persist audit records for every hybrid search execution to support compliance and forensics

### Feature Flags & Admin Endpoints

- [ ] T118 [P] [P3] Extend `core/config/feature_flags.py` with `hybrid_retrieval_enabled` and `citation_metadata_enabled` flags (defaults: false)
- [ ] T119 [P] [P3] Create GET `/admin/retrieval/tenants/{tenant_id}/status` endpoint in `apps/api/routers/admin_feature_flags.py` per contracts/pipeline.yaml
- [ ] T120 [P] [P3] Implement `HybridRetrievalStatus` response schema including hybrid_enabled, p95_latency_ms, baseline_p95_latency_ms, last_auto_disable_at, citation_coverage_ratio, cache_hit_rate
- [ ] T121 [P] [P3] Add admin endpoint to manually re-enable hybrid retrieval after investigating auto-disable events

### Documentation & Monitoring

- [ ] T122 [P] [P3] Create `docs/retrieval/hybrid-search.md` explaining BM25+vector fusion, weighting, fallback behavior, auto-disable guardrails
- [ ] T123 [P] [P3] Create `deploy/ops/docs/hybrid-retrieval.md` runbook covering index rebuild, latency investigation, manual override procedures
- [ ] T124 [P] [P3] Add Grafana panels for hybrid retrieval metrics: P95 latency trends, auto-disable events, citation coverage, BM25 index staleness
- [ ] T125 [P] [P3] Update `quickstart.md` with Phase 3 validation steps: enable flags, verify citations, monitor latency dashboards
- [ ] T126 [P] [P3] Document rollback: disable `hybrid_retrieval_enabled` flag, system reverts to vector-only, BM25 indexes dormant

### Testing & Validation

- [ ] T127 [P] [P3] Unit test BM25 ranking against sample queries with known relevance scores
- [ ] T128 [P] [P3] Unit test hybrid score fusion with various weighting configurations (30/70, 50/50, 70/30)
- [ ] T129 [P] [P3] Unit test fallback logic: BM25 unavailable triggers vector-only mode, degraded flag set
- [ ] T130 [P] [P3] Unit test citation truncation: verify top N sources retained when payload exceeds limit
- [ ] T131 [P] [P3] Unit test auto-disable logic: simulate sustained high latency, verify flag disabled after 3-minute window
- [ ] T132 [P] [P3] Integration test: enable hybrid retrieval, execute query, verify both BM25 and vector scores combined, citations present
- [ ] T133 [P] [P3] Integration test: BM25 index update lag - new chunk indexed within 5 minutes, staleness metric accurate
- [ ] T134 [P] [P3] Integration test: auto-disable scenario - trigger high latency, verify flag disabled, alert emitted, audit record created
- [ ] T135 [P] [P3] Performance test: measure P95 latency with hybrid vs vector-only on 100-query benchmark, validate ≤1.5× baseline
- [ ] T136 [P] [P3] Contract test: retrieval status endpoint matches OpenAPI spec

**Checkpoint Phase 3**: Hybrid retrieval operational with latency guardrails, citations functional, auto-disable tested. BM25 indexing asynchronous and monitored. All phases complete.

---

## Phase 4: Polish & Cross-Cutting Concerns

**Purpose**: Final integration, documentation, performance tuning, and cross-phase validation.

### Integration & Compatibility

- [ ] T137 [P] [P4] End-to-end integration test: upload compressed file, verify telemetry, cache hit, chunk quality, hybrid retrieval with citations all functional together
- [ ] T138 [P] [P4] Test feature flag isolation: verify each capability (telemetry, compression, cache, chunking, hybrid) works independently when others disabled
- [ ] T139 [P] [P4] Test rollback scenarios: disable each phase's flags, verify graceful fallback behavior, no data corruption
- [ ] T140 [P] [P4] Validate SLA compliance: upload 20 MB file through full pipeline, verify completion within 4 minutes with all features enabled, and run a stress case that triggers the ingest watchdog to confirm the pipeline aborts gracefully before the SLA is breached

### Documentation & Training

- [ ] T141 [P] [P4] Create comprehensive feature overview in `docs/features/rag-pipeline-enhancements.md` linking all phase docs
- [ ] T142 [P] [P4] Update `README.md` with feature highlights, links to runbooks, quickstart references
- [ ] T143 [P] [P4] Create operator training guide in `docs/operations/` covering telemetry dashboards, feature flag management, troubleshooting workflows
- [ ] T144 [P] [P4] Document migration paths for tenants: telemetry → compression → cache → chunking → hybrid with validation checkpoints

### Performance & Optimization

- [ ] T145 [P] [P4] Profile embedding cache lookup latency, optimize queries if exceeding 50ms P95
- [ ] T146 [P] [P4] Profile hybrid retrieval end-to-end latency, optimize BM25 query execution if needed
- [ ] T147 [P] [P4] Review database migration performance on staging replica with 1M chunks, document execution times
- [ ] T148 [P] [P4] Validate Prometheus metric cardinality: ensure label combinations don't exceed cardinality budgets

### Security & Compliance

- [ ] T149 [P] [P4] Security review: validate encryption keys never logged, cache entries properly isolated by tenant
- [ ] T150 [P] [P4] Compliance review: verify PII scrubbing enforced before caching, audit logs retention matches policy (30 days + 1 year)
- [ ] T151 [P] [P4] Penetration test: attempt zip bomb upload, verify size/timeout limits prevent resource exhaustion
- [ ] T152 [P] [P4] Access control audit: verify only admin users can modify feature flags, trigger eviction, rebuild indexes

### Monitoring & Alerting

- [ ] T153 [P] [P4] Configure Prometheus alerts: ingest failure rate >5%, cache hit rate <20%, hybrid latency >1.5× baseline, BM25 index lag >10 minutes
- [ ] T154 [P] [P4] Create incident response runbooks for each alert condition in `deploy/ops/runbooks/`
- [ ] T155 [P] [P4] Validate Grafana dashboards accessible to operations team with proper permissions, auto-refresh enabled
- [ ] T156 [P] [P4] Test alert delivery: trigger test alerts, verify PagerDuty/Slack/email notifications reach on-call team

### Final Validation

- [ ] T157 [P] [P4] Run full smoke test suite with all phases enabled, verify 0% regression rate
- [ ] T158 [P] [P4] Execute `quickstart.md` steps on clean staging environment, verify all commands succeed
- [ ] T159 [P] [P4] Conduct user acceptance testing with pilot tenant: upload mix of files, review RCA output with citations, collect feedback
- [ ] T160 [P] [P4] Stakeholder demo: showcase telemetry dashboards, cache cost savings, chunk quality improvements, hybrid retrieval precision

**Checkpoint Phase 4**: All features integrated, documented, monitored, and validated. Ready for production rollout.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 0 (Baseline)**: No dependencies - start immediately. BLOCKS all other phases.
- **Phase 1 (Compression/Cache)**: Depends on Phase 0 telemetry for monitoring. Can start after P0 checkpoint.
- **Phase 2 (Chunking)**: Depends on Phase 0 telemetry. Can run parallel with Phase 1 if staffed.
- **Phase 3 (Retrieval)**: Depends on Phase 2 chunk quality records and Phase 1 cache for full validation. Can start after P2 checkpoint.
- **Phase 4 (Polish)**: Depends on all phases complete for end-to-end testing.

### Critical Path

1. **Phase 0 complete** → Foundation ready (telemetry, smoke tests, sampling)
2. **Phase 1 complete** → Compression + cache operational (cost savings begin)
3. **Phase 2 complete** → Chunk quality improved (LLM efficiency gains)
4. **Phase 3 complete** → Hybrid retrieval + citations (analyst trust improved)
5. **Phase 4 complete** → Production-ready with monitoring

### Parallel Opportunities

- **Within Phase 0**: Tasks T001-T005 (infrastructure) can run parallel
- **Within Phase 1**: Archive extraction (T026-T029) parallel with cache models (T035-T039)
- **Within Phase 2**: Token infrastructure (T068-T072) parallel with stack trace detection (T073-T075)
- **Within Phase 3**: BM25 infrastructure (T099-T103) parallel with citation models (T108-T111)
- **Across Phases**: If multi-person team, Phase 1 and Phase 2 can overlap after Phase 0 complete

### Feature Flag Rollout Order

1. Enable `telemetry_enhanced_metrics_enabled` for all tenants (Phase 0)
2. Enable `compressed_ingestion_enabled` for pilot tenants (Phase 1)
3. Enable `embedding_cache_enabled` for pilot tenants, monitor hit rates (Phase 1)
4. Enable `embedding_cache_eviction_enabled` once hit rate ≥30% (Phase 1)
5. Enable `semantic_chunking_enabled` for pilot tenants (Phase 2)
6. Enable `hybrid_retrieval_enabled` for pilot tenants (Phase 3)
7. Enable `citation_metadata_enabled` for pilot tenants (Phase 3)
8. Gradual rollout to production tenants with monitoring at each step

---

## Implementation Strategy

### MVP Approach (Phase 0 Only)

1. Complete Phase 0
2. Deploy telemetry to production
3. Monitor for 1-2 weeks
4. Validate dashboards, smoke tests, sampling
5. Use metrics to inform Phase 1-3 priorities

### Incremental Delivery

1. **Phase 0** → Deploy telemetry → Monitor baseline
2. **Phase 1** → Deploy compression + cache → Measure cost savings
3. **Phase 2** → Deploy chunk quality → Measure token reduction
4. **Phase 3** → Deploy hybrid retrieval → Measure precision improvement
5. Each phase delivers value independently

### Risk Mitigation

- Feature flags allow instant rollback at any phase
- Smoke tests prevent regressions
- Telemetry provides early warning signals
- Pilot tenants validate before broad rollout
- Documented runbooks accelerate incident response

---

## Notes

- [P] tasks = different files/modules, can run in parallel
- [Phase] label maps task to specification user story/phase
- Each phase independently completable and deployable
- Commit after each logical task or task group
- Stop at checkpoints to validate phase independently
- Monitor metrics continuously during rollout
- All schema changes tested on staging replicas first
