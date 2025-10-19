# Data Model: Advanced ITSM Integration

**Feature**: Advanced ITSM Integration Hardening  
**Date**: 2025-10-12  
**Status**: Design Complete

## Overview

This document describes the data structures for retry logic, validation, templates, and metrics in the ITSM integration system.

---

## Core Data Structures

### RetryPolicy

**Purpose**: Configuration for retry behavior with exponential backoff

**Fields**:
| Field | Type | Default | Description |
|-------|------|---------|-------------|
| max_retries | int | 3 | Maximum number of retry attempts |
| retry_delay_seconds | float | 5.0 | Initial delay before first retry |
| exponential_backoff | bool | True | Enable exponential backoff |
| backoff_multiplier | float | 2.0 | Multiplier for exponential backoff |
| max_retry_delay_seconds | float | 60.0 | Maximum delay between retries |
| retryable_status_codes | List[int] | [429, 500, 502, 503, 504] | HTTP status codes that trigger retry |

**Validation Rules**:
- `max_retries` >= 0
- `retry_delay_seconds` > 0
- `backoff_multiplier` >= 1.0
- `max_retry_delay_seconds` >= `retry_delay_seconds`

**Source**: Loaded from `itsm_config.json["retry_policy"]`

**Example**:
```json
{
  "max_retries": 3,
  "retry_delay_seconds": 5,
  "exponential_backoff": true,
  "backoff_multiplier": 2,
  "max_retry_delay_seconds": 60,
  "retryable_status_codes": [429, 500, 502, 503, 504]
}
```

---

### TimeoutConfig

**Purpose**: Configuration for HTTP request timeouts

**Fields**:
| Field | Type | Default | Description |
|-------|------|---------|-------------|
| connection_timeout_seconds | float | 10.0 | Time to establish TCP connection |
| read_timeout_seconds | float | 30.0 | Time to receive response after request sent |
| total_timeout_seconds | float | 60.0 | Maximum end-to-end request duration |

**Validation Rules**:
- All timeouts > 0
- `total_timeout_seconds` >= `connection_timeout_seconds` + `read_timeout_seconds`

**Source**: Loaded from `itsm_config.json["timeout"]`

**Conversion**: Converts to `httpx.Timeout` object for HTTP client

---

### ValidationError

**Purpose**: Represents a single field validation error

**Fields**:
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| field | str | Yes | Name of the field that failed validation |
| error_code | str | Yes | Machine-readable error code (e.g., "required_field_missing") |
| message | str | Yes | Human-readable error message |
| details | Dict[str, Any] | No | Additional context (e.g., max_length, allowed_values) |

**Error Codes**:
- `required_field_missing` - Required field not provided
- `max_length_exceeded` - String exceeds max length
- `invalid_enum_value` - Value not in allowed set
- `pattern_mismatch` - Value doesn't match regex pattern
- `invalid_type` - Field type doesn't match expected type
- `invalid_platform` - Unsupported ITSM platform

**Example**:
```python
ValidationError(
    field="priority",
    error_code="invalid_enum_value",
    message="Field 'priority' has invalid value '6'. Allowed values: 1, 2, 3, 4, 5.",
    details={"allowed_values": ["1", "2", "3", "4", "5"], "provided_value": "6"}
)
```

---

### ValidationResult

**Purpose**: Result of payload validation with all errors

**Fields**:
| Field | Type | Description |
|-------|------|-------------|
| valid | bool | True if payload passed all validation checks |
| errors | List[ValidationError] | List of validation errors (empty if valid) |

**Methods**:
- `error_dict() -> Dict[str, List[Dict]]` - Group errors by field for API responses

**Example**:
```python
result = ValidationResult(
    valid=False,
    errors=[
        ValidationError(field="summary", error_code="required_field_missing", ...),
        ValidationError(field="priority", error_code="invalid_enum_value", ...)
    ]
)

# Convert to API response format
error_response = {
    "valid": False,
    "errors": result.error_dict()
}
# {
#   "valid": false,
#   "errors": {
#     "summary": [{"error_code": "required_field_missing", ...}],
#     "priority": [{"error_code": "invalid_enum_value", ...}]
#   }
# }
```

---

### TicketTemplate

**Purpose**: Represents a ticket template with metadata

**Fields**:
| Field | Type | Description |
|-------|------|-------------|
| name | str | Template name (e.g., "rca_incident") |
| platform | str | Target platform ("servicenow" or "jira") |
| fields | Dict[str, Any] | Template fields with variable placeholders |
| description | Optional[str] | Human-readable template description |
| required_variables | Optional[List[str]] | List of required variable names |

**Variable Syntax**: `{variable_name}` in string values

**Example**:
```python
TicketTemplate(
    name="rca_incident",
    platform="servicenow",
    fields={
        "short_description": "RCA Required: {job_name}",
        "description": "Job ID: {job_id}\nSeverity: {severity}\n\n{details}",
        "priority": "3",
        "category": "Software"
    },
    description="Template for RCA investigation tickets",
    required_variables=["job_name", "job_id", "severity", "details"]
)
```

---

### TicketCreationResult (Enhanced)

**Purpose**: Result of ticket creation with retry metadata

**Existing Fields**:
| Field | Type | Description |
|-------|------|-------------|
| ticket_id | str | Platform-specific ticket identifier |
| status | Optional[str] | Current ticket status |
| url | Optional[str] | Link to ticket in ITSM platform |
| payload | Dict[str, Any] | Payload sent to ITSM API |
| metadata | Dict[str, Any] | Additional metadata |

**New Metadata Fields** (in `metadata` dict):
| Field | Type | Description |
|-------|------|-------------|
| retry_metadata | Dict | Retry information from HTTP request |
| retry_metadata.retry_attempts | int | Number of retry attempts made |
| retry_metadata.retry_delays | List[float] | Delay before each retry (seconds) |
| retry_metadata.retryable_errors | List[Dict] | Errors that triggered retries |
| retry_metadata.final_error | Optional[str] | Final error message if all retries failed |
| template_name | Optional[str] | Template used (if created from template) |
| template_variables | Optional[Dict] | Variables passed to template |
| validation_errors | Optional[Dict] | Validation errors (if validation failed) |
| validation_failed | Optional[bool] | True if validation forced dry-run mode |

**Example**:
```python
TicketCreationResult(
    ticket_id="INC0012345",
    status="New",
    url="https://instance.service-now.com/...",
    payload={...},
    metadata={
        "sys_id": "abc123",
        "retry_metadata": {
            "retry_attempts": 2,
            "retry_delays": [5.0, 10.0],
            "retryable_errors": [
                {"attempt": 1, "status_code": 503, "message": "..."},
                {"attempt": 2, "status_code": 503, "message": "..."}
            ],
            "final_error": None
        },
        "template_name": "rca_incident",
        "template_variables": {"job_id": "job-123", "severity": "high"}
    }
)
```

---

## Database Model Changes

### Ticket Model Enhancements

**Purpose**: Add SLA tracking fields for ticket lifecycle

**New Fields**:
| Field | Type | Nullable | Description |
|-------|------|----------|-------------|
| acknowledged_at | DateTime(timezone=True) | Yes | When ticket was first acknowledged |
| resolved_at | DateTime(timezone=True) | Yes | When ticket was marked resolved |
| time_to_acknowledge | Interval | Yes | Duration from creation to acknowledgement |
| time_to_resolve | Interval | Yes | Duration from creation to resolution |

**Computed Fields**:
- `time_to_acknowledge` = `acknowledged_at` - `created_at`
- `time_to_resolve` = `resolved_at` - `created_at`

**Migration**:
```sql
ALTER TABLE tickets
ADD COLUMN acknowledged_at TIMESTAMP WITH TIME ZONE,
ADD COLUMN resolved_at TIMESTAMP WITH TIME ZONE,
ADD COLUMN time_to_acknowledge INTERVAL,
ADD COLUMN time_to_resolve INTERVAL;

CREATE INDEX idx_tickets_acknowledged_at ON tickets(acknowledged_at);
CREATE INDEX idx_tickets_resolved_at ON tickets(resolved_at);
```

---

## Configuration Schema

### itsm_config.json Structure

```json
{
  "retry_policy": { /* RetryPolicy fields */ },
  "timeout": { /* TimeoutConfig fields */ },
  "templates": {
    "servicenow": {
      "template_name": { /* Template fields */ }
    },
    "jira": {
      "template_name": { /* Template fields */ }
    }
  },
  "servicenow": {
    "field_mapping": { /* Field validation rules */ }
  },
  "jira": {
    "field_mapping": { /* Field validation rules */ }
  },
  "validation": {
    "enabled": true,
    "rules": {
      "servicenow": { /* Platform-specific validation toggles */ },
      "jira": { /* Platform-specific validation toggles */ }
    }
  }
}
```

---

## API Request/Response Models

### Template List Response

**Endpoint**: `GET /api/v1/tickets/templates`

**Response Model**:
```python
class TemplateMetadata(BaseModel):
    name: str
    platform: str
    description: Optional[str]
    required_variables: List[str]
    field_count: int

class TemplateListResponse(BaseModel):
    templates: List[TemplateMetadata]
    count: int
```

**Example Response**:
```json
{
  "templates": [
    {
      "name": "rca_incident",
      "platform": "servicenow",
      "description": "Template for RCA investigation tickets",
      "required_variables": ["job_name", "job_id", "severity", "details"],
      "field_count": 4
    }
  ],
  "count": 1
}
```

---

### Create from Template Request

**Endpoint**: `POST /api/v1/tickets/from-template`

**Request Model**:
```python
class CreateFromTemplateRequest(BaseModel):
    job_id: str
    platform: str  # "servicenow" or "jira"
    template_name: str
    variables: Optional[Dict[str, Any]] = None
    profile_name: Optional[str] = None
    dry_run: bool = True

class CreateFromTemplateResponse(BaseModel):
    ticket_id: str
    platform: str
    status: str
    url: Optional[str]
    dry_run: bool
    template_name: str
    created_at: datetime
    metadata: Dict[str, Any]
```

**Example Request**:
```json
{
  "job_id": "job-123",
  "platform": "servicenow",
  "template_name": "rca_incident",
  "variables": {
    "custom_field": "value"
  },
  "dry_run": false
}
```

---

## Metrics Schema

### Prometheus Metrics

**Counter Metrics**:
```
itsm_ticket_creation_total{platform="servicenow|jira", outcome="success|failure"}
itsm_ticket_retry_attempts_total{platform="servicenow|jira"}
itsm_validation_errors_total{platform="servicenow|jira", field="<field_name>"}
itsm_template_rendering_errors_total{template_name="<template_name>"}
```

**Histogram Metrics**:
```
itsm_ticket_creation_duration_seconds{platform="servicenow|jira", outcome="success|failure"}
# Buckets: [.005, .01, .025, .05, .075, .1, .25, .5, .75, 1.0, 2.5, 5.0, 7.5, 10.0, +Inf]
```

**Label Cardinality**:
- `platform`: 2 values (servicenow, jira)
- `outcome`: 2 values (success, failure)
- `field`: ~20 values per platform (bounded by field_mapping)
- `template_name`: ~10 values (bounded by template count)

**Total Cardinality**: <100 metric series (acceptable)

---

## State Transitions

### Ticket Lifecycle

```
[Created] --(acknowledge)--> [Acknowledged] --(resolve)--> [Resolved]
    |                              |                            |
    +-----(close without resolve)--+---------------------------+
                                   |
                              [Closed]
```

**State Updates via Status Refresh**:
1. `_refresh_ticket_batch()` fetches latest status from ITSM platform
2. If status changes to "Acknowledged" → set `acknowledged_at`, compute `time_to_acknowledge`
3. If status changes to "Resolved" → set `resolved_at`, compute `time_to_resolve`
4. Store raw ITSM response in `metadata.sync.raw`

---

## Relationships

```
Job (1) ---> (N) Tickets
  ^                |
  |                |
  +-- job_id ------+

Ticket (1) ---> (1) TicketCreationResult (transient, not stored)
  ^
  |
  +-- metadata.retry_metadata
  +-- metadata.template_name
  +-- metadata.validation_errors
```

---

## Validation Rules by Platform

### ServiceNow

| Field | Type | Required | Max Length | Enum Values | Regex |
|-------|------|----------|------------|-------------|-------|
| short_description | string | Yes | 160 | - | - |
| description | string | No | 4000 | - | - |
| priority | choice | No | - | 1,2,3,4,5 | - |
| category | string | No | - | [Inquiry / Help, Software, Hardware, Network, Database] | - |
| assignment_group | reference | No | - | - | - |

### Jira

| Field | Type | Required | Max Length | Enum Values | Regex |
|-------|------|----------|------------|-------------|-------|
| project_key | string | Yes | - | - | ^[A-Z][A-Z0-9]+$ |
| summary | string | Yes | 255 | - | - |
| description | text | No | - | - | - |
| issue_type | string | No | - | [Incident, Bug, Task, Story, Epic, Subtask] | - |
| priority | string | No | - | [Highest, High, Medium, Low, Lowest] | - |

---

## Index Strategy

### Database Indexes

**Existing**:
- `tickets.job_id` (foreign key index)
- `tickets.created_at` (for time-series queries)

**New (for SLA tracking)**:
- `tickets.acknowledged_at` (for SLA queries)
- `tickets.resolved_at` (for SLA queries)
- Composite: `(platform, status, created_at)` (for dashboard queries)

---

## Conclusion

Data model supports all requirements:
- ✅ Retry logic with comprehensive metadata
- ✅ Validation with structured error reporting
- ✅ Templates with variable substitution
- ✅ Metrics with appropriate labels and cardinality
- ✅ SLA tracking with lifecycle timestamps
- ✅ Backward compatibility with existing Ticket model
