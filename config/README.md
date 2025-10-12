# ITSM Configuration

This directory contains configuration files for the ITSM integration system.

## Files

### `itsm_config.json`

Comprehensive configuration template for ServiceNow and Jira integrations, including:

- **Field Mappings**: Complete field definitions for both platforms
- **Defaults**: Default values for ticket creation
- **Templates**: Pre-configured ticket templates for common scenarios
- **Validation Rules**: Field validation configuration
- **API Settings**: Endpoint URLs and timeout configurations
- **Retry Policy**: Error handling and retry logic

## Usage

### Loading Configuration

The configuration is automatically loaded by the ticket service at startup:

```python
from unified_rca_engine.core.tickets.config import load_itsm_config

config = load_itsm_config()
servicenow_defaults = config['servicenow']['defaults']
jira_defaults = config['jira']['defaults']
```

### Customizing Templates

Edit the `templates` section in `itsm_config.json`:

```json
{
  "templates": {
    "servicenow": {
      "custom_template": {
        "short_description": "Custom: {title}",
        "description": "{details}",
        "priority": "2"
      }
    }
  }
}
```

Use templates in ticket creation:

```python
from unified_rca_engine.core.tickets.service import TicketService

ticket_service = TicketService()
ticket = ticket_service.create_from_template(
    job_id="job-123",
    template_name="custom_template",
    variables={"title": "API Failure", "details": "..."}
)
```

### Adding Custom Fields

For ServiceNow custom fields (prefixed with `u_`):

```json
{
  "servicenow": {
    "custom_fields": {
      "u_business_service": {
        "type": "reference",
        "table": "cmdb_ci_service",
        "description": "Related business service"
      }
    }
  }
}
```

For Jira custom fields (use field ID from Jira):

```json
{
  "jira": {
    "custom_fields": {
      "customfield_10042": {
        "type": "string",
        "description": "Incident severity"
      }
    }
  }
}
```

### Validation Rules

Enable/disable field validation:

```json
{
  "validation": {
    "enabled": true,
    "rules": {
      "servicenow": {
        "validate_assignment_group": true,
        "validate_configuration_item": false
      }
    }
  }
}
```

### Retry Policy

Configure retry behavior for API failures:

```json
{
  "retry_policy": {
    "max_retries": 3,
    "retry_delay_seconds": 5,
    "exponential_backoff": true,
    "retryable_status_codes": [429, 500, 502, 503]
  }
}
```

## Environment Variables vs Configuration File

**Use Environment Variables for:**
- Credentials (username, password, tokens)
- Instance URLs
- Secrets

**Use Configuration File for:**
- Field mappings
- Default values
- Templates
- Validation rules
- Retry policies

## Security Notes

- ⚠️ **Never** store credentials in this configuration file
- Keep all sensitive data in environment variables or secrets manager
- The configuration file can be committed to version control
- Use `.env` files for local development credentials

## Customization Examples

### Example 1: Custom Priority Mapping

```json
{
  "servicenow": {
    "field_mapping": {
      "priority": {
        "values": {
          "1": "P0 - Critical",
          "2": "P1 - High", 
          "3": "P2 - Medium",
          "4": "P3 - Low"
        }
      }
    }
  }
}
```

### Example 2: Default Labels

```json
{
  "jira": {
    "defaults": {
      "labels": ["rca", "automated", "production", "monitoring"]
    }
  }
}
```

### Example 3: Template with Variables

```json
{
  "templates": {
    "servicenow": {
      "database_incident": {
        "short_description": "Database {db_name} - {issue_type}",
        "description": "Database Issue Detected\n\nDatabase: {db_name}\nHost: {db_host}\nIssue: {issue_type}\nMetrics:\n{metrics}\n\nAutomated RCA Job: {job_id}",
        "category": "Database",
        "priority": "2"
      }
    }
  }
}
```

## Related Documentation

- **Setup Guide**: `../docs/ITSM_INTEGRATION_GUIDE.md`
- **Quick Start**: `../docs/ITSM_QUICKSTART.md`
- **Environment Variables**: `../.env.example`

## Troubleshooting

### Configuration Not Loading

Check that the file is valid JSON:
```bash
python -m json.tool config/itsm_config.json
```

### Invalid Field Mappings

Verify field names match your ServiceNow/Jira instance:
- ServiceNow: Check via System Dictionary
- Jira: Check via REST API: `/rest/api/3/issue/createmeta`

### Template Variables Not Substituting

Ensure variable names match exactly:
```python
# Correct
variables = {"db_name": "prod-db-01"}

# Incorrect - won't match {db_name}
variables = {"dbName": "prod-db-01"}
```
