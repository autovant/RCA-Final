# ITSM Integration Guide

## Overview

The RCA Automation Portal now includes comprehensive ITSM (IT Service Management) integrations with **ServiceNow** and **Jira**, enabling automated ticket generation for root cause analysis findings.

### Key Features

- ✅ **ServiceNow Integration**: Create incident tickets with full field mapping
- ✅ **Jira Integration**: Create issue tickets with project tracking
- ✅ **Feature Toggles**: Enable/disable integrations via UI or configuration
- ✅ **Dual-Tracking Mode**: Link Jira issues to ServiceNow incidents
- ✅ **Dry-Run/Preview Mode**: Test ticket creation without external API calls
- ✅ **Real-Time Status Tracking**: Refresh ticket status from external systems
- ✅ **Search & Filter**: Advanced ticket lookup capabilities
- ✅ **Enterprise UI**: Modern dashboard with stats and visual indicators

---

## Architecture

### Backend Components

**Location**: `unified_rca_engine/core/tickets/`

1. **clients.py**: HTTP client adapters for ServiceNow and Jira REST APIs
2. **service.py**: Business logic for ticket creation, listing, and status refresh
3. **settings.py**: Database-backed feature toggle management
4. **models.py**: Database models for tickets and integration settings

### Frontend Components

**Location**: `unified_rca_engine/ui/src/`

1. **types/tickets.ts**: TypeScript interfaces for ticket data structures
2. **lib/api/tickets.ts**: API client for backend ticket endpoints
3. **store/ticketStore.ts**: Zustand state management for tickets
4. **components/tickets/**:
   - `TicketDashboard.tsx`: Main ticket listing with search/filter
   - `TicketSettingsPanel.tsx`: Feature toggle UI
   - `TicketCreationForm.tsx`: Form for manual ticket creation
   - `TicketDetailView.tsx`: Modal for viewing ticket details

---

## Setup Guide

### 1. ServiceNow Configuration

#### Prerequisites
- ServiceNow instance URL (e.g., `https://yourcompany.service-now.com`)
- ServiceNow credentials (username/password or OAuth token)
- Access to Incident table (`incident`)

#### Environment Variables

Add to your `.env` file:

```bash
# ServiceNow Configuration
SERVICENOW_INSTANCE_URL=https://yourcompany.service-now.com
SERVICENOW_USERNAME=your_username
SERVICENOW_PASSWORD=your_password

# Optional: OAuth Configuration
# SERVICENOW_CLIENT_ID=your_client_id
# SERVICENOW_CLIENT_SECRET=your_client_secret
# SERVICENOW_TOKEN_URL=https://yourcompany.service-now.com/oauth_token.do

# ServiceNow Defaults
SERVICENOW_DEFAULT_ASSIGNMENT_GROUP=IT Support
SERVICENOW_DEFAULT_CATEGORY=Software
SERVICENOW_DEFAULT_SUBCATEGORY=Application Error
SERVICENOW_DEFAULT_PRIORITY=3
SERVICENOW_DEFAULT_STATE=1
```

#### ServiceNow API Permissions

Your ServiceNow user must have the following roles:
- `incident_manager` or `itil`
- API read/write access to the Incident table

#### Testing ServiceNow Connection

```bash
curl -X POST "http://localhost:8000/api/v1/tickets/" \
  -H "Content-Type: application/json" \
  -d '{
    "job_id": "test-job-123",
    "platform": "servicenow",
    "payload": {
      "short_description": "Test Incident",
      "description": "Testing ServiceNow integration"
    },
    "dry_run": true
  }'
```

---

### 2. Jira Configuration

#### Prerequisites
- Jira instance URL (Cloud: `https://yourcompany.atlassian.net` or Server/Data Center)
- Jira credentials:
  - **Cloud**: Email + API Token
  - **Server/Data Center**: Username + Password
- Project key (e.g., `PROJ`, `OPS`)

#### Environment Variables

Add to your `.env` file:

```bash
# Jira Configuration
JIRA_BASE_URL=https://yourcompany.atlassian.net
JIRA_EMAIL=your.email@company.com
JIRA_API_TOKEN=your_jira_api_token

# For Jira Server/Data Center, use:
# JIRA_USERNAME=your_username
# JIRA_PASSWORD=your_password

# Jira Defaults
JIRA_DEFAULT_PROJECT_KEY=PROJ
JIRA_DEFAULT_ISSUE_TYPE=Incident
JIRA_DEFAULT_PRIORITY=Medium
```

#### Generating Jira API Token (Cloud)

1. Go to: https://id.atlassian.com/manage-profile/security/api-tokens
2. Click "Create API token"
3. Give it a label (e.g., "RCA Portal")
4. Copy the token and add to `.env`

#### Jira Project Configuration

Ensure your Jira project has:
- Issue type: `Incident` (or update `JIRA_DEFAULT_ISSUE_TYPE`)
- Appropriate permissions for your user to create issues

#### Testing Jira Connection

```bash
curl -X POST "http://localhost:8000/api/v1/tickets/" \
  -H "Content-Type: application/json" \
  -d '{
    "job_id": "test-job-123",
    "platform": "jira",
    "payload": {
      "project_key": "PROJ",
      "summary": "Test Issue",
      "description": "Testing Jira integration"
    },
    "dry_run": true
  }'
```

---

## Feature Toggle Configuration

### Method 1: Database Settings (Recommended)

Feature toggles are stored in the database and can be modified via the UI or API.

**Default State**:
- ServiceNow: Disabled
- Jira: Disabled
- Dual-Tracking Mode: Disabled

**Via UI**:
1. Navigate to Settings > ITSM Integration
2. Toggle ServiceNow and/or Jira switches
3. Enable Dual-Tracking Mode (if both are enabled)
4. Click "Save Changes"

**Via API**:
```bash
curl -X PUT "http://localhost:8000/api/v1/tickets/settings/state" \
  -H "Content-Type: application/json" \
  -d '{
    "servicenow_enabled": true,
    "jira_enabled": true,
    "dual_mode": false
  }'
```

### Method 2: Environment Variables (Initial Setup)

Override initial state with environment variables:

```bash
# Initial toggle states (overrides database on first run)
TICKET_SERVICENOW_ENABLED=true
TICKET_JIRA_ENABLED=true
TICKET_DUAL_MODE_ENABLED=false
```

---

## Usage Guide

### 1. Automatic Ticket Dispatch

When an RCA job completes, you can automatically create tickets in all enabled platforms:

**API Call**:
```bash
curl -X POST "http://localhost:8000/api/v1/tickets/dispatch" \
  -H "Content-Type: application/json" \
  -d '{
    "job_id": "rca-job-456",
    "servicenow_payload": {
      "short_description": "Critical Service Outage",
      "priority": "1"
    },
    "jira_payload": {
      "project_key": "OPS",
      "summary": "Investigate service downtime"
    }
  }'
```

**Response**:
```json
{
  "tickets": [
    {
      "id": "uuid",
      "ticket_id": "INC0010123",
      "platform": "servicenow",
      "status": "New",
      "url": "https://yourcompany.service-now.com/nav_to.do?uri=incident.do?sys_id=...",
      "dry_run": false,
      "created_at": "2024-01-15T10:30:00Z"
    },
    {
      "id": "uuid",
      "ticket_id": "OPS-456",
      "platform": "jira",
      "status": "Open",
      "url": "https://yourcompany.atlassian.net/browse/OPS-456",
      "dry_run": false,
      "metadata": {
        "servicenow_incident_id": "INC0010123"
      },
      "created_at": "2024-01-15T10:30:05Z"
    }
  ]
}
```

### 2. Manual Ticket Creation

Create tickets manually via the UI:

1. Navigate to RCA Job Details page
2. Click "Create Ticket" button
3. Select platform (ServiceNow or Jira)
4. Fill in required fields
5. Toggle "Preview Mode" to test (dry-run)
6. Click "Create Ticket" or "Preview Ticket"

### 3. Viewing Tickets

**Via UI**:
1. Navigate to RCA Job Details
2. Scroll to "ITSM Tickets" section
3. View stats, search, filter by platform/status
4. Click any row to view full ticket details
5. Click "View" to open ticket in external system

**Via API**:
```bash
curl "http://localhost:8000/api/v1/tickets/{job_id}?refresh=true"
```

### 4. Refreshing Ticket Status

Tickets are synced with external systems periodically. To manually refresh:

**Via UI**: Click "Refresh Status" button

**Via API**: Add `?refresh=true` query parameter

---

## Field Mapping

### ServiceNow Fields

| Field | Type | Required | Description | Example |
|-------|------|----------|-------------|---------|
| `short_description` | String | Yes | Brief incident summary | "Production API Gateway Down" |
| `description` | String | No | Detailed description | "API Gateway stopped responding at 10:30 AM EST..." |
| `assignment_group` | String | No | Group to assign incident | "IT Support", "DevOps Team" |
| `assigned_to` | String | No | Individual assignee | "john.doe@company.com" |
| `configuration_item` | String | No | Related CI | "api-gateway-prod-01" |
| `category` | String | No | Incident category | "Software", "Hardware", "Network" |
| `subcategory` | String | No | Incident subcategory | "Application Error", "Performance" |
| `priority` | String | No | Priority level (1-5) | "1" (Critical), "3" (Moderate) |
| `state` | String | No | Incident state (1-7) | "1" (New), "2" (In Progress) |

### Jira Fields

| Field | Type | Required | Description | Example |
|-------|------|----------|-------------|---------|
| `project_key` | String | Yes | Jira project key | "PROJ", "OPS" |
| `summary` | String | Yes | Issue summary | "Investigate API latency spike" |
| `description` | String | No | Detailed description | "API response times increased to 5s average..." |
| `issue_type` | String | No | Jira issue type | "Incident", "Bug", "Task" |
| `assignee` | String | No | Issue assignee | "john.doe" or "john.doe@company.com" |
| `priority` | String | No | Priority name | "Highest", "High", "Medium", "Low" |
| `labels` | Array | No | Issue labels | ["rca", "production", "api"] |

---

## Dual-Tracking Mode

When both ServiceNow and Jira are enabled, you can activate **Dual-Tracking Mode** to create linked tickets:

### How It Works

1. ServiceNow incident is created first
2. Jira issue is created with reference to ServiceNow incident
3. Jira description includes: `Related ServiceNow Incident: INC0010123`
4. Jira metadata stores: `servicenow_incident_id: "INC0010123"`

### Benefits

- **Unified Tracking**: Teams using different tools can see related tickets
- **Cross-Platform Visibility**: Link from Jira issues to ServiceNow incidents
- **Audit Trail**: Complete incident tracking across both systems

### Configuration

**Via UI**:
1. Enable both ServiceNow and Jira toggles
2. Enable "Dual-Tracking Mode" toggle
3. Save changes

**Via API**:
```bash
curl -X PUT "http://localhost:8000/api/v1/tickets/settings/state" \
  -H "Content-Type: application/json" \
  -d '{
    "servicenow_enabled": true,
    "jira_enabled": true,
    "dual_mode": true
  }'
```

---

## API Reference

### Endpoints

#### `POST /api/v1/tickets/`
Create a single ticket on one platform.

**Request Body**:
```json
{
  "job_id": "string",
  "platform": "servicenow" | "jira",
  "payload": { ... },
  "dry_run": false
}
```

#### `POST /api/v1/tickets/dispatch`
Create tickets on all enabled platforms.

**Request Body**:
```json
{
  "job_id": "string",
  "servicenow_payload": { ... },
  "jira_payload": { ... }
}
```

#### `GET /api/v1/tickets/{job_id}`
Get all tickets for a job.

**Query Parameters**:
- `refresh` (boolean): Refresh status from external systems

#### `GET /api/v1/tickets/settings/state`
Get current feature toggle state.

**Response**:
```json
{
  "servicenow_enabled": true,
  "jira_enabled": true,
  "dual_mode": false
}
```

#### `PUT /api/v1/tickets/settings/state`
Update feature toggle configuration.

**Request Body**:
```json
{
  "servicenow_enabled": true,
  "jira_enabled": false,
  "dual_mode": false
}
```

---

## Troubleshooting

### Common Issues

#### 1. ServiceNow: Authentication Failed

**Error**: `401 Unauthorized`

**Solution**:
- Verify `SERVICENOW_USERNAME` and `SERVICENOW_PASSWORD` are correct
- Check user has `incident_manager` or `itil` role
- For OAuth: Verify client credentials and token URL

#### 2. Jira: Project Not Found

**Error**: `Project 'PROJ' does not exist or you do not have permission to view it`

**Solution**:
- Verify project key is correct (case-sensitive)
- Ensure your Jira user has "Create Issues" permission
- For Jira Cloud: Use email + API token, not username + password

#### 3. Tickets Not Creating

**Symptoms**: Toggle enabled but tickets not being created

**Solution**:
1. Check feature toggle state: `GET /api/v1/tickets/settings/state`
2. Enable dry-run mode to test without external calls
3. Check backend logs for errors
4. Verify environment variables are loaded correctly

#### 4. Status Refresh Not Working

**Symptoms**: Ticket status not updating

**Solution**:
- Ensure ticket was created (not in dry-run mode)
- Check `ticket.url` is valid
- ServiceNow: Verify incident exists and is accessible
- Jira: Verify issue key is valid and accessible

### Debug Mode

Enable debug logging in backend:

```bash
# In .env
LOG_LEVEL=DEBUG
```

View logs:
```bash
tail -f logs/unified_rca_engine.log
```

### Testing Connectivity

Use the dry-run mode to test without creating real tickets:

```bash
# Test ServiceNow
curl -X POST "http://localhost:8000/api/v1/tickets/" \
  -H "Content-Type: application/json" \
  -d '{
    "job_id": "test",
    "platform": "servicenow",
    "payload": {"short_description": "Test"},
    "dry_run": true
  }'

# Test Jira
curl -X POST "http://localhost:8000/api/v1/tickets/" \
  -H "Content-Type: application/json" \
  -d '{
    "job_id": "test",
    "platform": "jira",
    "payload": {"project_key": "PROJ", "summary": "Test"},
    "dry_run": true
  }'
```

---

## Security Best Practices

1. **Never commit credentials** to version control
2. Use **environment variables** for all sensitive data
3. Use **API tokens** instead of passwords where possible
4. Implement **rate limiting** for ticket creation endpoints
5. Use **HTTPS** for all external API calls
6. Rotate credentials regularly
7. Use **OAuth 2.0** for ServiceNow if available
8. Restrict API access to authorized users only

---

## Advanced Configuration

### Custom Field Mapping

Extend field mapping in `unified_rca_engine/core/tickets/clients.py`:

```python
# ServiceNow custom fields
servicenow_payload = {
    **servicenow_payload,
    "u_custom_field": "custom_value",
    "u_business_service": "Web Application"
}

# Jira custom fields
jira_payload["fields"]["customfield_10001"] = "custom_value"
```

### Webhook Integration

Configure webhooks for real-time ticket updates:

```python
# In ServiceNow Business Rule or Flow
# POST to: http://your-rca-portal.com/api/v1/webhooks/servicenow
{
    "incident_id": "INC0010123",
    "state": "In Progress",
    "assigned_to": "john.doe"
}
```

### Custom Status Mapping

Modify status mapping in `unified_rca_engine/core/tickets/clients.py`:

```python
STATUS_MAP = {
    "1": "New",
    "2": "In Progress",
    "3": "On Hold",
    "6": "Resolved",
    "7": "Closed",
}
```

---

## Retry and Timeout Configuration

The ITSM integration includes robust retry logic and timeout handling to ensure reliable ticket creation even during network issues or service degradation.

### Retry Configuration

**Default Settings:**
```python
MAX_RETRIES = 3              # Maximum number of retry attempts
RETRY_DELAY = 1.0            # Initial delay between retries (seconds)
RETRY_BACKOFF = 2.0          # Exponential backoff multiplier
```

**Environment Variables:**
```bash
# Retry Configuration
ITSM_MAX_RETRIES=3
ITSM_RETRY_DELAY=1.0
ITSM_RETRY_BACKOFF=2.0
```

**Retry Behavior:**
- Initial attempt fails → Wait 1 second
- First retry fails → Wait 2 seconds (1 × 2^1)
- Second retry fails → Wait 4 seconds (1 × 2^2)
- Third retry fails → Return error

**Retryable Errors:**
- `429 Too Many Requests` - Rate limit exceeded
- `500 Internal Server Error` - Temporary server issues
- `502 Bad Gateway` - Upstream service unavailable
- `503 Service Unavailable` - Service temporarily down
- `504 Gateway Timeout` - Request timeout
- Network connection errors

**Non-Retryable Errors:**
- `400 Bad Request` - Invalid payload
- `401 Unauthorized` - Authentication failure
- `403 Forbidden` - Permission denied
- `404 Not Found` - Resource not found

### Timeout Configuration

**Default Timeouts:**
```python
CONNECTION_TIMEOUT = 10      # Connection establishment timeout (seconds)
READ_TIMEOUT = 30            # Response read timeout (seconds)
TOTAL_TIMEOUT = 60           # Total request timeout (seconds)
```

**Environment Variables:**
```bash
# Timeout Configuration
SERVICENOW_TIMEOUT=30
JIRA_TIMEOUT=30
```

**Timeout Behavior:**
- If request exceeds timeout → Retry (if retries remaining)
- If all retries exhausted → Return timeout error
- Metrics track timeout occurrences

### Monitoring Retry Behavior

Retry attempts are tracked via Prometheus metrics:
```promql
# Total retry attempts by platform
itsm_ticket_retry_attempts_total{platform="servicenow"}
itsm_ticket_retry_attempts_total{platform="jira"}

# Alert on excessive retries
rate(itsm_ticket_retry_attempts_total[5m]) > 10
```

---

## Validation Rules

The ITSM integration validates all ticket payloads before submission to external systems. Validation errors are returned with detailed field-level feedback.

### ServiceNow Validation Rules

**Required Fields:**
- `short_description` - Must be non-empty string (max 160 characters)

**Optional Fields with Validation:**
- `description` - String (max 4000 characters)
- `priority` - Must be one of: `1`, `2`, `3`, `4`, `5`
- `state` - Must be one of: `1`, `2`, `3`, `4`, `6`, `7`
- `assignment_group` - String (max 80 characters)
- `assigned_to` - Valid user ID or email
- `configuration_item` - Valid CI name or sys_id
- `category` - String (max 50 characters)
- `subcategory` - String (max 50 characters)

**Example Validation Error:**
```json
{
  "detail": "Validation failed",
  "validation_errors": [
    {
      "field": "short_description",
      "message": "Field is required and cannot be empty"
    },
    {
      "field": "priority",
      "message": "Must be one of: 1, 2, 3, 4, 5"
    }
  ]
}
```

### Jira Validation Rules

**Required Fields:**
- `project_key` - Must exist in Jira instance
- `summary` - Must be non-empty string (max 255 characters)

**Optional Fields with Validation:**
- `description` - String (Jira Markdown format)
- `issue_type` - Must exist in project (default: `Incident`)
- `priority` - Must be valid priority name (e.g., `High`, `Medium`, `Low`)
- `assignee` - Valid Jira username or account ID
- `labels` - Array of strings (alphanumeric + hyphens/underscores)
- `components` - Array of objects with `name` property

**Example Validation Error:**
```json
{
  "detail": "Validation failed",
  "validation_errors": [
    {
      "field": "project_key",
      "message": "Project key is required"
    },
    {
      "field": "labels",
      "message": "Labels must contain only alphanumeric characters, hyphens, and underscores"
    }
  ]
}
```

### Custom Validation Logic

Location: `core/tickets/validation.py`

```python
def validate_ticket_payload(platform: str, payload: Dict[str, Any]) -> ValidationResult:
    """
    Validates ticket payload based on platform-specific rules.
    
    Returns:
        ValidationResult with is_valid flag and list of FieldError objects
    """
    pass
```

---

## Template Usage

Templates allow you to create tickets from pre-configured blueprints with variable substitution, reducing manual data entry and ensuring consistency.

### Template Structure

Templates are defined in `config/itsm_config.json`:

```json
{
  "templates": {
    "servicenow": [
      {
        "name": "production_incident",
        "description": "Template for production incidents",
        "required_variables": ["service_name", "error_message"],
        "payload": {
          "short_description": "Production Incident: {service_name}",
          "description": "Error: {error_message}\n\nEnvironment: Production",
          "priority": "1",
          "state": "2",
          "category": "Software",
          "subcategory": "Application Error"
        }
      }
    ],
    "jira": [
      {
        "name": "bug_report",
        "description": "Standard bug report template",
        "required_variables": ["component", "bug_description"],
        "payload": {
          "issue_type": "Bug",
          "summary": "Bug in {component}",
          "description": "{bug_description}",
          "priority": "High",
          "labels": ["bug", "production"]
        }
      }
    ]
  }
}
```

### Using Templates via API

**List Available Templates:**
```bash
curl "http://localhost:8000/api/v1/tickets/templates?platform=servicenow"
```

**Response:**
```json
{
  "templates": [
    {
      "name": "production_incident",
      "platform": "servicenow",
      "description": "Template for production incidents",
      "required_variables": ["service_name", "error_message"],
      "field_count": 6
    }
  ],
  "count": 1
}
```

**Create Ticket from Template:**
```bash
curl -X POST "http://localhost:8000/api/v1/tickets/from-template" \
  -H "Content-Type: application/json" \
  -d '{
    "job_id": "job-123",
    "platform": "servicenow",
    "template_name": "production_incident",
    "variables": {
      "service_name": "Payment API",
      "error_message": "Database connection timeout"
    },
    "dry_run": false
  }'
```

**Response:**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "job_id": "job-123",
  "platform": "servicenow",
  "ticket_id": "INC0012345",
  "url": "https://yourcompany.service-now.com/incident.do?sys_id=abc123",
  "status": "New",
  "template_name": "production_incident",
  "created_at": "2025-10-12T10:30:00Z"
}
```

### Using Templates via UI

1. Open Ticket Creation Form
2. Check "Use Template" toggle
3. Select template from dropdown (filtered by platform)
4. Fill in required variables
5. Preview shows variable substitution
6. Submit to create ticket

### Template Rendering Errors

If template rendering fails, the error is tracked:
```promql
itsm_template_rendering_errors_total{template_name="production_incident"}
```

---

## API Endpoints

### Ticket Management Endpoints

#### Create Ticket
```http
POST /api/v1/tickets/
Content-Type: application/json

{
  "job_id": "string",
  "platform": "servicenow" | "jira",
  "payload": { /* platform-specific fields */ },
  "profile_name": "string (optional)",
  "dry_run": boolean
}
```

**Response:** `201 Created` with ticket object

---

#### List Job Tickets
```http
GET /api/v1/tickets/{job_id}?refresh=false
```

**Query Parameters:**
- `refresh` (optional): If `true`, fetch latest status from external systems

**Response:** `200 OK` with ticket list

---

#### Get Template List
```http
GET /api/v1/tickets/templates?platform=servicenow
```

**Query Parameters:**
- `platform` (optional): Filter by platform (`servicenow` or `jira`)

**Response:** `200 OK`
```json
{
  "templates": [
    {
      "name": "string",
      "platform": "servicenow" | "jira",
      "description": "string",
      "required_variables": ["string"],
      "field_count": number
    }
  ],
  "count": number
}
```

---

#### Create from Template
```http
POST /api/v1/tickets/from-template
Content-Type: application/json

{
  "job_id": "string",
  "platform": "servicenow" | "jira",
  "template_name": "string",
  "variables": { "key": "value" },
  "profile_name": "string (optional)",
  "dry_run": boolean
}
```

**Response:** `201 Created`
```json
{
  "id": "uuid",
  "job_id": "string",
  "platform": "servicenow" | "jira",
  "ticket_id": "string",
  "url": "string",
  "status": "string",
  "template_name": "string",
  "created_at": "ISO 8601 timestamp"
}
```

**Error Responses:**
- `404 Not Found` - Job or template not found
- `400 Bad Request` - Validation errors or missing variables
- `500 Internal Server Error` - External API errors

---

### Feature Toggle Endpoints

#### Get Toggle State
```http
GET /api/v1/tickets/toggle
```

**Response:** `200 OK`
```json
{
  "servicenow_enabled": boolean,
  "jira_enabled": boolean,
  "dual_mode": boolean
}
```

---

#### Update Toggle State
```http
PUT /api/v1/tickets/toggle
Content-Type: application/json

{
  "servicenow_enabled": boolean,
  "jira_enabled": boolean,
  "dual_mode": boolean
}
```

**Response:** `200 OK` with updated toggle state

---

## Metrics and Monitoring

The ITSM integration exposes comprehensive Prometheus metrics for monitoring ticket operations, performance, and errors.

### Available Metrics

#### 1. Ticket Creation Total
```promql
itsm_ticket_creation_total{platform="servicenow|jira", outcome="success|failure"}
```
**Type:** Counter  
**Labels:** `platform`, `outcome`  
**Description:** Total number of ticket creation attempts by platform and outcome

**Example Queries:**
```promql
# Success rate by platform
rate(itsm_ticket_creation_total{outcome="success"}[5m])
  / rate(itsm_ticket_creation_total[5m])

# Error rate
rate(itsm_ticket_creation_total{outcome="failure"}[5m])
```

---

#### 2. Ticket Creation Duration
```promql
itsm_ticket_creation_duration_seconds{platform="servicenow|jira", outcome="success|failure"}
```
**Type:** Histogram  
**Labels:** `platform`, `outcome`  
**Buckets:** `[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0]`  
**Description:** Duration of ticket creation operations in seconds

**Example Queries:**
```promql
# p95 latency by platform
histogram_quantile(0.95, 
  rate(itsm_ticket_creation_duration_seconds_bucket[5m])
)

# Average duration
rate(itsm_ticket_creation_duration_seconds_sum[5m])
  / rate(itsm_ticket_creation_duration_seconds_count[5m])
```

---

#### 3. Retry Attempts
```promql
itsm_ticket_retry_attempts_total{platform="servicenow|jira"}
```
**Type:** Counter  
**Labels:** `platform`  
**Description:** Total number of retry attempts for failed ticket operations

**Example Queries:**
```promql
# Retry rate over last 5 minutes
rate(itsm_ticket_retry_attempts_total[5m])

# Total retries by platform
sum by (platform) (itsm_ticket_retry_attempts_total)
```

---

#### 4. Validation Errors
```promql
itsm_validation_errors_total{platform="servicenow|jira", field="string"}
```
**Type:** Counter  
**Labels:** `platform`, `field`  
**Description:** Total validation errors by platform and field name

**Example Queries:**
```promql
# Top 10 validation errors
topk(10, sum by (field) (itsm_validation_errors_total))

# Validation error rate
rate(itsm_validation_errors_total[5m])
```

---

#### 5. Template Rendering Errors
```promql
itsm_template_rendering_errors_total{template_name="string"}
```
**Type:** Counter  
**Labels:** `template_name`  
**Description:** Total template rendering errors by template name

**Example Queries:**
```promql
# Templates with rendering errors
sum by (template_name) (itsm_template_rendering_errors_total)
```

---

#### 6. Time to Acknowledge (SLA)
```promql
itsm_ticket_time_to_acknowledge_seconds{platform="servicenow|jira"}
```
**Type:** Histogram  
**Labels:** `platform`  
**Buckets:** `[60, 300, 600, 1800, 3600, 7200, 14400, 28800, 86400]` (1m to 1d)  
**Description:** Time from ticket creation to acknowledgement in seconds

**Example Queries:**
```promql
# p95 time to acknowledge
histogram_quantile(0.95,
  rate(itsm_ticket_time_to_acknowledge_seconds_bucket[1h])
)
```

---

#### 7. Time to Resolve (SLA)
```promql
itsm_ticket_time_to_resolve_seconds{platform="servicenow|jira"}
```
**Type:** Histogram  
**Labels:** `platform`  
**Buckets:** `[300, 1800, 3600, 7200, 14400, 28800, 86400, 172800, 604800]` (5m to 1w)  
**Description:** Time from ticket creation to resolution in seconds

**Example Queries:**
```promql
# Average time to resolve
rate(itsm_ticket_time_to_resolve_seconds_sum[1h])
  / rate(itsm_ticket_time_to_resolve_seconds_count[1h])
```

---

## Grafana Dashboard

A pre-built Grafana dashboard is available at `deploy/docker/config/grafana/dashboards/itsm_analytics.json`.

### Dashboard Panels

#### Panel 1: Ticket Creation Rate
**Type:** Time Series  
**Query:**
```promql
sum by (platform, outcome) (
  rate(itsm_ticket_creation_total[5m])
)
```
**Description:** Shows ticket creation rate by platform with success/failure breakdown

---

#### Panel 2: Duration Percentiles
**Type:** Time Series  
**Queries:**
```promql
# p50
histogram_quantile(0.50, sum by (le, platform) (
  rate(itsm_ticket_creation_duration_seconds_bucket[5m])
))

# p95
histogram_quantile(0.95, sum by (le, platform) (
  rate(itsm_ticket_creation_duration_seconds_bucket[5m])
))

# p99
histogram_quantile(0.99, sum by (le, platform) (
  rate(itsm_ticket_creation_duration_seconds_bucket[5m])
))
```
**Thresholds:** Green <2s, Yellow <5s, Red ≥5s

---

#### Panel 3: Error Rate
**Type:** Area Chart  
**Query:**
```promql
sum by (platform) (
  rate(itsm_ticket_creation_total{outcome="failure"}[5m])
) / sum by (platform) (
  rate(itsm_ticket_creation_total[5m])
) * 100
```
**Thresholds:** Green <1%, Yellow <5%, Orange <10%, Red ≥10%

---

#### Panel 4: Retry Attempts
**Type:** Stacked Bar Chart  
**Query:**
```promql
sum by (platform) (
  increase(itsm_ticket_retry_attempts_total[5m])
)
```

---

#### Panel 5: Top Validation Errors
**Type:** Donut Chart  
**Query:**
```promql
topk(10, sum by (platform, field) (
  itsm_validation_errors_total
))
```

---

#### Panel 6: Template Rendering Errors
**Type:** Bar Chart  
**Query:**
```promql
sum by (template_name) (
  itsm_template_rendering_errors_total
)
```

---

#### Panel 7: Operations Summary
**Type:** Gauge  
**Metrics:**
- Total tickets created (last 1h)
- Error rate (%)
- Average duration (seconds)
- Total retries
- Validation errors

---

## Prometheus Alerts

Pre-configured alerts are available in `deploy/docker/config/alert_rules.yml`.

### Alert: HighITSMErrorRate
**Severity:** Warning  
**Condition:** Error rate > 5% for 5 minutes  
**Query:**
```promql
sum by (platform) (
  rate(itsm_ticket_creation_total{outcome="failure"}[5m])
) / sum by (platform) (
  rate(itsm_ticket_creation_total[5m])
) > 0.05
```
**Runbook:** Check ITSM platform status, review logs, verify credentials

---

### Alert: CriticalITSMErrorRate
**Severity:** Critical  
**Condition:** Error rate > 25% for 2 minutes  
**Action:** Immediate investigation required

---

### Alert: ExcessiveITSMRetries
**Severity:** Warning  
**Condition:** >50 retries/minute for 5 minutes  
**Action:** Check network connectivity, external service status

---

### Alert: ValidationFailureSpike
**Severity:** Warning  
**Condition:** >10 validation errors/minute for 3 minutes  
**Action:** Review recent payload changes, check template configurations

---

### Alert: TemplateRenderingFailures
**Severity:** Warning  
**Condition:** Any template rendering errors for 1 minute  
**Action:** Review template configuration and variable inputs

---

### Alert: SlowITSMTicketCreation
**Severity:** Warning  
**Condition:** p95 latency > 5 seconds for 5 minutes  
**Action:** Check external service performance, review timeout settings

---

### Alert: NoITSMActivity
**Severity:** Info  
**Condition:** No tickets created for 30 minutes  
**Action:** Verify expected activity levels, check feature toggles

---

## Performance Considerations

- **Ticket Creation**: ~1-3 seconds per platform
- **Status Refresh**: ~0.5-1 second per ticket
- **Bulk Dispatch**: Sequential creation (ServiceNow → Jira)
- **Rate Limits**: Respect external API rate limits
  - ServiceNow: Typically 1000 requests/hour
  - Jira Cloud: 10,000 requests/hour (or 150/second for GraphQL)

### Optimization Tips

1. Use `dry_run: true` for testing
2. Cache ticket data locally
3. Batch status refresh operations
4. Implement background workers for ticket creation
5. Use webhooks instead of polling for status updates

---

## License

This ITSM integration is part of the Unified RCA Engine project.

---

## Support

For issues or questions:
1. Check this documentation
2. Review backend logs
3. Test with dry-run mode
4. Contact your system administrator
