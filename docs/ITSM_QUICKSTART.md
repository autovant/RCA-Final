# ITSM Integration Quick Start Guide

Get up and running with ServiceNow and Jira ticket integrations in 10 minutes.

## Prerequisites

- RCA Automation Portal installed and running
- ServiceNow instance URL and credentials OR Jira instance URL and API token
- Access to create incidents/issues in your ITSM platforms

## Step 1: Configure Environment Variables

### For ServiceNow

```bash
# Copy example environment file
cp .env.example .env

# Edit .env and add:
SERVICENOW_INSTANCE_URL=https://yourcompany.service-now.com
SERVICENOW_USERNAME=your_username
SERVICENOW_PASSWORD=your_password
SERVICENOW_DEFAULT_ASSIGNMENT_GROUP=IT Support
```

### For Jira

```bash
# Add to .env:
JIRA_BASE_URL=https://yourcompany.atlassian.net
JIRA_EMAIL=your.email@company.com
JIRA_API_TOKEN=your_api_token
JIRA_DEFAULT_PROJECT_KEY=PROJ
```

**Getting Jira API Token:**
1. Go to: https://id.atlassian.com/manage-profile/security/api-tokens
2. Click "Create API token"
3. Copy and paste into `.env`

## Step 2: Enable Feature Toggles

### Option A: Via UI (Recommended)

1. Start the application:
   ```bash
   # Backend
   cd unified_rca_engine
   python -m uvicorn apps.api.main:app --reload
   
   # Frontend
   cd ui
   npm run dev
   ```

2. Navigate to: `http://localhost:3000/settings/itsm`

3. Toggle on ServiceNow and/or Jira

4. Click "Save Changes"

### Option B: Via API

```bash
curl -X PUT "http://localhost:8000/api/v1/tickets/settings/state" \
  -H "Content-Type: application/json" \
  -d '{
    "servicenow_enabled": true,
    "jira_enabled": true,
    "dual_mode": false
  }'
```

### Option C: Via Environment Variables

```bash
# Add to .env:
TICKET_SERVICENOW_ENABLED=true
TICKET_JIRA_ENABLED=true
TICKET_DUAL_MODE_ENABLED=false
```

## Step 3: Test Connection (Dry Run)

Test without creating real tickets:

### Test ServiceNow

```bash
curl -X POST "http://localhost:8000/api/v1/tickets/" \
  -H "Content-Type: application/json" \
  -d '{
    "job_id": "test-job-123",
    "platform": "servicenow",
    "payload": {
      "short_description": "Test Incident from RCA Portal"
    },
    "dry_run": true
  }'
```

**Expected Response:**
```json
{
  "id": "uuid",
  "ticket_id": "DRY-RUN-SNOW-xxx",
  "platform": "servicenow",
  "status": "dry-run",
  "dry_run": true
}
```

### Test Jira

```bash
curl -X POST "http://localhost:8000/api/v1/tickets/" \
  -H "Content-Type: application/json" \
  -d '{
    "job_id": "test-job-123",
    "platform": "jira",
    "payload": {
      "project_key": "PROJ",
      "summary": "Test Issue from RCA Portal"
    },
    "dry_run": true
  }'
```

## Step 4: Create Your First Real Ticket

### Via UI

1. Open RCA job details page
2. Click "Create Ticket" button
3. Select platform (ServiceNow or Jira)
4. Fill in required fields:
   - **ServiceNow**: Short Description
   - **Jira**: Project Key, Summary
5. **Uncheck** "Preview Mode" toggle
6. Click "Create Ticket"

### Via API

**ServiceNow:**
```bash
curl -X POST "http://localhost:8000/api/v1/tickets/" \
  -H "Content-Type: application/json" \
  -d '{
    "job_id": "rca-job-456",
    "platform": "servicenow",
    "payload": {
      "short_description": "Production API Gateway Outage",
      "description": "API Gateway stopped responding at 10:30 AM",
      "priority": "1",
      "assignment_group": "DevOps Team"
    },
    "dry_run": false
  }'
```

**Jira:**
```bash
curl -X POST "http://localhost:8000/api/v1/tickets/" \
  -H "Content-Type: application/json" \
  -d '{
    "job_id": "rca-job-456",
    "platform": "jira",
    "payload": {
      "project_key": "OPS",
      "summary": "Investigate API Gateway Outage",
      "description": "Gateway failed health checks at 10:30 AM",
      "priority": "Highest",
      "labels": ["production", "api", "outage"]
    },
    "dry_run": false
  }'
```

## Step 5: Verify Ticket Creation

### Via UI

1. Navigate to RCA job details
2. Scroll to "ITSM Tickets" section
3. See your newly created ticket
4. Click row to view details
5. Click "View" to open in external system

### Via API

```bash
curl "http://localhost:8000/api/v1/tickets/rca-job-456"
```

**Response:**
```json
{
  "tickets": [
    {
      "id": "uuid",
      "ticket_id": "INC0010123",
      "platform": "servicenow",
      "status": "New",
      "url": "https://yourcompany.service-now.com/...",
      "created_at": "2024-01-15T10:35:00Z"
    }
  ]
}
```

## Step 6: Enable Dual-Tracking (Optional)

If using both ServiceNow and Jira:

1. Ensure both toggles are enabled
2. Enable "Dual-Tracking Mode" toggle
3. Save changes

Now when you dispatch tickets, Jira issues will automatically reference their ServiceNow incidents:

```bash
curl -X POST "http://localhost:8000/api/v1/tickets/dispatch" \
  -H "Content-Type: application/json" \
  -d '{
    "job_id": "rca-job-789",
    "servicenow_payload": {
      "short_description": "Database Performance Degradation"
    },
    "jira_payload": {
      "project_key": "OPS",
      "summary": "DB Performance Issue"
    }
  }'
```

The Jira issue will contain: `Related ServiceNow Incident: INC0010124`

## Common Issues & Solutions

### Issue: 401 Unauthorized (ServiceNow)

**Solution:**
- Check username and password are correct
- Verify user has `incident_manager` or `itil` role
- Try accessing ServiceNow web UI with same credentials

### Issue: Project not found (Jira)

**Solution:**
- Verify project key is correct (case-sensitive: `PROJ` not `proj`)
- Check your Jira user has "Create Issues" permission
- For Cloud: Use email + API token, NOT username + password

### Issue: Tickets not creating

**Solution:**
1. Check toggle state: `GET /api/v1/tickets/settings/state`
2. Review backend logs: `tail -f logs/unified_rca_engine.log`
3. Test with dry-run mode first
4. Verify environment variables loaded: 
   ```python
   from core.config import settings
   print(settings.servicenow.instance_url)
   ```

### Issue: Module not found errors

**Solution:**
```bash
# Install dependencies
cd unified_rca_engine
pip install -r requirements.txt

cd ui
npm install
```

## Next Steps

✅ **You're ready to go!** Your ITSM integration is configured.

**Explore more:**
- Read full documentation: `docs/ITSM_INTEGRATION_GUIDE.md`
- Customize field mappings: `config/itsm_config.json`
- Set up webhooks for real-time updates
- Create custom templates for common incident types
- Integrate with alerting systems for automated ticket creation

## Quick Reference

### API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/tickets/` | POST | Create single ticket |
| `/api/v1/tickets/dispatch` | POST | Create tickets on all enabled platforms |
| `/api/v1/tickets/{job_id}` | GET | List all tickets for job |
| `/api/v1/tickets/settings/state` | GET | Get toggle state |
| `/api/v1/tickets/settings/state` | PUT | Update toggles |

### Field Quick Reference

**ServiceNow Required:**
- `short_description` (string, max 160 chars)

**Jira Required:**
- `project_key` (string, e.g., "PROJ")
- `summary` (string, max 255 chars)

**Common Optional Fields:**
- `description` (detailed info)
- `priority` (ServiceNow: 1-5, Jira: Highest/High/Medium/Low/Lowest)
- `assignee` (username or email)

## Support

Need help?
- Check full docs: `docs/ITSM_INTEGRATION_GUIDE.md`
- Review logs: `logs/unified_rca_engine.log`
- Test with dry-run: `"dry_run": true`
- Contact your system administrator

---

**Congratulations!** 🎉 You've successfully set up ITSM integrations.
