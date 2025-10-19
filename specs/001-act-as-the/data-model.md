# Data Model – File Upload & RAG Pipeline Enhancements

## UploadTelemetryEvent
- **Purpose**: Persist per-stage telemetry for ingest, embed, cache, and storage operations.
- **Fields**:
  - `id` (UUID, PK)
  - `tenant_id` (UUID, indexed)
  - `job_id` (UUID, nullable for standalone telemetry)
  - `upload_id` (UUID, references `files.File.id`)
  - `stage` (enum: ingest|embed|cache|storage)
  - `feature_flags` (JSONB, enabled flags at execution time)
  - `status` (enum: success|partial|failed)
  - `duration_ms` (integer)
  - `started_at` / `completed_at` (timestamptz)
  - `metadata` (JSONB, stores error codes, extractor details, skipped entries)
- **Relationships**: Many-to-one with `File`; cascades on delete to keep telemetry consistent.
- **Validation Rules**: `duration_ms >= 0`; `completed_at >= started_at`; `metadata` must include `skipped_count` when `status = partial`.

## UploadSampleSnapshot
- **Purpose**: Store curated upload distributions for smoke/regression packs.
- **Fields**:
  - `id` (UUID, PK)
  - `captured_at` (timestamptz)
  - `tenant_scope` (text, values: specific tenant ID or "multi-tenant")
  - `files` (JSONB array of `{extension, count, p50_size_bytes, p95_size_bytes}`)
  - `requested_by` (UUID, references `User.id`)
- **Relationships**: None beyond `User` reference.
- **Validation Rules**: Exactly 10 entries enforced; each `count > 0`; percentile sizes must be ascending (`p50 <= p95`).

## EmbeddingCacheEntry
- **Purpose**: Cache deduplicated embeddings to avoid redundant LLM calls.
- **Fields**:
  - `id` (UUID, PK)
  - `tenant_id` (UUID, indexed)
  - `content_sha256` (char(64), indexed)
  - `model` (text)
  - `embedding_vector_id` (UUID, references vector store table)
  - `hit_count` (bigint default 0)
  - `last_accessed_at` (timestamptz, indexed)
  - `created_at` (timestamptz)
  - `expires_at` (timestamptz, nullable)
- **Relationships**: Unique constraint on `(tenant_id, content_sha256, model)`; optional FK to `VectorEmbedding` table.
- **Validation Rules**: `expires_at` must be null or > `created_at`; `hit_count` increments atomically.
- **State Transitions**:
  - `new` → `active` on first write
  - `active` → `evicting` when eviction job selects entry
  - `evicting` → `deleted` once worker removes vector + row

## ChunkQualityRecord
- **Purpose**: Persist quality metrics for generated chunks.
- **Fields**:
  - `id` (UUID, PK)
  - `tenant_id` (UUID, indexed)
  - `chunk_id` (UUID, references chunk storage table)
  - `model` (text)
  - `token_budget` (integer)
  - `printable_ratio` (numeric 0–1)
  - `stack_trace_preserved` (boolean)
  - `chunk_quality_score` (numeric 0–1)
  - `warnings` (JSONB array of strings)
  - `created_at` (timestamptz)
- **Relationships**: One-to-one with chunk record; cascades on delete.
- **Validation Rules**: `chunk_quality_score >= 0.9` for chunks promoted to retrieval; otherwise ingestion marks upload partial and logs warning.

## HybridRetrievalAudit (new log table)
- **Purpose**: Track hybrid search executions for latency guardrails.
- **Fields**:
  - `id` (UUID, PK)
  - `tenant_id` (UUID, indexed)
  - `query_id` (UUID)
  - `vector_latency_ms` (integer)
  - `bm25_latency_ms` (integer)
  - `combined_latency_ms` (integer)
  - `result_count` (integer)
  - `citations_returned` (integer)
  - `auto_disabled` (boolean)
  - `created_at` (timestamptz)
- **Relationships**: None direct; query ID links to request logs.
- **Validation Rules**: `auto_disabled` true only when `combined_latency_ms` exceeds configured threshold.

## FeatureFlagSettings (extension)
- **Purpose**: Store per-tenant feature switches and chunk sizing configuration.
- **Fields**:
  - `id` (UUID, PK)
  - `tenant_id` (UUID, unique)
  - `flags` (JSONB, keys include `telemetry`, `compressed_ingest`, `embedding_cache`, `quality_retrieval`)
  - `chunk_overrides` (JSONB mapping `{model: token_budget}`)
  - `updated_at` (timestamptz)
  - `updated_by` (UUID, references `User.id`)
- **Validation Rules**: Token budgets must be positive integers; ensure toggles default false.
