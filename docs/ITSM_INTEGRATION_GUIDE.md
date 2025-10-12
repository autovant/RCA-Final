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
