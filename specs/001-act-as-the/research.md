# Research Summary – File Upload & RAG Pipeline Pragmatic Enhancements

## Instrumentation Scope

- **Decision**: Instrument ingest, embed, cache, and storage stages via `core.metrics.MetricsCollector` wrappers and emit Prometheus counters (`rca_pipeline_stage_total`) and histograms (`rca_pipeline_stage_duration_seconds`) with labels for tenant, stage, feature flag, and outcome.
- **Rationale**: Reusing the existing metrics collector keeps the telemetry consistent with current dashboards while satisfying the success criteria that metrics appear within 30 seconds. Stage-specific labels make regression detection straightforward.
- **Alternatives considered**: Direct Prometheus instrumentation inside each service (too fragmented and harder to test); pushing metrics via OpenTelemetry exporter (overhead without current collector support).

## Encoding Smoke Coverage

- **Decision**: Extend the existing smoke harness to replay curated sample files covering UTF-8, UTF-16LE/BE, and malformed byte sequences, failing fast when ingest deviates from baseline.
- **Rationale**: The project already maintains file fixtures under `tests/smoke/files`; augmenting the suite minimizes new tooling while providing CI gate coverage.
- **Alternatives considered**: Build a standalone binary fuzz tester (overkill for targeted regressions); rely only on unit tests (would miss end-to-end regressions).

## Archive Ingestion

- **Decision**: Use Python’s `gzip` and `zipfile` modules backed by `tempfile.SpooledTemporaryFile` to extract `.gz` and `.zip` archives, enforcing cumulative extracted size limits and skipping unsupported entries with warnings.
- **Rationale**: Standard library support keeps dependencies minimal and integrates cleanly with asynchronous file service routines while enabling partial success handling per clarification.
- **Alternatives considered**: Introduce `libarchive` bindings (adds native dependency complexity); reject archives outright (fails roadmap goal).

## Embedding Cache Design

- **Decision**: Create an `embedding_cache` Postgres table storing `tenant_id`, `content_sha256`, `vector_id`, `model`, `created_at`, `last_accessed_at`, and `hit_count`, with a unique constraint on `(tenant_id, content_sha256, model)` and eviction managed by an async worker pulling batches via `NOW() - last_accessed_at > threshold` once hit rate ≥30%.
- **Rationale**: Postgres keeps cache operations transactional with existing migrations, aligns with rollback requirements, and leverages `pgvector` for reuse of stored embeddings.
- **Alternatives considered**: Redis cache (fast but lacks durable rollback story); application-level memoization (does not share hits between processes).

## Token-Aware Chunking

- **Decision**: Integrate `tiktoken` for GPT routes and Anthropic’s tokenizer via their SDK, centralizing chunk sizing configuration in `core/files/chunking_config.py` with tenant + model overrides delivered through admin settings.
- **Rationale**: Dedicated tokenizers ensure accuracy against provider limits while isolating configuration so ops can adjust without redeploying.
- **Alternatives considered**: Estimate tokens via character counts (too imprecise and fails success criteria); call model APIs for token counts (slow and rate-limited).

## Stack Trace Preservation & Quality Scoring

- **Decision**: Preserve code blocks and stack traces by detecting common frame patterns prior to splitting, normalize whitespace, and compute `chunk_quality_score` (0–1) combining printable ratio and metadata coverage; reject chunks <0.9.
- **Rationale**: Aligns with spec guardrails while producing auditable metrics for pilots.
- **Alternatives considered**: Heuristic-free approach (risks garbled output); heavy NLP summarization (too slow for ingest SLA).

## Hybrid Retrieval Strategy

- **Decision**: Combine existing pgvector similarity search with PostgreSQL BM25-style ranking using `tsvector` + `ts_rank_cd`, merging scores through weighted sum, and fallback to vector-only if lexical search exceeds latency thresholds.
- **Rationale**: Keeps infrastructure in Postgres, simplifying deployment and allowing real-time disablement per tenant when latency exceeds 1.5× baseline.
- **Alternatives considered**: Deploy Elasticsearch/OpenSearch (introduces new ops surface area); rely solely on vector search with metadata filters (fails citation recall goals).

## Upload Sampling Script

- **Decision**: Provide a `scripts/pipeline/snapshot_upload_distribution.py` CLI using SQL queries against `UploadTelemetryEvent` to export the top 10 file types and size percentiles to JSON/CSV.
- **Rationale**: Lightweight script leverages telemetry data to refresh regression packs without manual database access.
- **Alternatives considered**: Build Grafana dashboard export flow (manual and harder to automate); add API endpoint (unnecessary exposure).
