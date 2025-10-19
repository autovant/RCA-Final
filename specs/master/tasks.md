---
description: "Task list for Advanced ITSM Integration Hardening implementation"
---

# Tasks: Advanced ITSM Integration Hardening

**Input**: Design documents from `/specs/master/`
**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅, contracts/ ✅

**Tests**: This feature implementation does NOT include test tasks as testing was not explicitly requested in the specification.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`
- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3, US4)
- Exact file paths included in descriptions

---

## Phase 1: Setup (Shared Infrastructure) ✅ COMPLETED

**Purpose**: Configuration and base infrastructure already in place

**Status**: Configuration exists in `config/itsm_config.json` with all required sections:
- ✅ `retry_policy` with exponential backoff settings
- ✅ `timeout` configuration (connection, read, total)
- ✅ `templates.servicenow` and `templates.jira` with 4 initial templates
- ✅ `field_mapping` with validation rules for both platforms

---

## Phase 2: Foundational (Blocking Prerequisites) ✅ COMPLETED

**Purpose**: Core retry, validation, and template infrastructure that ALL user stories depend on

**⚠️ CRITICAL**: These tasks are complete - foundational infrastructure ready for user story enhancements

**Completed Tasks**:
- ✅ T001 [US1] Created `RetryPolicy` and `TimeoutConfig` dataclasses in `core/tickets/clients.py`
- ✅ T002 [US1] Implemented retry logic with exponential backoff in `ServiceNowClient._request()` method
- ✅ T003 [US1] Implemented retry logic with exponential backoff in `JiraClient._request()` method
- ✅ T004 [US1] Integrated timeout configuration into both ITSM clients
- ✅ T005 [US2] Created `core/tickets/validation.py` with `TicketPayloadValidator` class
- ✅ T006 [US2] Integrated validation into `TicketService.create_ticket()` method
- ✅ T007 [US3] Created `core/tickets/template_service.py` with `TicketTemplateService` class
- ✅ T008 [US3] Added `create_from_template()` method to `TicketService` class

**Checkpoint**: ✅ Foundation complete - user story enhancement tasks can now begin

---

## Phase 3: User Story 1 - Automatic Retry on Transient Failures (Priority: P1) ✅ COMPLETED

**Goal**: ServiceNow/Jira clients automatically retry on transient failures with exponential backoff

**User Story**: 
> As a platform operator, I want ITSM ticket creation to automatically retry on transient failures, 
> so that temporary network issues don't result in lost tickets.

**Acceptance Criteria**:
- ✅ ServiceNow and Jira clients retry on 429, 500, 502, 503, 504 status codes
- ✅ Exponential backoff with configurable multiplier (default: 2x)
- ✅ Maximum 3 retries by default (configurable)
- ✅ Retry attempts and delays captured in ticket metadata
- ✅ Non-retryable errors (4xx except 429) fail immediately

**Independent Test**: Create ticket during simulated transient failure (503), verify automatic retry with exponential delays

**Status**: ✅ IMPLEMENTATION COMPLETE

**Completed Implementation**:
- ✅ T001 [US1] Created `RetryPolicy` dataclass in `core/tickets/clients.py`
  - Loads from `itsm_config.json["retry_policy"]`
  - Fields: max_retries, retry_delay_seconds, exponential_backoff, backoff_multiplier, max_retry_delay_seconds, retryable_status_codes
- ✅ T002 [US1] Created `TimeoutConfig` dataclass in `core/tickets/clients.py`
  - Loads from `itsm_config.json["timeout"]`
  - Converts to `httpx.Timeout` object
- ✅ T003 [US1] Implemented retry loop in `ServiceNowClient._request()` method
  - Exponential backoff calculation: `delay = min(retry_delay * (backoff_multiplier ** attempt), max_retry_delay)`
  - Captures retry_metadata: retry_attempts, retry_delays, retryable_errors, final_error
  - Returns tuple: (response, retry_metadata)
- ✅ T004 [US1] Implemented retry loop in `JiraClient._request()` method
  - Matching implementation to ServiceNowClient
  - Same retry_metadata structure
- ✅ T005 [US1] Updated `ServiceNowClient.create_incident()` to unpack tuple and store retry_metadata
- ✅ T006 [US1] Updated `ServiceNowClient.fetch_incident()` to unpack tuple
- ✅ T007 [US1] Updated `JiraClient.create_issue()` to unpack tuple and store retry_metadata
- ✅ T008 [US1] Updated `JiraClient.fetch_issue()` to unpack tuple
- ✅ T009 [US1] Enhanced `TicketCreationResult` in `core/tickets/service.py` to include retry_metadata in metadata dict

**Checkpoint**: ✅ User Story 1 fully functional - retry logic operational for all ITSM operations

---

## Phase 4: User Story 2 - Pre-Flight Payload Validation (Priority: P1) ✅ COMPLETED

**Goal**: Validate ticket payloads against field schemas before transmission to ITSM platforms

**User Story**: 
> As a developer, I want ticket payloads validated against field schemas before transmission, 
> so that I receive clear error messages instead of cryptic API failures.

**Acceptance Criteria**:
- ✅ Validation enforces required fields, max lengths, enum values, regex patterns
- ✅ Validation errors include field name, error code, and descriptive message
- ✅ API responses distinguish validation errors from server errors
- ✅ Validation failures prevent ticket creation and emit structured events

**Independent Test**: Submit invalid payload (missing required field), verify validation error with field details before API call

**Status**: ✅ IMPLEMENTATION COMPLETE

**Completed Implementation**:
- ✅ T010 [US2] Created `ValidationError` dataclass in `core/tickets/validation.py`
  - Fields: field, error_code, message, details
  - Error codes: required_field_missing, max_length_exceeded, invalid_enum_value, pattern_mismatch, invalid_type, invalid_platform
- ✅ T011 [US2] Created `ValidationResult` dataclass in `core/tickets/validation.py`
  - Fields: valid (bool), errors (List[ValidationError])
  - Method: error_dict() for grouping errors by field
- ✅ T012 [US2] Implemented `TicketPayloadValidator` class in `core/tickets/validation.py`
  - Loads field_mapping from `itsm_config.json`
  - Loads validation.rules from `itsm_config.json`
  - Method: validate() performs required, max_length, enum, pattern validation
  - Returns ValidationResult with accumulated errors
- ✅ T013 [US2] Created `validate_ticket_payload()` convenience function
- ✅ T014 [US2] Integrated validation into `TicketService.create_ticket()` method
  - Calls validate_ticket_payload() before client._request()
  - If validation fails: forces dry_run=True, stores validation_errors in metadata
  - Validation errors accessible in TicketCreationResult

**Checkpoint**: ✅ User Story 2 fully functional - payload validation operational before all ticket creation

---

## Phase 5: User Story 3 - Template-Based Ticket Creation (Priority: P2) ✅ COMPLETED (Backend + API)

**Goal**: Enable reusable ticket templates with variable substitution for consistent ticket formatting

**User Story**: 
> As an automation engineer, I want to create tickets from reusable templates with variable substitution, 
> so that tickets have consistent formatting and required fields.

**Acceptance Criteria**:
- ✅ Templates defined in `itsm_config.json` with `{variable}` placeholders
- ✅ API endpoint to list available templates by platform (IMPLEMENTED)
- ✅ API endpoint to create ticket from template with variable values (IMPLEMENTED)
- ✅ Template rendering errors provide missing variable details
- ⬜ UI provides template dropdown with field preview (READY - API endpoints available)

**Independent Test**: Create ticket from "rca_incident" template with job variables, verify field substitution

**Status**: ✅ BACKEND + API COMPLETE, UI READY TO IMPLEMENT

**Completed Implementation**:
- ✅ T015 [US3] Created `TicketTemplate` dataclass in `core/tickets/template_service.py`
  - Fields: name, platform, fields, required_variables
- ✅ T016 [US3] Implemented `TicketTemplateService` class in `core/tickets/template_service.py`
  - Loads templates from `itsm_config.json["templates"]`
  - Caches templates in memory
  - Method: list_templates(platform) returns template metadata
  - Method: get_template(platform, name) retrieves specific template
  - Method: render_template(platform, name, variables) performs recursive substitution
  - Private method: _extract_variables() detects {variable} placeholders
- ✅ T017 [US3] Added `list_templates()` method to `TicketService` class
  - Delegates to TicketTemplateService
- ✅ T018 [US3] Implemented `create_from_template()` method in `TicketService` class
  - Loads job context for auto-injected variables
  - Merges job context with user-provided variables
  - Renders template with merged variables
  - Validates rendered payload
  - Creates ticket via create_ticket()
  - Stores template_name in metadata

**Completed Implementation**:
- ✅ T019 [P] [US3] Created Pydantic models for template API in `apps/api/routers/tickets.py`
  - TemplateMetadataResponse model (name, platform, description, required_variables, field_count)
  - TemplateListResponse model (templates list, count)
  - CreateFromTemplateRequest model (job_id, platform, template_name, variables, profile_name, dry_run)
  - CreateFromTemplateResponse model (extends TicketResponse with template_name)
- ✅ T020 [US3] Implemented GET `/api/v1/tickets/templates` endpoint in `apps/api/routers/tickets.py`
  - Query param: platform (optional, enum: servicenow|jira)
  - Calls TicketService.list_templates()
  - Returns TemplateListResponse with template metadata
  - Error handling for invalid platform (400) and internal errors (500)
- ✅ T021 [US3] Implemented POST `/api/v1/tickets/from-template` endpoint in `apps/api/routers/tickets.py`
  - Request body: CreateFromTemplateRequest
  - Validates job exists (404 if not found)
  - Calls TicketService.create_from_template()
  - Returns CreateFromTemplateResponse with ticket details
  - Error handling for: template_not_found (404), validation_failed (400), internal errors (500)
  - Proper exception-to-HTTP status code mapping

**Checkpoint**: ✅ Backend complete, API endpoints implemented - UI development can now proceed

---

## Phase 6: User Story 4 - ITSM Operations Metrics (Priority: P2) ⬜ NOT STARTED

**Goal**: Expose Prometheus metrics for all ITSM operations to enable monitoring and alerting

**User Story**: 
> As an SRE, I want Prometheus metrics for ticket operations, 
> so that I can monitor integration health and create alerts.

**Acceptance Criteria**:
- ⬜ Metrics for: ticket creation (total, duration), retry attempts, validation errors, template rendering errors
- ⬜ Metrics labeled by: platform, outcome, retry_attempts
- ⬜ Grafana dashboard visualizes throughput, error rates, SLA compliance
- ⬜ Alert rules for sustained high error rates

**Independent Test**: Create tickets via API, query /metrics endpoint, verify counter/histogram values

**Status**: ⬜ NOT STARTED

### Completed Implementation for User Story 4 (Metrics Instrumentation)

- ✅ T022 [P] [US4] Imported Prometheus metrics in `core/tickets/service.py`
  - Imported: `from prometheus_client import Counter, Histogram`
  - Defined module-level metrics:
    - `itsm_ticket_creation_total` = Counter with labels: platform, outcome
    - `itsm_ticket_creation_duration_seconds` = Histogram with labels: platform, outcome (buckets: 0.1-60s)
    - `itsm_validation_errors_total` = Counter with labels: platform, field
    - `itsm_template_rendering_errors_total` = Counter with labels: template_name
- ✅ T023 [P] [US4] Imported Prometheus metrics in `core/tickets/clients.py`
  - Imported: `from prometheus_client import Counter`
  - Defined module-level metrics:
    - `itsm_ticket_retry_attempts_total` = Counter with labels: platform
- ✅ T024 [US4] Instrumented `TicketService.create_ticket()` method
  - Added timer at start of method (`start_time = time.time()`)
  - Increments `itsm_ticket_creation_total{platform, outcome}` on completion
  - Observes duration in `itsm_ticket_creation_duration_seconds{platform, outcome}`
  - Increments `itsm_validation_errors_total{platform, field}` for each validation error
  - Handles both success and failure outcomes
- ✅ T025 [US4] Instrumented `TicketService.create_from_template()` method
  - Increments `itsm_template_rendering_errors_total{template_name}` on TemplateRenderError
  - Delegates ticket creation metrics to create_ticket()
- ✅ T026 [US4] Instrumented ServiceNow client retry logic
  - Increments `itsm_ticket_retry_attempts_total{platform="servicenow"}` for each retry attempt
- ✅ T027 [US4] Instrumented Jira client retry logic
  - Increments `itsm_ticket_retry_attempts_total{platform="jira"}` for each retry attempt

### Completed Implementation for User Story 4 (Dashboard & Alerts)
- ✅ T028 [US4] Created Grafana dashboard JSON in `deploy/docker/config/grafana/dashboards/itsm_analytics.json`
  - Panel 1: Ticket creation rate by platform (line chart with success/failure breakdown)
  - Panel 2: Ticket creation duration percentiles - p50, p95, p99 (smooth line chart with thresholds)
  - Panel 3: Error rate percentage by platform (area chart with color-coded thresholds)
  - Panel 4: Retry attempts over time by platform (stacked bar chart)
  - Panel 5: Top 10 validation errors by field (donut chart)
  - Panel 6: Template rendering errors by template (bar chart)
  - Panel 7: ITSM operations summary (gauge panel with 5 key metrics)
  - Auto-refresh: 10 seconds, Time range: Last 1 hour
- ✅ T029 [US4] Created Prometheus alert rules in `deploy/docker/config/alert_rules.yml`
  - Alert: HighITSMErrorRate (>5% errors over 5min, severity: warning)
  - Alert: CriticalITSMErrorRate (>25% errors over 2min, severity: critical)
  - Alert: ExcessiveITSMRetries (>50 retries/min, severity: warning)
  - Alert: ValidationFailureSpike (>10 errors/min, severity: warning)
  - Alert: TemplateRenderingFailures (any errors, severity: warning)
  - Alert: SlowITSMTicketCreation (p95 >5s, severity: warning)
  - Alert: NoITSMActivity (no tickets for 30min, severity: info)
  - All alerts include runbook annotations

### Completed Implementation for User Story 4 (SLA Tracking)
- ✅ T030 [P] [US4] Added SLA tracking fields to `Ticket` model in `core/db/models.py`
  - Added columns: acknowledged_at (DateTime, nullable), resolved_at (DateTime, nullable)
  - Added columns: time_to_acknowledge (Integer, nullable, seconds), time_to_resolve (Integer, nullable, seconds)
  - Updated to_dict() method to include SLA fields
  - Migration: Created Alembic migration 70a4e9f6d8c2_add_sla_tracking_to_tickets.py
- ✅ T031 [US4] Updated `TicketService._refresh_ticket_batch()` to compute SLA metrics
  - Detects status transitions to "In Progress", "Assigned", "Acknowledged" -> sets acknowledged_at
  - Detects status transitions to "Resolved", "Closed", "Done", "Completed" -> sets resolved_at
  - Computes time_to_acknowledge = (acknowledged_at - created_at).total_seconds()
  - Computes time_to_resolve = (resolved_at - created_at).total_seconds()
  - Updates database with SLA fields
- ✅ T032 [P] [US4] Added SLA metrics to Prometheus instrumentation
  - New metric: `itsm_ticket_time_to_acknowledge_seconds` Histogram by platform with buckets [1m to 1d]
  - New metric: `itsm_ticket_time_to_resolve_seconds` Histogram by platform with buckets [5m to 1w]
  - Observes values in _refresh_ticket_batch() when SLA fields are computed

**Checkpoint**: ✅ User Story 4 COMPLETE - All metrics, dashboard, alerts, and SLA tracking implemented

---

## Phase 7: User Story 3 (UI) - Template Selection Interface (Priority: P3) ✅ COMPLETE

**Goal**: Provide React UI for template selection and ticket creation with preview

**Prerequisites**: Phase 5 API endpoints (T019-T021) must be complete ✅

**Status**: ✅ COMPLETE - All UI components implemented with template support

### Completed Implementation for User Story 3 UI

- ✅ T033 [P] [US3] Updated TypeScript types in `ui/src/types/tickets.ts`
  - Added `TemplateMetadata` interface (name, platform, description, required_variables, field_count)
  - Added `TemplateListResponse` interface (templates[], count)
  - Added `CreateFromTemplateRequest` interface (job_id, platform, template_name, variables, profile_name, dry_run)
  - Added `CreateFromTemplateResponse` interface extending Ticket with template_name
- ✅ T034 [US3] Created template store in `ui/src/store/ticketStore.ts`
  - Added state: templates[], selectedTemplate, templatesLoading
  - Added action: fetchTemplates(platform?) with error handling and toast notifications
  - Added action: selectTemplate(template) to set selected template
  - Added action: clearTemplate() to reset template selection
  - Created `ui/src/lib/api/tickets.ts` with getTemplates() and createFromTemplate() methods
- ✅ T035 [US3] Updated `TicketCreationForm.tsx` component in `ui/src/components/tickets/`
  - Added "Use Template" toggle with checkbox
  - Added template dropdown populated from API (filtered by platform)
  - Template dropdown shows template name and field count
  - Added template variables section with dynamic inputs for required_variables
  - Updated handleSubmit to call createFromTemplate() when template selected
  - Conditional rendering: show manual fields OR template fields (not both)
  - Clear validation errors when switching between manual/template modes
- ✅ T036 [US3] Created template preview component `TemplatePreview.tsx` in `ui/src/components/tickets/`
  - Displays template name, platform badge, and field count
  - Shows template description if available
  - Lists all required_variables with status indicators (CheckCircle/AlertCircle)
  - Shows variable values with truncation for long text (>30 chars)
  - Real-time completion status: "Ready" (green) vs "X missing" (amber)
  - Summary panel explaining field count and completion status
  - Exported via index.ts for easy imports
- ✅ T037 [US3] Updated `TicketCreationForm.tsx` validation to show inline errors
  - Added validationErrors state (Record<string, string>)
  - Extract validation errors from API error response (validation_errors array)
  - Display inline error messages below each field with AlertCircle icon
  - Red border styling for invalid fields (border-red-300)
  - Clear validation errors when user edits field
  - Works for both manual form fields and template variable inputs
  - Show error_code and message below field

**Checkpoint**: ⬜ User Story 3 UI blocked - needs T019-T021 completion first

---

## Phase 8: Polish & Cross-Cutting Concerns ⬜ NOT STARTED

**Purpose**: Documentation, OpenAPI spec updates, and cross-cutting improvements

- [ ] T038 [P] [POLISH] Update `docs/ITSM_INTEGRATION_GUIDE.md` with new sections:
  - Section: "Retry and Timeout Configuration" (how to tune retry_policy and timeout)
  - Section: "Payload Validation" (validation rules, error codes, troubleshooting)
  - Section: "Template Usage" (creating templates, variable substitution, best practices)
  - Section: "Metrics and Monitoring" (metrics list, Grafana dashboard, alert rules)
  - Examples for each feature
- [ ] T039 [P] [POLISH] Update `docs/ITSM_QUICKSTART.md` or create if missing
  - Quick start guide for template-based ticket creation
  - cURL examples for new API endpoints
  - Common troubleshooting scenarios (validation failures, template errors, retry exhaustion)
- [ ] T040 [POLISH] Update OpenAPI specification in `apps/api/main.py`
  - Import OpenAPI schema models for template endpoints
  - Add schema definitions for: TemplateMetadataResponse, TemplateListResponse, CreateFromTemplateRequest, CreateFromTemplateResponse, ValidationErrorResponse
  - Add example responses showing retry_metadata and validation errors
  - Update tags and descriptions
- [ ] T041 [P] [POLISH] Create runbook in `docs/ITSM_RUNBOOK.md`
  - Runbook: "High ITSM Error Rate" (check metrics, review logs, verify ITSM platform status)
  - Runbook: "Excessive Retries" (check retry_policy config, investigate ITSM platform degradation)
  - Runbook: "Validation Failures" (review field_mapping, check payload structure)
  - Runbook: "Template Rendering Errors" (verify template syntax, check required variables)

**Checkpoint**: ⬜ Documentation and polish tasks pending

---

## Dependencies

**User Story Completion Order** (based on priorities and dependencies):

```
Phase 1 (Setup) ✅
    ↓
Phase 2 (Foundational) ✅
    ↓
    ├─→ Phase 3 (US1: Retry) ✅ [P1] ← COMPLETE
    ├─→ Phase 4 (US2: Validation) ✅ [P1] ← COMPLETE
    └─→ Phase 5 (US3: Templates Backend) ✅ [P2] ← COMPLETE
         ↓
         Phase 5 (US3: Templates API) ⚠️ [P2] ← IN PROGRESS (T019-T021)
              ↓
              ├─→ Phase 6 (US4: Metrics) ⬜ [P2] ← Can start in parallel
              └─→ Phase 7 (US3: UI) ⬜ [P3] ← BLOCKED on T019-T021
                   ↓
                   Phase 8 (Polish) ⬜ ← Final phase
```

**Critical Path**:
1. ✅ Foundational (T001-T009) - COMPLETE
2. ⚠️ US3 API Endpoints (T019-T021) - CURRENT PRIORITY
3. ⬜ US4 Metrics (T022-T032) - Can start now (parallel)
4. ⬜ US3 UI (T033-T037) - Blocked on step 2
5. ⬜ Polish (T038-T041) - Final

**Parallel Opportunities**:
- After Phase 2 complete: US1, US2, US3 backend could be implemented in parallel (already done ✅)
- After T021 complete: US4 metrics (T022-T032) and US3 UI (T033-T037) can run in parallel
- Polish tasks (T038-T041) are fully parallelizable

---

## Parallel Execution Examples

### Current Sprint: US3 API + US4 Metrics (Recommended)

**Track 1: US3 API Endpoints (Sequential)**
```
T019 → T020 → T021
```

**Track 2: US4 Metrics (Parallel Start)**
```
T022 [P] ─┐
T023 [P] ─┤
T030 [P] ─┴─→ T024 → T025 → T026 → T027 → T031 → T032 → T028 → T029
```

**Estimated Timeline**:
- Track 1: 4-6 hours (API endpoints)
- Track 2: 8-10 hours (metrics instrumentation + dashboard)
- Can execute in parallel after T021

### Final Sprint: UI + Documentation (Parallel)

**Track 1: US3 UI (Sequential with some parallelism)**
```
T033 [P] ─┐
         ├─→ T034 → T035 ─┬─→ T037
T036 ─────┘              └─→ (parallel with T037)
```

**Track 2: Documentation (Fully Parallel)**
```
T038 [P] ─┐
T039 [P] ─┼─→ Done
T041 [P] ─┘
T040 ────────→ Done (depends on T019-T021)
```

---

## Implementation Strategy

### MVP Scope (Already Delivered ✅)
**Deliverable**: Retry logic, validation, and template backend
- ✅ User Story 1: Automatic retry with exponential backoff
- ✅ User Story 2: Pre-flight payload validation
- ✅ User Story 3: Template service backend (no API yet)

**Value**: Core resilience and data quality features operational

### Iteration 2 Scope (CURRENT PRIORITY ⚠️)
**Deliverable**: Template API endpoints + Metrics infrastructure
- ⚠️ User Story 3: API endpoints (T019-T021) - 50% complete
- ⬜ User Story 4: Prometheus metrics (T022-T032)

**Value**: Template-based creation accessible via API, full observability

### Iteration 3 Scope (FUTURE)
**Deliverable**: UI and documentation
- ⬜ User Story 3: React UI for templates (T033-T037)
- ⬜ Polish: Documentation and runbooks (T038-T041)

**Value**: End-to-end user experience, production readiness

---

## Task Completeness Validation

### User Story 1: Retry ✅
- [x] Retry logic implemented in both clients
- [x] Exponential backoff with configurable parameters
- [x] Retry metadata captured and stored
- [x] Timeout configuration integrated
- [x] Non-retryable errors handled correctly

**Independent Test**: ✅ Can be tested by mocking HTTP 503 responses and verifying retry behavior

### User Story 2: Validation ✅
- [x] Validation module created with all error codes
- [x] Required fields, max length, enum, regex validation
- [x] Validation integrated into ticket creation
- [x] Validation errors stored in metadata
- [x] Error accumulation (not fail-fast)

**Independent Test**: ✅ Can be tested by submitting invalid payloads and checking ValidationResult

### User Story 3: Templates ⚠️
- [x] Template service created with rendering logic
- [x] Variable substitution with recursive support
- [x] Template listing and retrieval
- [x] Integration into TicketService
- [ ] API endpoints (T019-T021) - PENDING
- [ ] UI components (T033-T037) - BLOCKED

**Independent Test**: ⚠️ Backend testable, API/UI blocked on T019-T021

### User Story 4: Metrics ⬜
- [ ] All metrics defined and instrumented (T022-T027)
- [ ] Grafana dashboard created (T028)
- [ ] Alert rules defined (T029)
- [ ] SLA tracking fields added (T030-T032)

**Independent Test**: ⬜ Cannot test until T022-T032 complete

---

## Summary

**Total Tasks**: 41
- ✅ Completed: 18 (Phases 1-2, US1, US2, US3 backend)
- ⚠️ In Progress: 3 (US3 API endpoints: T019-T021)
- ⬜ Pending: 20 (US4 metrics, US3 UI, Polish)

**Tasks by User Story**:
- US1 (Retry): 9 tasks ✅ COMPLETE
- US2 (Validation): 5 tasks ✅ COMPLETE
- US3 (Templates): 9 tasks total (4 ✅ complete, 3 ⚠️ in progress, 2 ⬜ pending UI)
- US4 (Metrics): 11 tasks ⬜ NOT STARTED
- Polish: 4 tasks ⬜ NOT STARTED

**Parallel Opportunities**: 15 tasks marked [P] for parallel execution

**Independent Test Criteria**: Each user story has clear, independent test criteria defined

**MVP Delivered**: ✅ US1 + US2 + US3 backend (retry, validation, templates) fully functional

**Recommended Next Steps**:
1. Complete US3 API endpoints (T019-T021) - unblocks UI development
2. Start US4 metrics (T022-T032) in parallel - enables observability
3. After T021: Implement US3 UI (T033-T037) and polish (T038-T041) in parallel
