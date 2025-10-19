# Unified Ingestion Data Model

This document captures the schema additions that enable cross-workspace related incidents, platform detection outcomes, and archive extraction guardrails. Each section summarises the table definition, enforced constraints, and how the data is produced.

## `incident_fingerprints`

- **Purpose**: Stores the searchable signature for each completed RCA job.
- **Primary Key**: `id UUID`
- **Key Columns**:
  - `session_id UUID` – one-to-one with `jobs.id`; cascade deletes follow the job lifecycle.
  - `tenant_id UUID` – partitioning key for row-level security rules.
  - `embedding_vector vector(settings.VECTOR_DIMENSION)` – required when `fingerprint_status = 'available'`.
  - `summary_text TEXT` – analyst-facing synopsis (truncated to 4096 characters).
  - `relevance_threshold REAL` – baseline similarity threshold used for default queries.
  - `visibility_scope visibility_scope_enum` – `tenant_only` or `multi_tenant`; governs cross-workspace exposure.
  - `fingerprint_status fingerprint_status_enum` – `available`, `degraded`, or `missing`.
  - `safeguard_notes JSONB` – structured hints when fingerprints are suppressed or degraded.
- **Indices & Constraints**:
  - `uq_incident_fingerprints_session` protects the one-to-one mapping with jobs.
  - IVFFlat index on `embedding_vector` for pgvector similarity search (`cosine_distance`).
  - Check constraints ensure summary length, relevance bounds, and vector presence for available fingerprints.
- **Populated By**: Job processor after successful ingestion in Phase 4 task T018, with safeguard metadata from T019.

## `platform_detection_results`

- **Purpose**: Captures per-job platform detection metadata and parser execution outcomes.
- **Primary Key**: `id UUID`
- **Key Columns**:
  - `job_id UUID` – unique foreign key to `jobs.id` (one record per ingestion run).
  - `detected_platform detected_platform_enum` – enumerates supported RPA platforms plus `unknown`.
  - `confidence_score NUMERIC(5,4)` – bounded between 0 and 1.
  - `detection_method TEXT` – e.g., `heuristic`, `ml_model`.
  - `parser_executed BOOLEAN` and `parser_version TEXT` – track downstream parser execution state.
  - `extracted_entities JSONB` – platform-specific artefacts emitted by parsers.
  - `feature_flag_snapshot JSONB` – captured configuration flags at decision time.
  - `created_at TIMESTAMPTZ` – server-side timestamp.
- **Indices & Constraints**:
  - `uq_platform_detection_results_job` enforces one record per job.
  - Additional indices cover lookup by job id, platform type, and creation time.
  - Confidence bounded via `ck_platform_detection_confidence_bounds`.
- **Populated By**: Platform detection pipeline (Phase 5 tasks) once archive extraction completes.

## `archive_extraction_audits`

- **Purpose**: Records guardrail evaluations for expanded archive formats.
- **Primary Key**: `id UUID`
- **Key Columns**:
  - `job_id UUID` – unique foreign key to `jobs.id`.
  - `source_filename TEXT` and `archive_type archive_type_enum` – capture original artefact details.
  - `member_count INT`, `compressed_size_bytes BIGINT`, `estimated_uncompressed_bytes BIGINT` – capacity metrics.
  - `decompression_ratio NUMERIC(10,2)` – expansion ratio, used for guardrail enforcement.
  - `guardrail_status archive_guardrail_status_enum` – `passed`, `blocked_ratio`, `blocked_members`, `timeout`, or `error`.
  - `blocked_reason TEXT` and `partial_members JSONB` – audit trail for blocked extractions.
  - `started_at`, `completed_at TIMESTAMPTZ` – extraction timeline.
- **Indices & Constraints**:
  - `uq_archive_extraction_audits_job` ensures single audit record per job.
  - Check constraints cover positive sizes, member counts, ratio bounds, and blocked-reason requirements.
- **Populated By**: Archive extraction service once guardrails execute (Phase 6 tasks).

## `analyst_audit_events`

- **Purpose**: Supplies compliance logging for cross-workspace related incident access.
- **Primary Key**: `id UUID`
- **Key Columns**:
  - `analyst_id UUID` – authenticated user performing the action.
  - `source_workspace_id UUID` and `related_workspace_id UUID` – identify the viewing and related tenants.
  - `session_id UUID` and `related_session_id UUID` – pair of RCA sessions involved in the audit record.
  - `action analyst_audit_action_enum` – currently only `viewed_related_incident`.
  - `timestamp TIMESTAMPTZ` – server timestamp when the event was recorded.
- **Indices & Constraints**:
  - `ix_analyst_audit_events_analyst_timestamp` supports chronological review per analyst.
  - `ix_analyst_audit_events_session` enables traceability for a given session pair.
  - Constraint `ck_analyst_audit_distinct_workspaces` blocks redundant same-workspace events.
- **Populated By**: Related incident API once visibility scope allows cross-tenant results (Phase 3 task T012).

## Enums Introduced

| Enum | Values | Notes |
| --- | --- | --- |
| `visibility_scope_enum` | `tenant_only`, `multi_tenant` | Aligns with feature flag defaults; multi-tenant requires auditing enabled. |
| `fingerprint_status_enum` | `available`, `degraded`, `missing` | Derived from ingestion outcomes and safeguard checks. |
| `detected_platform_enum` | `blue_prism`, `uipath`, `appian`, `automation_anywhere`, `pega`, `unknown` | Extend as new platforms are onboarded. |
| `archive_type_enum` | `zip`, `gz`, `bz2`, `xz`, `tar_gz`, `tar_bz2`, `tar_xz` | Matches expanded archive support. |
| `archive_guardrail_status_enum` | `passed`, `blocked_ratio`, `blocked_members`, `timeout`, `error` | Distinguishes guardrail failure reasons. |
| `analyst_audit_action_enum` | `viewed_related_incident` | Extensible for future analyst actions. |

## Configuration Tie-Ins

The new tables rely on settings exposed via `core.config.Settings`:

- Feature flags (`RELATED_INCIDENTS_ENABLED`, `PLATFORM_DETECTION_ENABLED`, `ARCHIVE_EXPANDED_FORMATS_ENABLED`).
- Related incident defaults (`RELATED_INCIDENTS_MIN_RELEVANCE`, `RELATED_INCIDENTS_MAX_RESULTS`).
- Platform detection thresholds (`PLATFORM_DETECTION_ROLLOUT_CONFIDENCE`, `PLATFORM_DETECTION_PARSER_TIMEOUT_SECONDS`).
- Archive guardrails (`ARCHIVE_GUARDRAIL_MAX_DECOMPRESSION_RATIO`, `ARCHIVE_GUARDRAIL_MAX_MEMBER_COUNT`).

Keep environment overrides in sync with operational guidance documented in `docs/operations/feature-flags.md`.
