<!--
Sync Impact Report:
  Version Change: 0.0.0 → 1.0.0
  Modified Principles:
    - All principles newly defined for RCA Insight Engine
  Added Sections:
    - Core Principles (5 principles)
    - Enterprise Integration Standards
    - Quality & Observability Standards
    - Governance
  Templates Requiring Updates:
    ✅ Constitution updated
    ⚠️ plan-template.md - pending review for ITSM integration checks
    ⚠️ spec-template.md - pending review for retry/validation requirements
    ⚠️ tasks-template.md - pending review for template-driven task types
  Follow-up TODOs:
    - Review and update plan template to include ITSM validation gates
    - Review and update spec template for enterprise integration requirements
-->

# RCA Insight Engine Constitution

## Core Principles

### I. Resilience by Design
**All external integrations MUST implement configurable retry logic with exponential backoff.**

- ServiceNow and Jira clients MUST honour `retry_policy` from configuration
- Retry attempts, delays, and failure reasons MUST be captured in result metadata
- HTTP requests MUST respect connection, read, and total timeout limits
- Only retryable status codes (429, 500, 502, 503, 504) trigger automatic retry
- Non-retryable errors (4xx excluding 429) MUST fail fast without retry
- Maximum retry attempts and backoff multipliers MUST be externally configurable

**Rationale:** Enterprise ITSM platforms experience transient failures. Silent failures or unbounded retries compromise reliability and create hidden operational debt.

### II. Schema-First Validation
**All ITSM payloads MUST be validated against declared field mappings before transmission.**

- Load `field_mapping` and `validation.rules` from `itsm_config.json`
- Enforce required fields, max lengths, enumerated values, and regex patterns
- Return descriptive validation errors to API consumers with field-level detail
- Validation failures MUST prevent ticket creation and emit structured error events
- Custom fields MUST be validated against their declared types and constraints
- Validation rules MUST be testable independently of HTTP clients

**Rationale:** Invalid payloads cause silent failures or create malformed tickets. Pre-flight validation ensures data quality and reduces integration support burden.

### III. Template-Driven Ticket Creation
**Ticket creation MUST support reusable, parameterized templates for consistent formatting.**

- Templates defined in `itsm_config.json["templates"]` with variable substitution
- Template variables (e.g., `{job_id}`, `{severity}`, `{timestamp}`) replaced at creation time
- TicketService MUST expose `create_from_template(job_id, template_name, variables)` method
- API endpoints MUST support listing templates and creating tickets from templates
- UI MUST provide template selection with dynamic field population
- Template rendering failures MUST emit detailed error messages identifying missing variables

**Rationale:** Ad-hoc ticket formatting leads to inconsistent categorization and poor discoverability. Templates enforce organizational standards and reduce human error.

### IV. Metrics-First Integration
**All ITSM operations MUST emit Prometheus-compatible metrics for latency, success, and retry counts.**

- Instrument ticket creation, status refresh, and template rendering
- Metrics labeled by: `platform` (servicenow/jira), `outcome` (success/failure), `retry_attempts`
- Expose metrics via `/metrics` endpoint in OpenMetrics format
- SLA compliance metrics MUST track: time-to-acknowledge, time-to-resolve
- Dashboards (Grafana or equivalent) MUST visualize ticket throughput and error rates
- Alert rules MUST fire on sustained high error rates or SLA violations

**Rationale:** Observability is non-negotiable for enterprise integrations. Metrics enable proactive incident response and capacity planning.

### V. Test Coverage for Integration Paths
**All retry logic, validation rules, and template rendering MUST have dedicated unit tests.**

- Test successful retry after transient failure
- Test respect of max retry limits
- Test validation failures for each field type (required, length, enum, regex)
- Test template variable substitution and error handling for missing variables
- Test metrics emission for each operation outcome
- Integration tests MUST mock ITSM endpoints to validate retry/timeout behaviour

**Rationale:** Integration code paths are notoriously under-tested. Explicit test requirements prevent regression and ensure contract compliance.

## Enterprise Integration Standards

### Timeout Configuration
- Connection timeout: MUST NOT exceed 10 seconds
- Read timeout: MUST NOT exceed 30 seconds
- Total request timeout: MUST NOT exceed 60 seconds
- Timeouts MUST be configurable via `itsm_config.json["timeout"]`

### Error Propagation
- All ITSM client errors MUST be wrapped in `TicketClientError` with context
- Retry metadata (attempt count, delays, final error) MUST be included in result objects
- API responses MUST distinguish between validation errors, client errors, and server errors

### Credential Management
- Credentials MUST be loaded from environment variables or secret stores
- Credentials MUST NEVER be logged or included in error messages
- OAuth tokens MUST be cached and refreshed proactively before expiry

## Quality & Observability Standards

### Structured Logging
- All ITSM operations MUST log: `job_id`, `platform`, `operation`, `outcome`, `latency_ms`
- Errors MUST include: `error_type`, `retry_attempt`, `retryable` flag
- Logs MUST be JSON-structured for automated parsing

### Prometheus Metrics (Required)
- `itsm_ticket_creation_total{platform, outcome}`
- `itsm_ticket_creation_duration_seconds{platform, outcome}`
- `itsm_ticket_retry_attempts_total{platform}`
- `itsm_validation_errors_total{platform, field}`
- `itsm_template_rendering_errors_total{template_name}`

### API Documentation
- All new endpoints MUST be documented in OpenAPI spec with examples
- Error responses MUST include `error_code`, `message`, `details` fields
- Template endpoints MUST document available variables and rendering rules

## Governance

### Amendment Procedure
1. Propose constitution change with rationale and impact analysis
2. Update version following semantic versioning:
   - **MAJOR**: Breaking changes to principles or removal of mandatory rules
   - **MINOR**: New principles added or material expansions
   - **PATCH**: Clarifications, typo fixes, non-semantic refinements
3. Update dependent templates and documentation in same commit
4. Obtain approval from project maintainers before merge

### Versioning Policy
- Version format: `MAJOR.MINOR.PATCH`
- Constitution changes MUST be tracked in git history
- Sync Impact Report MUST be included as HTML comment in constitution file

### Compliance Review
- All pull requests MUST verify compliance with constitution principles
- Code reviewers MUST enforce retry logic, validation, and test coverage requirements
- CI pipeline MUST validate metrics exposition and OpenAPI spec completeness

### Guidance Files
- Runtime development guidance: `README.md`, `PRD.md`
- ITSM-specific guidance: `ITSM_README.md`, `ITSM_INTEGRATION_GUIDE.md`
- Template files: `.specify/templates/plan-template.md`, `.specify/templates/spec-template.md`

**Version**: 1.0.0 | **Ratified**: 2025-10-12 | **Last Amended**: 2025-10-12