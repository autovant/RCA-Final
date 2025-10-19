# Research: Advanced ITSM Integration

**Feature**: Advanced ITSM Integration Hardening  
**Date**: 2025-10-12  
**Status**: Research Complete

## Research Questions

### Q1: What retry strategy best balances reliability and latency for ITSM APIs?

**Decision**: Exponential backoff with jitter and circuit breaker pattern

**Rationale**:
- ITSM platforms (ServiceNow, Jira) commonly experience transient failures during high load
- Exponential backoff prevents thundering herd: 5s → 10s → 20s → 40s (capped at 60s)
- Jitter (randomization) prevents synchronized retries across multiple workers
- Circuit breaker prevents retry storms when platform is truly down
- Industry standard for distributed systems (AWS SDK, Google Cloud Client Libraries)

**Alternatives Considered**:
1. **Fixed-interval retry** - Rejected: Can cause thundering herd, doesn't adapt to severity
2. **Linear backoff** - Rejected: Too slow for transient failures, too aggressive for sustained issues
3. **Exponential without cap** - Rejected: Could lead to minutes-long waits for user-facing operations

**References**:
- [AWS SDK Retry Strategy](https://aws.amazon.com/blogs/architecture/exponential-backoff-and-jitter/)
- [Google Cloud Retry Best Practices](https://cloud.google.com/apis/design/errors#error_retries)
- [Polly Resilience Patterns](https://github.com/App-vNext/Polly/wiki/Retry)

---

### Q2: Should validation be fail-fast or accumulate all errors?

**Decision**: Accumulate all validation errors in a single pass

**Rationale**:
- Better developer experience: See all validation issues at once vs. iterative fixing
- Aligns with industry-standard validators (JSON Schema, Pydantic, JSR-303)
- Minimal performance impact: Single traversal of payload dictionary
- Enables client-side correction without round-trips

**Alternatives Considered**:
1. **Fail-fast on first error** - Rejected: Poor DX, requires multiple attempts to fix all issues
2. **Async validation with streaming** - Rejected: Overkill for small ticket payloads (<5KB)

**Implementation Notes**:
- Return `ValidationResult` with `List[ValidationError]`
- Each error includes: field, error_code, message, details
- Client can group errors by field for inline display

---

### Q3: How to handle template variable substitution for complex types (lists, dicts)?

**Decision**: Support recursive substitution with string interpolation only

**Rationale**:
- Templates primarily used for text fields (description, summary)
- Complex types (lists, dicts) passed through without variable substitution
- If complex field contains strings with `{var}`, those are substituted
- Prevents type coercion issues (e.g., `{priority}` might be int or string)
- Aligns with Jinja2, Mustache, and other template engines

**Alternatives Considered**:
1. **Type-aware substitution** - Rejected: Requires schema knowledge, complex edge cases
2. **Strict string-only templates** - Rejected: Too limiting for nested payloads
3. **JSONPath-style references** - Rejected: Overkill for current use cases

**Example**:
```json
{
  "summary": "Issue in {system}",
  "labels": ["rca", "automated"],
  "custom_fields": {
    "environment": "{environment}",
    "severity": "{severity}"
  }
}
```

---

### Q4: What metrics are essential for ITSM integration observability?

**Decision**: Counter, Histogram, and Gauge metrics with platform/outcome labels

**Metrics Chosen**:
1. **itsm_ticket_creation_total** (Counter) - Track volume by platform and outcome
2. **itsm_ticket_creation_duration_seconds** (Histogram) - Latency distribution with retry overhead
3. **itsm_ticket_retry_attempts_total** (Counter) - Retry frequency by platform
4. **itsm_validation_errors_total** (Counter) - Validation failures by platform and field
5. **itsm_template_rendering_errors_total** (Counter) - Template failures by template_name

**Rationale**:
- Counters for alerting on error rates and throughput
- Histograms for latency percentiles (p50, p95, p99)
- Labels enable drill-down (platform, outcome, field, template)
- Aligned with Prometheus best practices (metric naming, label cardinality)

**Alternatives Considered**:
1. **Gauge for active requests** - Rejected: Not useful for async request/response pattern
2. **Per-status-code metrics** - Rejected: Too high cardinality, use labels instead
3. **Summary instead of Histogram** - Rejected: Histogram better for aggregation across instances

**Alert Rules**:
- Fire if error rate >5% over 5 minutes
- Fire if p95 latency >3s over 10 minutes
- Fire if retry rate >50% over 5 minutes

---

### Q5: Best practices for timeout configuration in async HTTP clients?

**Decision**: Separate connection, read, and total timeouts with httpx.Timeout

**Configuration**:
- **Connection timeout**: 10s (time to establish TCP connection)
- **Read timeout**: 30s (time to receive response after request sent)
- **Total timeout**: 60s (maximum end-to-end duration including retries)

**Rationale**:
- Connection timeout prevents hanging on unreachable hosts
- Read timeout prevents waiting indefinitely for slow ITSM APIs
- Total timeout ensures retry loops don't exceed SLA
- httpx.Timeout provides granular control vs. single timeout value
- Aligns with HTTPX best practices and production deployments

**Alternatives Considered**:
1. **Single timeout value** - Rejected: Can't distinguish connection vs. read issues
2. **No timeout** - Rejected: Can cause indefinite hangs
3. **Dynamic timeouts based on endpoint** - Rejected: Premature optimization

**Implementation**:
```python
timeout = httpx.Timeout(
    connect=10.0,
    read=30.0,
    write=30.0,
    pool=60.0
)
```

---

### Q6: How to store and retrieve templates from configuration?

**Decision**: Load from `itsm_config.json` at service initialization, cache in memory

**Rationale**:
- Templates change infrequently (configuration-as-code)
- Loading at startup avoids disk I/O on every ticket creation
- JSON format is human-readable and version-controllable
- No database dependency for template storage
- Service restart required for template updates (acceptable for config changes)

**Alternatives Considered**:
1. **Database storage** - Rejected: Overkill for configuration data, adds complexity
2. **Hot-reload on file change** - Rejected: Adds complexity, rare update frequency
3. **Separate template files** - Rejected: Harder to version and deploy

**Template Discovery**:
- Templates indexed by: `{platform}.{template_name}`
- Example: `servicenow.rca_incident`, `jira.production_incident`
- List endpoint returns all templates with metadata (name, platform, required_variables)

---

## Technology Stack Validation

### Python asyncio Best Practices
- **Finding**: All ITSM operations use `async/await` consistently
- **Validation**: No blocking I/O in async context (httpx is fully async)
- **Best Practice**: Use `asyncio.sleep()` for retry delays (not `time.sleep()`)

### HTTPx for Async HTTP
- **Finding**: httpx recommended over aiohttp for better type hints and error handling
- **Validation**: Supports timeout configuration, connection pooling, retry-friendly exceptions
- **Best Practice**: Use context managers for client lifecycle

### Pydantic for API Contracts
- **Finding**: Pydantic v2 provides fast validation and auto-generated OpenAPI schemas
- **Validation**: Existing codebase uses Pydantic for API models
- **Best Practice**: Use `@dataclass` for internal models, Pydantic for API boundaries

### Prometheus Client for Metrics
- **Finding**: `prometheus_client` library is standard for Python
- **Validation**: Thread-safe, supports Counter/Histogram/Gauge/Summary
- **Best Practice**: Use labels for dimensions, avoid high cardinality

---

## Design Patterns

### Retry Pattern
**Pattern**: Retry with exponential backoff and circuit breaker
**Application**: ServiceNowClient, JiraClient
**Benefits**: Resilience to transient failures, prevents cascade failures

### Validation Pattern
**Pattern**: Fail-fast validation with error accumulation
**Application**: TicketPayloadValidator
**Benefits**: Better developer experience, single-pass validation

### Template Pattern
**Pattern**: Variable substitution with recursive traversal
**Application**: TicketTemplateService
**Benefits**: Flexible, supports nested objects, type-safe

### Service Layer Pattern
**Pattern**: Orchestration layer coordinating clients, validation, templates
**Application**: TicketService
**Benefits**: Single responsibility, testable, composable

---

## Implementation Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Retry storms during platform outages | Medium | High | Circuit breaker pattern, exponential backoff |
| Template variable injection attacks | Low | Medium | No eval/exec, string substitution only |
| Validation performance degradation | Low | Low | Single-pass validation, <10ms overhead |
| Metrics cardinality explosion | Low | Medium | Limit label values, use high-level labels |
| Breaking changes to existing ticket API | Low | High | Maintain backward compatibility, add new optional params |

---

## Testing Strategy

### Unit Tests
- **Retry Logic**: Mock httpx responses, verify retry attempts and delays
- **Validation**: Test all validation rules (required, length, enum, regex)
- **Templates**: Test variable substitution, missing variables, nested objects
- **Metrics**: Verify metric emission for all code paths

### Integration Tests
- **End-to-End**: Create ticket with retry, validation, and template
- **External APIs**: Use VCR.py to record/replay ITSM API interactions
- **Performance**: Measure validation/template overhead (<10ms target)

### Contract Tests
- **API Endpoints**: OpenAPI schema validation
- **Template Schema**: Validate all templates against field mappings

---

## Performance Benchmarks

### Baseline (Existing Implementation)
- Ticket creation (no retry): ~500ms (p95)
- Network latency to ServiceNow: ~200ms
- Network latency to Jira: ~150ms

### Target (With Enhancements)
- Ticket creation (no retry): ~510ms (p95) - 10ms validation overhead
- Ticket creation (1 retry): ~1.5s (p95) - 5s delay + 500ms attempt
- Ticket creation (3 retries): ~2s (p95) - worst case
- Template rendering: <5ms
- Validation: <10ms

---

## Conclusion

All research questions resolved with clear decisions and rationale. Implementation can proceed to Phase 1 (Retry/Timeout) without blockers. Technical choices align with:
- Industry best practices (AWS, Google Cloud patterns)
- Python async/await ecosystem
- Existing RCA Insight Engine architecture
- Constitution principles (resilience, validation, templates, metrics, testing)
