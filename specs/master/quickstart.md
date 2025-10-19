# Quickstart: Advanced ITSM Integration

**Feature**: Advanced ITSM Integration Hardening  
**Version**: 1.0.0  
**Last Updated**: 2025-10-12

## Overview

This guide helps you get started with the advanced ITSM integration features including retry logic, payload validation, template-based ticket creation, and observability.

---

## Prerequisites

- Python 3.11+
- PostgreSQL 15+ with existing RCA Insight Engine database
- ServiceNow and/or Jira instance credentials
- Basic familiarity with RCA Insight Engine configuration

---

## Quick Start (5 minutes)

### 1. Verify Configuration

Check that `config/itsm_config.json` exists with the new sections:

```bash
cat config/itsm_config.json | jq '.retry_policy, .timeout, .templates'
```

Expected output should show retry_policy, timeout, and templates sections.

### 2. Test Validation

```python
from core.tickets.validation import validate_ticket_payload

# Test ServiceNow payload validation
payload = {
    "short_description": "Test incident",
    "priority": "1"
}

result = validate_ticket_payload("servicenow", payload)
print(f"Valid: {result.valid}")
if not result.valid:
    for error in result.errors:
        print(f"  {error.field}: {error.message}")
```

### 3. List Available Templates

```bash
curl http://localhost:8000/api/v1/tickets/templates
```

Expected response:
```json
{
  "templates": [
    {
      "name": "rca_incident",
      "platform": "servicenow",
      "required_variables": ["job_name", "job_id", "severity", "details"],
      "field_count": 6
    }
  ],
  "count": 4
}
```

### 4. Create Ticket from Template

```bash
curl -X POST http://localhost:8000/api/v1/tickets/from-template \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "job_id": "job-test-123",
    "platform": "servicenow",
    "template_name": "rca_incident",
    "dry_run": true
  }'
```

---

## Configuration Guide

### Retry Policy Configuration

Edit `config/itsm_config.json`:

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

**Tuning Guidelines**:
- **Increase `max_retries`** if your ITSM platform has frequent transient failures
- **Decrease `retry_delay_seconds`** if you need faster failure detection
- **Increase `backoff_multiplier`** to be more conservative during outages
- **Add status codes** to `retryable_status_codes` if your platform uses custom codes

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

**Tuning Guidelines**:
- **Increase `read_timeout_seconds`** if ITSM API responses are slow
- **Decrease `total_timeout_seconds`** if you need strict SLA enforcement
- Keep `total_timeout_seconds` >= `retry_delay_seconds` * `max_retries` + `read_timeout_seconds`

### Creating Custom Templates

Add to `config/itsm_config.json`:

```json
{
  "templates": {
    "servicenow": {
      "my_custom_template": {
        "short_description": "Custom: {title}",
        "description": "Created by: {creator}\nDetails: {details}",
        "priority": "{priority}",
        "category": "Software",
        "assignment_group": "My Team"
      }
    }
  }
}
```

**Template Variables**:
- Use `{variable_name}` syntax for substitution
- Available auto-injected variables: `job_id`, `job_name`, `timestamp`, `severity`, `details`, `system`, `primary_cause`, `evidence`
- Pass custom variables in API request `variables` field

---

## Common Use Cases

### Use Case 1: Create Ticket with Automatic Retry

```python
from core.tickets.service import TicketService

service = TicketService()

# Automatically retries on transient failures
ticket = await service.create_ticket(
    job_id="job-123",
    platform="servicenow",
    payload={"short_description": "Test", "priority": "3"},
    dry_run=False
)

# Check retry metadata
retry_info = ticket.metadata.get("retry_metadata", {})
print(f"Retry attempts: {retry_info.get('retry_attempts', 0)}")
```

### Use Case 2: Validate Payload Before Sending

```python
from core.tickets.validation import validate_ticket_payload

payload = {
    "summary": "My Issue",
    "priority": "InvalidPriority"  # Will fail validation
}

result = validate_ticket_payload("jira", payload)

if not result.valid:
    errors_by_field = result.error_dict()
    # Handle validation errors before attempting creation
    for field, errors in errors_by_field.items():
        for error in errors:
            print(f"{field}: {error['message']}")
```

### Use Case 3: Template-Based Ticket Creation

```python
from core.tickets.service import TicketService

service = TicketService()

ticket = await service.create_from_template(
    job_id="job-456",
    platform="jira",
    template_name="production_incident",
    variables={
        "impact_statement": "Payment processing delayed by 5 minutes",
        "affected_services": "payments, checkout"
    },
    dry_run=False
)

print(f"Created ticket: {ticket.ticket_id}")
```

### Use Case 4: Monitor Metrics

```bash
# View ITSM metrics
curl http://localhost:8001/metrics | grep itsm_

# Example metrics:
# itsm_ticket_creation_total{platform="servicenow",outcome="success"} 142
# itsm_ticket_creation_duration_seconds_sum{platform="servicenow"} 71.3
# itsm_ticket_retry_attempts_total{platform="servicenow"} 12
# itsm_validation_errors_total{platform="jira",field="priority"} 3
```

---

## API Examples

### List Templates (cURL)

```bash
# All templates
curl http://localhost:8000/api/v1/tickets/templates

# ServiceNow only
curl "http://localhost:8000/api/v1/tickets/templates?platform=servicenow"

# Jira only
curl "http://localhost:8000/api/v1/tickets/templates?platform=jira"
```

### Create from Template (Python)

```python
import httpx

async with httpx.AsyncClient() as client:
    response = await client.post(
        "http://localhost:8000/api/v1/tickets/from-template",
        json={
            "job_id": "job-789",
            "platform": "servicenow",
            "template_name": "critical_alert",
            "variables": {
                "alert_name": "High CPU Usage",
                "alert_details": "CPU usage exceeded 90% for 10 minutes"
            },
            "dry_run": False
        },
        headers={"Authorization": f"Bearer {token}"}
    )
    
    ticket = response.json()
    print(f"Ticket ID: {ticket['ticket_id']}")
    print(f"URL: {ticket['url']}")
```

### Create from Template (JavaScript)

```javascript
const response = await fetch('http://localhost:8000/api/v1/tickets/from-template', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${token}`
  },
  body: JSON.stringify({
    job_id: 'job-789',
    platform: 'jira',
    template_name: 'rca_issue',
    variables: {
      additional_context: 'Found during nightly batch'
    },
    dry_run: false
  })
});

const ticket = await response.json();
console.log(`Ticket: ${ticket.ticket_id} - ${ticket.url}`);
```

---

## Troubleshooting

### Problem: Validation Always Fails

**Symptoms**: All ticket creation attempts fail validation with "required_field_missing" errors.

**Solution**:
1. Check that `config/itsm_config.json` has correct `field_mapping` for your platform
2. Verify required fields are present in your payload
3. Use `validate_ticket_payload()` to see specific errors before attempting creation

```python
from core.tickets.validation import validate_ticket_payload

result = validate_ticket_payload("servicenow", your_payload)
for error in result.errors:
    print(f"{error.field}: {error.error_code} - {error.message}")
```

### Problem: Retries Not Working

**Symptoms**: Requests fail immediately without retrying, or retry too many times.

**Solution**:
1. Check `retry_policy` in `config/itsm_config.json`
2. Verify status code is in `retryable_status_codes` list
3. Check logs for retry attempts: `grep "retrying in" app.log`

```bash
# View retry configuration
cat config/itsm_config.json | jq '.retry_policy'

# Check if your error status code is listed
# Add it to retryable_status_codes if needed
```

### Problem: Timeout Too Short

**Symptoms**: Requests fail with "Read timeout" or "Total timeout exceeded" errors.

**Solution**:
1. Increase `read_timeout_seconds` if ITSM API is slow
2. Increase `total_timeout_seconds` if retries are needed
3. Monitor actual request durations: `curl http://localhost:8001/metrics | grep duration`

```json
{
  "timeout": {
    "connection_timeout_seconds": 15,
    "read_timeout_seconds": 45,
    "total_timeout_seconds": 120
  }
}
```

### Problem: Template Variables Not Substituting

**Symptoms**: Ticket contains literal `{variable_name}` instead of actual value.

**Solution**:
1. Ensure variable name matches exactly (case-sensitive)
2. Check template definition in `config/itsm_config.json`
3. Pass variables in `variables` dict when creating from template

```python
# WRONG: Variable name doesn't match template
variables = {"jobId": "123"}  # Template uses {job_id}

# CORRECT: Match template variable names exactly
variables = {"job_id": "123"}
```

### Problem: Missing Metrics

**Symptoms**: Metrics endpoint doesn't show `itsm_*` metrics.

**Solution**:
1. Verify metrics instrumentation is complete (check Phase 3 tasks)
2. Create at least one ticket to generate metrics
3. Check metrics are enabled: `cat core/config.py | grep METRICS_ENABLED`

```bash
# Force metrics generation
curl -X POST http://localhost:8000/api/v1/tickets/from-template \
  -H "Content-Type: application/json" \
  -d '{"job_id":"test","platform":"servicenow","template_name":"rca_incident","dry_run":true}'

# Then check metrics
curl http://localhost:8001/metrics | grep itsm_
```

---

## Next Steps

1. **Test in Development**: Create test tickets with `dry_run: true` to validate configuration
2. **Monitor Metrics**: Set up Grafana dashboard (see `deploy/docker/config/grafana/dashboards/itsm_analytics.json`)
3. **Create Custom Templates**: Add templates for your organization's ticket types
4. **Configure Alerts**: Set up Prometheus alert rules for error rates and SLA violations
5. **Review Documentation**: See `docs/ITSM_INTEGRATION_GUIDE.md` for detailed information

---

## Reference

- **API Specification**: `specs/master/contracts/api-spec.yaml`
- **Data Model**: `specs/master/data-model.md`
- **Configuration**: `config/itsm_config.json`
- **Metrics**: `http://localhost:8001/metrics`
- **Grafana Dashboard**: `http://localhost:3000/d/itsm-analytics`

---

## Support

For issues or questions:
1. Check logs: `docker logs rca-api`
2. Review metrics: `curl http://localhost:8001/metrics | grep itsm_`
3. Validate configuration: `python -c "from core.tickets.validation import TicketPayloadValidator; print(TicketPayloadValidator())"`
4. Open GitHub issue with:
   - Error message
   - Configuration (redact credentials)
   - Retry metadata from ticket.metadata
