# Feature Specification: Advanced ITSM Integration Hardening

**Feature ID**: ITSM-ADV-001  
**Priority**: High  
**Status**: Implementation Phase  
**Date**: 2025-10-12

## Overview

Implement enterprise-grade ITSM features to harden ServiceNow/Jira integrations with retry logic, payload validation, template-driven ticket creation, and comprehensive analytics.

## Goals

1. **Resilience**: Add configurable retry/backoff for transient failures in ITSM integrations
2. **Data Quality**: Enforce payload schema validation before ticket transmission
3. **Consistency**: Support template-driven ticket creation with variable substitution
4. **Observability**: Expose comprehensive metrics for ITSM operations and SLA tracking
5. **Developer Experience**: Provide clear API contracts and documentation

## User Stories

### US-1: Automatic Retry on Transient Failures
**As a** platform operator  
**I want** ITSM ticket creation to automatically retry on transient failures  
**So that** temporary network issues don't result in lost tickets

**Acceptance Criteria:**
- ServiceNow and Jira clients retry on 429, 500, 502, 503, 504 status codes
- Exponential backoff with configurable multiplier (default: 2x)
- Maximum 3 retries by default (configurable)
- Retry attempts and delays captured in ticket metadata
- Non-retryable errors (4xx except 429) fail immediately

### US-2: Pre-Flight Payload Validation
**As a** developer  
**I want** ticket payloads validated against field schemas before transmission  
**So that** I receive clear error messages instead of cryptic API failures

**Acceptance Criteria:**
- Validation enforces required fields, max lengths, enum values, regex patterns
- Validation errors include field name, error code, and descriptive message
- API responses distinguish validation errors from server errors
- Validation failures prevent ticket creation and emit structured events

### US-3: Template-Based Ticket Creation
**As a** automation engineer  
**I want** to create tickets from reusable templates with variable substitution  
**So that** tickets have consistent formatting and required fields

**Acceptance Criteria:**
- Templates defined in `itsm_config.json` with `{variable}` placeholders
- API endpoint to list available templates by platform
- API endpoint to create ticket from template with variable values
- Template rendering errors provide missing variable details
- UI provides template dropdown with field preview

### US-4: ITSM Operations Metrics
**As a** SRE  
**I want** Prometheus metrics for ticket operations  
**So that** I can monitor integration health and create alerts

**Acceptance Criteria:**
- Metrics for: ticket creation (total, duration), retry attempts, validation errors, template rendering errors
- Metrics labeled by: platform, outcome, retry_attempts
- Grafana dashboard visualizes throughput, error rates, SLA compliance
- Alert rules for sustained high error rates

## Technical Requirements

### Retry Configuration
```json
{
  "retry_policy": {
    "max_retries": 3,
    "retry_delay_seconds": 5,
    "exponential_backoff": true,
    "backoff_multiplier": 2,
    "max_retry_delay_seconds": 60,
    "retryable_status_codes": [429, 500, 502, 503, 504]
  }
}
```

### Timeout Configuration
```json
{
  "timeout": {
    "connection_timeout_seconds": 10,
    "read_timeout_seconds": 30,
    "total_timeout_seconds": 60
  }
}
```

### Template Format
```json
{
  "templates": {
    "servicenow": {
      "rca_incident": {
        "short_description": "RCA Required: {job_name}",
        "description": "Job ID: {job_id}\nSeverity: {severity}\n\n{details}",
        "priority": "{priority}"
      }
    }
  }
}
```

### API Endpoints

**GET /api/v1/tickets/templates**
- Query params: `platform` (optional: servicenow|jira)
- Response: List of template metadata

**POST /api/v1/tickets/from-template**
- Body: `{job_id, platform, template_name, variables, dry_run}`
- Response: Created ticket with template metadata

### Metrics

Required Prometheus metrics:
- `itsm_ticket_creation_total{platform, outcome}` - Counter
- `itsm_ticket_creation_duration_seconds{platform, outcome}` - Histogram
- `itsm_ticket_retry_attempts_total{platform}` - Counter
- `itsm_validation_errors_total{platform, field}` - Counter
- `itsm_template_rendering_errors_total{template_name}` - Counter

## Implementation Phases

### Phase 1: Retry & Timeout (COMPLETED)
- [x] Retry logic in ServiceNowClient and JiraClient
- [x] Timeout configuration support
- [x] Retry metadata in TicketCreationResult

### Phase 2: Validation & Templates (COMPLETED)
- [x] Payload validation module
- [x] Template service with variable substitution
- [x] Integration into TicketService
- [x] create_from_template method

### Phase 3: Analytics & UI (IN PROGRESS)
- [ ] API endpoints for templates
- [ ] Prometheus metrics instrumentation
- [ ] Grafana dashboard
- [ ] SLA tracking fields
- [ ] React UI for template selection
- [ ] Comprehensive unit tests
- [ ] Documentation updates

## Dependencies

- Existing: `httpx`, `sqlalchemy`, `pydantic`, `prometheus_client`
- Configuration: `config/itsm_config.json`
- Database: PostgreSQL with existing `tickets` table

## Success Metrics

- Retry success rate: >90% for transient failures
- Validation error rate: <1% of total ticket creation attempts
- Template usage: >50% of tickets created via templates
- Ticket creation p95 latency: <2s including retries
- Zero silent failures (all errors logged and metered)

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Excessive retries cause delays | Medium | Configurable max retries and backoff ceiling |
| Validation too strict blocks legitimate tickets | High | Dry-run mode with validation warnings |
| Template variables missing | Medium | Clear error messages with required variable list |
| Metrics overhead | Low | Async metric emission, sampling for high-volume |

## References

- Constitution: `.specify/memory/constitution.md`
- PRD: `PRD.md`
- README: `README.md`
- ITSM Config: `config/itsm_config.json`
