# Feature Specification: Unified Ingestion Intelligence Enhancements

**Feature Branch**: `[002-unified-ingestion-enhancements]`  
**Created**: 2025-10-17  
**Status**: Draft  
**Input**: User description: "Unified ingestion enhancements for related incidents discovery, platform-specific parsing, and expanded archive handling"

## Clarifications

### Session 2025-10-17

- Q: Should related incident results stay within the originating customer workspace? → A: Allow cross-workspace results for all user roles.

## User Scenarios & Testing *(mandatory)*

<!--
  IMPORTANT: User stories should be PRIORITIZED as user journeys ordered by importance.
  Each user story/journey must be INDEPENDENTLY TESTABLE - meaning if you implement just ONE of them,
  you should still have a viable MVP (Minimum Viable Product) that delivers value.
  
  Assign priorities (P1, P2, P3, etc.) to each story, where P1 is the most critical.
  Think of each story as a standalone slice of functionality that can be:
  - Developed independently
  - Tested independently
  - Deployed independently
  - Demonstrated to users independently
-->

### User Story 1 - Analyst sees related incidents during RCA review (Priority: P1)

Operations analysts need immediate context on whether a new incident resembles past investigations while reviewing an RCA session, even when the most relevant precedent lives in a different customer workspace they have access to.

**Why this priority**: Surfacing historical precedents directly in the workflow reduces time-to-mitigation on the highest-value analyses.

**Independent Test**: Trigger a completed RCA session and confirm the analyst can retrieve, review, and act on related incidents without other feature work.

**Acceptance Scenarios**:

1. **Given** an incident analysis has completed, **When** the analyst opens the session detail, **Then** the system presents a ranked list of similar past incidents including summary context and relevance score, regardless of which workspace originally hosted the precedent.
2. **Given** the analyst adjusts relevance filters, **When** the filter is applied, **Then** the related list updates within the session view while maintaining at least one result when available.

---

### User Story 2 - Job ingestion indexes incident fingerprints (Priority: P1)

The ingestion pipeline must create searchable fingerprints for newly processed RCAs so they appear in similarity lookups.

**Why this priority**: Without timely indexing, analysts cannot rely on related incident discovery for current work.

**Independent Test**: Complete a single ingestion job and verify a similarity search immediately returns the fresh analysis by session identifier.

**Acceptance Scenarios**:

1. **Given** a job completes successfully, **When** the pipeline stores fingerprint data, **Then** the incident is queryable through the search endpoint within agreed latency thresholds.
2. **Given** the incident lacks embeddable content, **When** the job finalizes, **Then** the system records a telemetry warning and marks the fingerprint as unavailable while keeping the job otherwise successful.

---

### User Story 3 - Platform-specific log parsing enriches insights (Priority: P2)

Ingestion should detect supported RPA platforms and extract platform entities that inform downstream summaries.

**Why this priority**: Platform context boosts RCA accuracy and makes downstream automation recommendations actionable.

**Independent Test**: Upload a log bundle from each supported platform and confirm the pipeline stores detected platform, confidence, and extracted entities without requiring other feature delivery.

**Acceptance Scenarios**:

1. **Given** a supported platform log is ingested, **When** detection confidence meets the rollout threshold, **Then** the pipeline records the platform, extracted entities, and exposes them in job metadata.
2. **Given** detection confidence falls below the threshold, **When** ingestion completes, **Then** the job continues via the generic pipeline while telemetry captures the low-confidence outcome.

---

### User Story 4 - Safe archive handling expands file support (Priority: P3)

File submitters need to upload compressed artifacts in additional formats without risking infrastructure stability.

**Why this priority**: Supporting tar- and bzip-based formats unlocks more customer data sources while protecting infrastructure from decompression abuse.

**Independent Test**: Process an archive in each new format and verify members are validated, extraction completes or halts safely, and job metadata reflects the outcome.

**Acceptance Scenarios**:

1. **Given** a `.tar.gz` archive contains supported files, **When** the user uploads it, **Then** extraction succeeds within existing resource limits and the ingest job proceeds automatically.
2. **Given** an archive exceeds decompression ratio safeguards, **When** extraction begins, **Then** the system aborts extraction, records the warning, and marks the job for operator review.

### Edge Cases

- Multi-platform log bundles contain mixed sources; the system must either identify the dominant platform or default to generic processing with clear telemetry.
- Similarity search returns no matches above the confidence threshold; analysts should see a clear "no related incidents" state with guidance to adjust filters.
- Archive extraction encounters unsupported member types or nested archives; extraction should stop before processing unknown types and surface guidance in job metadata.
- Uploads exceed time or size guards; ingestion should timeout gracefully, notify telemetry, and avoid leaving partial data in storage.
- Telemetry pipeline is unavailable; feature flags must prevent blocking analyst workflows while logging deferred events for later replay.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The ingestion pipeline MUST generate and store a similarity fingerprint for every completed RCA session, including metadata required for future matching.
- **FR-002**: The system MUST provide an endpoint for analysts to search incidents by textual context, returning ranked related sessions with relevance scores.
- **FR-003**: The analyst user interface MUST display related incidents within the session detail view and allow filtering by relevance threshold or platform.
- **FR-004**: The pipeline MUST record when fingerprint creation is skipped or degraded and surface the status in job metadata and telemetry.
- **FR-005**: The ingestion flow MUST detect supported RPA platforms (Blue Prism, UiPath, Appian, Automation Anywhere, Pega) and assign a confidence score to each detection attempt.
- **FR-006**: When detection confidence meets the rollout threshold, the system MUST run the platform-specific parser and persist extracted entities in existing job storage.
- **FR-007**: When detection confidence is below threshold, the job MUST follow the generic parsing path while preserving raw artifacts for future review.
- **FR-008**: Detection and parser outcomes MUST be emitted to existing telemetry and metrics collectors, including confidence, success/failure, and feature flag status.
- **FR-009**: Archive extraction MUST support `.bz2`, `.xz`, `.tar.gz`, `.tar.bz2`, and `.tar.xz` formats while reusing the current resource guardrails.
- **FR-010**: The system MUST block extraction when decompression ratio or member count safeguards are exceeded and record the event for operator visibility.
- **FR-011**: Validation utilities MUST confirm that extracted members meet supported file-type rules across all archive formats before ingestion continues.
- **FR-012**: Feature flags MUST allow progressive rollout of platform detection/parsing and expanded archive handling without code redeployments.

### Key Entities *(include if feature involves data)*

- **Incident Fingerprint**: Represents the searchable signature of a completed RCA session, including session identifier, summary descriptors, embedding reference, and relevance status.
- **Platform Detection Result**: Captures detected platform name, confidence score, parser flag state, extracted entity references, and telemetry correlation IDs.
- **Archive Extraction Audit**: Records archive source details, format, extraction outcome (success, partial, blocked), safeguard metrics, and associated job identifiers.

### Platform Detection Specification

**Supported Platforms**: Blue Prism, UiPath, Appian, Automation Anywhere, Pega

**Detection Methodology**:

Each platform is identified by analyzing log file characteristics:

| Platform | Primary Indicators | Confidence Weight | Example Patterns |
|----------|-------------------|-------------------|------------------|
| Blue Prism | File naming (`*.log`), XML structure, `<process>` tags | 0.4 file + 0.6 content | `<process name="...">`, `<stage name="...">` |
| UiPath | `.xaml` workflow files, `UiPath.` namespaces | 0.3 file + 0.7 content | `<Activity x:TypeArguments="...">`, `UiPath.Core.Activities` |
| Appian | JSON-structured process logs, `appian-` prefixes | 0.2 file + 0.8 content | `"processModel":`, `"taskName":`, `"appian-process-id"` |
| Automation Anywhere | `.atmx` task files, `Automation Anywhere` headers | 0.5 file + 0.5 content | `<AutomationAnywhere>`, `<TaskBot>` |
| Pega | `.pega` extension, `px-` class prefixes | 0.3 file + 0.7 content | `"pyClassName": "px...`, `"pzInsKey":` |

**Confidence Calculation**:
- Base score = sum(indicator_weight × match_success)
- Bonus: +0.1 if multiple indicators match
- Penalty: -0.2 if conflicting indicators detected
- Final confidence = clamp(base_score + bonus - penalty, 0.0, 1.0)

**Rollout Threshold**: `0.70` (configurable via `platform_detection.confidence_threshold`)

**Decision Logic**:
- confidence ≥ threshold → Run platform-specific parser
- confidence < threshold → Use generic pipeline, log detection result for model improvement

**See Also**: `contracts/platform-detection-api.md` for parser interface contracts

### Assumptions

- Similarity scoring hides matches below a configurable confidence threshold but allows analysts to lower the threshold manually when needed.
- Low-confidence platform detections default to the generic ingestion pipeline while storing raw artifacts for future upgrades.
- Archive ingestion continues to extract only the first supported file per job unless ops explicitly expands scope during rollout.
- Analysts with access to multiple customer workspaces can see related incidents across those workspaces without additional permission tiers.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 90% of completed RCA sessions generate searchable fingerprints within 2 minutes of job completion.
- **SC-002**: Analysts locate at least one relevant historical incident for 80% of sessions where a matching fingerprint exists.
- **SC-003**: At least 85% of ingested log bundles from supported platforms yield extracted entities stored alongside the job within the pilot period.
- **SC-004**: Less than 1% of archive ingestion attempts fail due to extraction safeguards while zero infrastructure incidents are attributed to decompression abuse during rollout.
- **SC-005**: Analyst satisfaction surveys report a 20% increase in perceived context completeness during RCA reviews after feature launch.

## Testing Requirements *(mandatory per Constitution V)*

### Unit Test Coverage

All new code paths MUST include dedicated unit tests covering:

1. **Validation Rules** (FR-011):
   - Test supported file type validation for each archive format (.bz2, .xz, .tar.gz, .tar.bz2, .tar.xz)
   - Test rejection of unsupported member types
   - Test nested archive detection and handling

2. **Safeguard Behavior** (FR-010):
   - Test decompression ratio enforcement (threshold: configured in `core/config.py`)
   - Test member count limit enforcement (threshold: configured in `core/config.py`)
   - Test extraction abort and audit event emission

3. **Platform Detection Logic** (FR-005):
   - Test confidence score calculation for each supported platform
   - Test threshold-based parser routing
   - Test generic fallback when confidence < threshold

4. **Fingerprint Generation** (FR-001):
   - Test successful fingerprint creation from completed job
   - Test degraded fingerprint scenarios (missing embeddings)
   - Test fingerprint generation failure and retry logic

### Integration Test Coverage

- End-to-end ingestion flow for each archive format with safeguard validation
- Platform detection → parser execution → entity persistence flow
- Related incident search across workspaces with filtering
- Feature flag toggling without service restart

### Test Execution

- All tests MUST pass before merge to feature branch
- Coverage target: >80% for new code paths
- Test results documented in `docs/reports/unified-ingestion-validation.md`

## Implementation Status

✅ **COMPLETED** - All tasks delivered successfully. See [Implementation Summary](../../docs/UNIFIED_INGESTION_COMPLETE.md) for full details.
