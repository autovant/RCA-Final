---
description: "Task list for unified ingestion intelligence enhancements"
---

# Tasks: Unified Ingestion Intelligence Enhancements

**Input**: Design documents from `/specs/002-unified-ingestion-enhancements/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Tests**: Regression coverage already exists in project; no explicit TDD mandate in spec. Functional verification tasks focus on manual/automated checks outlined in user stories and quickstart.

**Organization**: Tasks grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`
- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: User story the task supports (e.g., US1, US2)
- Include exact file paths in descriptions

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Ensure local environments, feature flags, and telemetry scaffolding are ready for story development.

- [x] T001 [P] [Setup] Verify feature flags `related_incidents`, `platform_detection`, `archive_expanded_formats` exist in `core/config.py` and environment templates; add defaults if missing.
- [x] T001a [Setup] Add Grafana dashboard panel for feature flag adoption metrics in `deploy/ops/dashboards/telemetry/feature-flags.json` tracking flag state and usage rates.
- [x] T002 [P] [Setup] Review `start-dev.ps1` / docker compose to confirm Postgres (pgvector) and Redis services provisioned; document any adjustments in `docs/operations/local-dev.md`.
- [x] T003 [Setup] Update `docs/operations/feature-flags.md` with rollout notes for new flags and cross-workspace visibility auditing.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core schema and telemetry groundwork required before story implementation.

- [x] T004 [Foundational] Extend Alembic migration in `alembic/versions/` to add columns/tables for `IncidentFingerprint.visibility_scope`, `PlatformDetectionResult`, `ArchiveExtractionAudit`, `AnalystAuditEvent` per data-model.md.
- [x] T005 [Foundational] Update SQLAlchemy models in `core/jobs/models.py`, `core/files/models.py`, `core/metrics/models.py` (as appropriate) to match new schema fields.
- [x] T006 [Foundational] Wire structured logging keys for archive safeguards and platform detection in `core/logging.py`.
- [x] T007 [Foundational] Add Prometheus metric definitions for detection outcomes and archive guardrail statuses in `core/metrics/collectors.py`.
- [x] T008 [Foundational] Refresh Pydantic settings / config validation for new feature flags and thresholds in `core/config.py`.
- [x] T009 [Foundational] Document new schema + metrics in `docs/reference/data-model.md` and `docs/reference/metrics.md`.

**Checkpoint**: Database schema and telemetry ready; user story work can begin.

---

## Phase 3: User Story 1 - Analyst sees related incidents during RCA review (Priority: P1) 🎯 MVP

**Goal**: Display cross-workspace related incidents within session detail, including filtering and auditing.

**Independent Test**: After completing tasks, follow Quickstart sections 1, 2, 4, and 5 to confirm related incidents render with adjustable filters and audit events logged.

### Implementation

- [x] T010 [US1] Implement Postgres query service for similarity search in `core/jobs/fingerprint_service.py` leveraging pgvector and visibility scope.
- [x] T011 [US1] Update API endpoint `/api/v1/incidents/{session_id}/related` and `/incidents/search` in `apps/api/routes/incidents.py` to use new service, scope parameter, and audit token.
- [x] T012 [US1] Add auditing hook to record cross-workspace views in `core/security/audit.py` (insert `AnalystAuditEvent`).
- [x] T013 [US1] Enhance analytics telemetry in `core/metrics/collectors.py` for related incident responses.
- [x] T014 [P] [US1] Update UI related incidents panel in `ui/app/(rca)/sessions/[id]/related-incidents.tsx` with filtering controls and audit token propagation.
- [x] T015 [P] [US1] Adjust UI API client in `ui/lib/api/related-incidents.ts` to accept `scope`, `platform`, `min_relevance`, and handle audit responses.
- [x] T016 [US1] Extend UI state management/tests in `ui/tests/related-incidents.test.tsx` to cover filter behavior and empty states.
- [x] T017 [US1] Add documentation snippet to `docs/getting-started/analyst-guide.md` describing related incident panel usage and cross-workspace visibility.

**Checkpoint**: Related incidents visible and auditable in UI using existing data.

---

## Phase 4: User Story 2 - Job ingestion indexes incident fingerprints (Priority: P1)

**Goal**: Ensure completed ingestion jobs generate/update fingerprints with guardrail reporting.

**Independent Test**: Run ingestion pipeline via Quickstart step 3; confirm new job creates fingerprint, respects guardrails, and search API returns result immediately.

### Implementation

- [x] T018 [US2] Integrate fingerprint creation workflow in `core/jobs/processor.py` post-job completion with visibility scope logic.
- [x] T019 [US2] Persist safeguard notes and statuses to `IncidentFingerprint` when fingerprints are degraded or missing in `core/jobs/fingerprint_service.py`.
- [x] T019a [US2] Implement retry logic for fingerprint generation failures in `core/jobs/fingerprint_service.py` with exponential backoff (3 attempts, 2s/4s/8s delays) per Constitution I.
- [x] T020 [US2] Emit job metadata updates and telemetry for fingerprint status in `apps/worker/events.py` or equivalent event publisher.
- [x] T021 [P] [US2] Add FastAPI admin endpoint or job metadata surface in `apps/api/routes/jobs.py` exposing fingerprint status for debugging.
- [x] T022 [P] [US2] Update unit/integration tests in `tests/test_job_processor.py` and `tests/integration/test_incident_search.py` to cover new fingerprint lifecycle.
- [x] T023 [US2] Update operational docs `docs/operations/job-processor.md` with indexing behavior and troubleshooting steps.

**Checkpoint**: New ingestion runs generate searchable fingerprints with status telemetry.

---

## Phase 5: User Story 3 - Platform-specific log parsing enriches insights (Priority: P2)

**Goal**: Detect RPA platforms during ingestion and extract platform-specific entities with telemetry.

**Independent Test**: Ingest log bundles for each platform from sample data; verify detection confidence, parser outcomes, and extracted entities recorded.

### Implementation

- [x] T024 [US3] Implement platform detection orchestration in `core/files/detection.py`, applying rollout threshold and feature flags.
- [x] T025 [US3] Add parser execution path in `core/jobs/processor.py` to call platform-specific parsers when confidence met.
- [x] T026 [US3] Persist detection results and extracted entities to `PlatformDetectionResult` model in `core/jobs/models.py` and associated repositories.
- [x] T027 [P] [US3] Implement/extend platform parser modules under `core/files/platforms/` for Blue Prism, UiPath, Appian, Automation Anywhere, Pega with entity extraction outputs.
- [x] T028 [US3] Emit telemetry metrics and structured logs for detection/parsing outcomes in `core/metrics/collectors.py` and `core/logging.py`.
- [x] T029 [P] [US3] Update job metadata response and UI components (e.g., `ui/app/(rca)/sessions/[id]/metadata.tsx`) to display platform information and parser entities.
- [x] T030 [US3] Refresh documentation `docs/reference/platform-detection.md` outlining detection confidence thresholds and parser behavior.

**Checkpoint**: ✅ Platform detection outputs enrich job metadata and appear in UI.

---

## Phase 6: User Story 4 - Safe archive handling expands file support (Priority: P3)

**Goal**: Support additional archive formats with guardrails preventing decompression abuse.

**Independent Test**: Upload archives in each new format; verify supported members extracted, safeguard failures logged, and jobs marked for review when blocked.

### Implementation

- [x] T031 [US4] Extend archive extraction utility `core/files/extraction.py` to handle `.bz2`, `.xz`, `.tar.gz`, `.tar.bz2`, `.tar.xz` with streaming.
- [x] T032 [US4] Implement safeguard evaluation (decompression ratio, member count) for tar-based archives in `core/files/validators.py`.
- [x] T033 [US4] Ensure validation utilities enforce supported member checks across formats in `core/files/validation.py` and update associated unit tests `tests/test_file_service.py`.
- [x] T034 [US4] Record extraction audit events in `ArchiveExtractionAudit` via `core/files/audit.py` and surface warnings in job metadata.
- [x] T035 [P] [US4] Update CLI tooling `scripts/pipeline/ingest_archive.py` to recognize new formats and present warnings when guardrails trigger.
- [x] T036 [US4] Document format support and troubleshooting in `docs/operations/archive-handling.md` and `docs/troubleshooting/archive-issues.md`.

**Checkpoint**: ✅ Expanded archive formats processed safely with guardrail reporting.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Unify testing, performance, and documentation post-story delivery.

- [x] T037 [P] [Polish] Consolidate new Prometheus metrics into dashboards; update Grafana json in `deploy/ops/dashboards/telemetry/unified-ingestion.json` and `pipeline-overview.json`.
- [x] T038 [Polish] Run full regression suite (`pytest`, `npm test`) and capture results in `docs/reports/unified-ingestion-validation.md`.
- [x] T039 [Polish] Review structured logging outputs, ensuring sensitive data excluded; adjust `core/logging.py` filters as needed.
- [x] T040 [Polish] Final documentation sweep linking spec, plan, quickstart updates across `docs/index.md`.

**Checkpoint**: ✅ All tasks complete. Project ready for production deployment.

---

## Dependencies & Execution Order

- **Phase 1 → Phase 2**: Setup tasks must complete to ensure environment readiness; Phase 2 blocks all user stories.
- **Phase 2 → Phases 3-6**: Schema and telemetry updates must land before story work begins.
- **User Stories**: US1 (P1) and US2 (P1) can start immediately after Phase 2. US3 (P2) depends on US2 fingerprints for parser outputs. US4 (P3) independent but benefits from Phase 2 guardrail groundwork.
- **Polish**: Runs after selected stories delivered.

### Story Completion Dependencies
- US1 and US2 are parallel P1 priorities; delivering US1 alone constitutes MVP.
- US3 depends on ingestion outputs introduced in US2 (reuse data structures and telemetry).
- US4 independent of other stories but leverages archive audit schema from Phase 2.

### Parallel Opportunities
- Within Phase 1/2: Tasks marked [P] operate on distinct files.
- US1: T014 and T015 (UI updates) can run in parallel once API contract ready.
- US2: T021 and T022 can execute concurrently (admin endpoint vs tests) after T018/T019.
- US3: T027 and T029 handle independent modules (backend parsers vs UI) and can proceed simultaneously.
- US4: T035 (CLI) parallel to backend extraction changes.

## Implementation Strategy

### MVP Focus
1. Complete Phases 1-2.
2. Deliver US1 to provide analyst-facing related incidents (core business value).
3. Validate via Quickstart (steps 1-5) before expanding scope.

### Incremental Delivery
- After MVP, prioritize US2 to keep index fresh, then US3 for richer insights, and finally US4 for broader archive support.

### Parallel Team Approach
- Developer A: Schema & US1 backend.
- Developer B: US1 UI and docs.
- Developer C: US2 ingestion enhancements.
- Developer D: US3 parsers and telemetry.
- Rotate to US4 and Polish as earlier stories complete.
