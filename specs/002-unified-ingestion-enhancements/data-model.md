# Data Model: Unified Ingestion Intelligence Enhancements

## IncidentFingerprint
- **Purpose**: Persist searchable similarity metadata for completed RCA sessions.
- **Key Fields**:
  - `id` (UUID, primary key)
  - `session_id` (UUID, unique per RCA session)
  - `tenant_id` (UUID, foreign key to tenant/workspace)
  - `embedding_vector` (pgvector, cosine distance metric)
  - `summary_text` (TEXT, truncated to 4096 chars)
  - `relevance_threshold` (REAL, default 0.5)
  - `visibility_scope` (ENUM: `tenant_only`, `multi_tenant`)
  - `created_at` / `updated_at` (TIMESTAMP WITH TIME ZONE)
  - `fingerprint_status` (ENUM: `available`, `degraded`, `missing`)
  - `safeguard_notes` (JSONB, optional metrics or warnings)
- **Relationships**:
  - `session_id` references `jobs.session_id`
  - `tenant_id` enforces multi-tenant partitioning and RLS policies
- **Validation Rules**:
  - `embedding_vector` required when `fingerprint_status = available`
  - `summary_text` required and trimmed of PII
  - `visibility_scope = multi_tenant` only when analyst audit controls enabled
- **State Transitions**:
  - `missing → available` after successful embedding generation
  - `available → degraded` if downstream recalculation fails

## PlatformDetectionResult
- **Purpose**: Track platform detection metadata and parser outcomes per ingestion job.
- **Key Fields**:
  - `id` (UUID, primary key)
  - `job_id` (UUID, foreign key to ingestion job record)
  - `detected_platform` (ENUM: `blue_prism`, `uipath`, `appian`, `automation_anywhere`, `pega`, `unknown`)
  - `confidence_score` (NUMERIC(5,4))
  - `detection_method` (TEXT, e.g., `heuristic`, `ml_model`)
  - `parser_executed` (BOOLEAN)
  - `parser_version` (TEXT)
  - `extracted_entities` (JSONB array of platform-specific objects)
  - `feature_flag_snapshot` (JSONB, captured at run time)
  - `created_at` (TIMESTAMP WITH TIME ZONE)
- **Relationships**:
  - `job_id` references ingestion job table for cascading lifecycle
- **Validation Rules**:
  - `confidence_score` between 0 and 1
  - `parser_executed` true only when `confidence_score ≥ rollout_threshold`
  - `extracted_entities` schema validated per platform contract
- **State Transitions**:
  - Initial record inserted post-archive extraction
  - Updates allowed to append entities after parser completes

## ArchiveExtractionAudit
- **Purpose**: Record extraction outcomes and safeguard metrics for uploaded archives.
- **Key Fields**:
  - `id` (UUID, primary key)
  - `job_id` (UUID, foreign key)
  - `source_filename` (TEXT)
  - `archive_type` (ENUM: `zip`, `gz`, `bz2`, `xz`, `tar_gz`, `tar_bz2`, `tar_xz`)
  - `member_count` (INTEGER)
  - `compressed_size_bytes` (BIGINT)
  - `estimated_uncompressed_bytes` (BIGINT)
  - `decompression_ratio` (NUMERIC(10,2))
  - `guardrail_status` (ENUM: `passed`, `blocked_ratio`, `blocked_members`, `timeout`, `error`)
  - `blocked_reason` (TEXT nullable)
  - `partial_members` (JSONB array with file names + reasons)
  - `started_at` / `completed_at` (TIMESTAMP WITH TIME ZONE)
- **Relationships**:
  - `job_id` references ingestion job table (one-to-one per uploaded archive)
- **Validation Rules**:
  - `decompression_ratio` computed, must be recorded when guardrail evaluated
  - `guardrail_status = blocked_*` requires `blocked_reason`
  - `member_count` non-negative, `compressed_size_bytes` > 0
- **State Transitions**:
  - Created when extraction begins with provisional metrics
  - Updated upon completion with final guardrail status

## AnalystAuditEvent (extension)
- **Purpose**: Capture cross-workspace related incident access for compliance.
- **Key Fields**:
  - `id` (UUID, primary key)
  - `analyst_id` (UUID)
  - `source_workspace_id` (UUID)
  - `related_workspace_id` (UUID)
  - `session_id` (UUID of currently viewed job)
  - `related_session_id` (UUID of matched incident)
  - `timestamp` (TIMESTAMP WITH TIME ZONE)
  - `action` (ENUM: `viewed_related_incident`)
- **Relationships**:
  - `analyst_id` references users table
  - `source_workspace_id` & `related_workspace_id` reference tenant/workspace table
- **Validation Rules**:
  - `related_workspace_id` must differ from `source_workspace_id` for cross-workspace events
  - Records only inserted when visibility_scope = `multi_tenant`

## Derived Views
- **RelatedIncidentView**: materialized view joining `IncidentFingerprint` with job summaries and detection results for fast analyst queries. Refresh triggered post-ingestion job completion.

## Data Retention & Partitioning
- Incident fingerprints and detection results partitioned by `tenant_id` (or workspace) to maintain RLS policies.
- Archive audit records retained for 90 days (configurable) to support forensic review without bloating primary tables.
