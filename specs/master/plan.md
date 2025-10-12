# Implementation Plan: Advanced ITSM Integration Hardening

**Branch**: `master` | **Date**: 2025-10-12 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/master/spec.md`

**Note**: This plan covers Phases 1-2 (completed) and Phase 3 (in progress) of the advanced ITSM features.

## Summary

Implement enterprise-grade ITSM integration features including:
1. **Resilience**: Configurable retry logic with exponential backoff for ServiceNow/Jira clients
2. **Data Quality**: Schema-first payload validation against field mappings
3. **Consistency**: Template-driven ticket creation with variable substitution
4. **Observability**: Prometheus metrics for all ITSM operations and SLA tracking

**Technical Approach**:
- Extend existing `core/tickets/clients.py` with retry/timeout infrastructure
- Create new `core/tickets/validation.py` for pre-flight payload validation
- Create new `core/tickets/template_service.py` for template rendering
- Integrate validation and templates into `core/tickets/service.py`
- Add REST API endpoints for template operations
- Instrument all operations with Prometheus metrics
- Create Grafana dashboard for visualization

## Technical Context

**Language/Version**: Python 3.11+  
**Primary Dependencies**: 
- FastAPI (REST API framework)
- httpx (async HTTP client with retry support)
- SQLAlchemy 2.0+ (ORM with asyncio support)
- Pydantic v2 (data validation)
- prometheus_client (metrics)
- asyncio (async/await patterns)

**Storage**: 
- PostgreSQL 15+ with pgvector extension
- Existing `tickets` table in `core.db.models`
- JSON configuration in `config/itsm_config.json`

**Testing**: 
- pytest with pytest-asyncio for async tests
- httpx MockTransport for HTTP client testing
- pytest-mock for mocking ITSM APIs
- Coverage target: >85% for new code

**Target Platform**: 
- Linux server (Docker containers)
- Python asyncio runtime
- Gunicorn + Uvicorn workers

**Project Type**: Web application (backend-focused with React UI)

**Performance Goals**:
- Ticket creation p95 latency: <2s (including retries)
- Validation overhead: <10ms per payload
- Template rendering: <5ms per template
- Support 100 concurrent ticket creation requests
- Metrics collection overhead: <1ms per operation

**Constraints**:
- Must maintain backward compatibility with existing ticket creation API
- Retry logic must not exceed 60s total timeout
- Validation must not block async event loop
- All ITSM credentials must remain in environment/secrets (never logged)
- Template system must support nested variable substitution

**Scale/Scope**:
- 4 initial templates (2 ServiceNow, 2 Jira)
- ~20 validation rules per platform
- Support for 2 ITSM platforms (ServiceNow, Jira)
- Expected: 1000s of tickets per day in production
- Metrics retention: 30 days in Prometheus

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

**Constitution Version**: 1.0.0 (Ratified: 2025-10-12)

### Principle I: Resilience by Design ✅
- **Requirement**: All external integrations MUST implement configurable retry logic with exponential backoff
- **Implementation**: 
  - `RetryPolicy` class in `clients.py` loads from `itsm_config.json`
  - ServiceNowClient and JiraClient implement retry loops in `_request()` methods
  - Exponential backoff with configurable multiplier, max delay, and retryable status codes
  - Retry metadata captured in all results
- **Status**: COMPLIANT

### Principle II: Schema-First Validation ✅
- **Requirement**: All ITSM payloads MUST be validated against declared field mappings before transmission
- **Implementation**:
  - `TicketPayloadValidator` in `validation.py` loads field_mapping from config
  - Validates required fields, max lengths, enums, regex patterns
  - Returns structured `ValidationResult` with field-level errors
  - Integrated into `TicketService.create_ticket()` before transmission
- **Status**: COMPLIANT

### Principle III: Template-Driven Ticket Creation ✅
- **Requirement**: Ticket creation MUST support reusable, parameterized templates
- **Implementation**:
  - `TicketTemplateService` in `template_service.py` loads templates from config
  - Variable substitution with `{variable}` syntax
  - `TicketService.create_from_template()` method with automatic job context injection
  - Template validation for missing required variables
- **Status**: COMPLIANT

### Principle IV: Metrics-First Integration ⚠️
- **Requirement**: All ITSM operations MUST emit Prometheus-compatible metrics
- **Implementation**: IN PROGRESS
  - Metrics instrumentation pending (Task 9)
  - Required metrics identified:
    - `itsm_ticket_creation_total{platform, outcome}`
    - `itsm_ticket_creation_duration_seconds{platform, outcome}`
    - `itsm_ticket_retry_attempts_total{platform}`
    - `itsm_validation_errors_total{platform, field}`
    - `itsm_template_rendering_errors_total{template_name}`
- **Status**: PARTIAL - Core infrastructure complete, instrumentation pending

### Principle V: Test Coverage for Integration Paths ⚠️
- **Requirement**: All retry logic, validation rules, and template rendering MUST have dedicated unit tests
- **Implementation**: PENDING
  - Test files identified: `test_itsm_retry.py`, `test_itsm_validation.py`, `test_itsm_templates.py`
  - Test scenarios documented in tasks 13-16
- **Status**: PARTIAL - Core code complete, tests pending

### Enterprise Integration Standards ✅
- **Timeout Configuration**: Implemented via `TimeoutConfig` class
  - Connection: 10s, Read: 30s, Total: 60s (configurable)
- **Error Propagation**: All errors wrapped in `TicketClientError` with context
- **Credential Management**: No changes to existing secure credential handling
- **Status**: COMPLIANT

### Quality & Observability Standards ✅
- **Structured Logging**: All operations log with job_id, platform, operation, outcome
- **Prometheus Metrics**: Infrastructure ready (pending instrumentation)
- **API Documentation**: OpenAPI spec updates pending (Task 18)
- **Status**: MOSTLY COMPLIANT (documentation updates pending)

**GATE VERDICT**: ✅ PASS with minor follow-ups
- Phases 1-2 fully compliant with constitution
- Phase 3 tasks will complete metrics and testing requirements
- No blocking violations

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

**Structure Decision**: Web application with FastAPI backend and React frontend. ITSM feature is backend-focused with minimal UI changes.

```
core/
├── tickets/
│   ├── __init__.py
│   ├── clients.py              # [MODIFIED] Retry/timeout logic, RetryPolicy, TimeoutConfig
│   ├── service.py              # [MODIFIED] Validation integration, create_from_template()
│   ├── validation.py           # [NEW] TicketPayloadValidator, ValidationResult
│   ├── template_service.py     # [NEW] TicketTemplateService, template rendering
│   ├── settings.py             # [EXISTING] No changes
│   └── __init__.py             # [EXISTING] No changes
├── db/
│   └── models.py               # [PENDING] Add SLA tracking fields to Ticket model
├── metrics.py                  # [MODIFIED] Add ITSM-specific metrics
└── logging.py                  # [EXISTING] No changes

apps/
├── api/
│   ├── routers/
│   │   └── tickets.py          # [MODIFIED] Add template endpoints
│   └── main.py                 # [MODIFIED] Update OpenAPI spec
└── worker/
    └── main.py                 # [EXISTING] No changes

config/
└── itsm_config.json            # [EXISTING] Already has retry_policy, timeout, templates, validation

tests/
├── test_itsm_retry.py          # [NEW] Retry logic tests
├── test_itsm_validation.py     # [NEW] Validation tests
├── test_itsm_templates.py      # [NEW] Template rendering tests
└── test_metrics.py             # [MODIFIED] Add ITSM metrics tests

ui/
└── src/
    └── components/
        └── tickets/
            └── TicketCreationForm.tsx  # [MODIFIED] Add template selection UI

deploy/
└── docker/
    └── config/
        └── grafana/
            └── dashboards/
                └── itsm_analytics.json  # [NEW] ITSM dashboard

docs/
├── ITSM_INTEGRATION_GUIDE.md   # [MODIFIED] Add retry/validation/template docs
└── ITSM_README.md              # [MODIFIED] Update with new features
```

**Key Files by Phase**:

**Phase 1 (Completed):**
- `core/tickets/clients.py` - Retry and timeout infrastructure
- `core/tickets/validation.py` - Payload validation

**Phase 2 (Completed):**
- `core/tickets/template_service.py` - Template system
- `core/tickets/service.py` - Integration layer

**Phase 3 (In Progress):**
- `apps/api/routers/tickets.py` - REST endpoints
- `core/metrics.py` - Metrics instrumentation
- `tests/test_itsm_*.py` - Test suite
- `ui/src/components/tickets/TicketCreationForm.tsx` - UI updates
- `deploy/docker/config/grafana/dashboards/itsm_analytics.json` - Dashboard
- `docs/ITSM_*.md` - Documentation

## Complexity Tracking

*No constitutional violations requiring justification. All design decisions align with established principles.*
