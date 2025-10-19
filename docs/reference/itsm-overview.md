# ITSM Integration for RCA Automation Portal

Complete ServiceNow and Jira ticket integration system for automated incident management and tracking.

## 🎯 Overview

This comprehensive ITSM integration enables the RCA Automation Portal to automatically create, track, and manage tickets in ServiceNow and Jira. Built with enterprise-grade features including feature toggles, dual-tracking mode, and a modern React UI.

## ✨ Features

### Core Capabilities
- ✅ **ServiceNow Integration**: Full incident management with field mapping
- ✅ **Jira Integration**: Issue creation with project tracking and labels
- ✅ **Feature Toggles**: Enable/disable integrations via UI or configuration
- ✅ **Dual-Tracking Mode**: Link Jira issues to ServiceNow incidents
- ✅ **Dry-Run/Preview Mode**: Test without creating real tickets
- ✅ **Real-Time Status Sync**: Refresh ticket status from external systems

### UI Components
- 🎨 **Modern Dashboard**: Stats, search, filters, and visual indicators
- ⚙️ **Settings Panel**: Toggle ServiceNow and Jira integrations
- 📝 **Creation Form**: Dynamic form with platform-specific fields
- 🔍 **Detail View**: Complete ticket information and external links
- 🔄 **Auto-Refresh**: Configurable periodic status updates

### Technical Features
- 🔐 **Secure**: Credentials in environment variables only
- 🚀 **Performance**: Async operations with retry logic
- 📊 **State Management**: Zustand store for React state
- 🎯 **Type-Safe**: Full TypeScript support
- 🔧 **Configurable**: JSON-based field mapping and templates

## 📦 What's Included

### Backend Components
```
unified_rca_engine/
├── core/
│   └── tickets/
│       ├── clients.py          # ServiceNow & Jira API clients
│       ├── service.py          # Ticket business logic
│       ├── settings.py         # Feature toggle management
│       └── __init__.py
├── apps/api/routers/
│   └── tickets.py              # REST API endpoints
└── core/db/
    └── models.py               # Database models
```

### Frontend Components
```
ui/src/
├── components/tickets/
│   ├── TicketDashboard.tsx     # Main ticket listing
│   ├── TicketSettingsPanel.tsx # Feature toggles UI
│   ├── TicketCreationForm.tsx  # Ticket creation form
│   ├── TicketDetailView.tsx    # Detail modal view
│   └── index.ts                # Barrel exports
├── lib/
│   ├── api/tickets.ts          # API client
│   └── utils/ticketUtils.ts    # Utility functions
├── store/
│   └── ticketStore.ts          # Zustand state management
└── types/
    └── tickets.ts              # TypeScript types
```

### Configuration & Documentation
```
unified_rca_engine/
├── config/
│   ├── itsm_config.json        # Field mappings & templates
│   └── README.md               # Configuration guide
├── docs/
│   ├── ITSM_INTEGRATION_GUIDE.md  # Complete documentation
│   └── ITSM_QUICKSTART.md         # Quick start guide
└── .env.example                # Environment template
```

## 🚀 Quick Start

### 1. Install Dependencies

**Backend:**
```bash
cd unified_rca_engine
pip install -r requirements.txt
```

**Frontend:**
```bash
cd ui
npm install
```

### 2. Configure Environment

```bash
cp .env.example .env
```

**For ServiceNow:**
```bash
SERVICENOW_INSTANCE_URL=https://yourcompany.service-now.com
SERVICENOW_USERNAME=your_username
SERVICENOW_PASSWORD=your_password
```

**For Jira:**
```bash
JIRA_BASE_URL=https://yourcompany.atlassian.net
JIRA_EMAIL=your.email@company.com
JIRA_API_TOKEN=your_api_token
```

### 3. Enable Integrations

**Via UI:**
1. Start the app: `npm run dev` (frontend) and `uvicorn apps.api.main:app --reload` (backend)
2. Navigate to Settings → ITSM Integration
3. Toggle on ServiceNow and/or Jira
4. Save changes

**Via API:**
```bash
curl -X PUT "http://localhost:8000/api/v1/tickets/settings/state" \
  -H "Content-Type: application/json" \
  -d '{"servicenow_enabled": true, "jira_enabled": true}'
```

### 4. Create Your First Ticket

```bash
curl -X POST "http://localhost:8000/api/v1/tickets/" \
  -H "Content-Type: application/json" \
  -d '{
    "job_id": "test-job-123",
    "platform": "servicenow",
    "payload": {"short_description": "Test Incident"},
    "dry_run": true
  }'
```

## 📖 Documentation

- **[Quick Start Guide](docs/ITSM_QUICKSTART.md)**: Get up and running in 10 minutes
- **[Integration Guide](docs/ITSM_INTEGRATION_GUIDE.md)**: Complete setup, configuration, and usage
- **[Configuration Guide](config/README.md)**: Field mappings and templates
- **[Environment Variables](.env.example)**: All available configuration options

## 🎨 UI Components Usage

### Import Components

```typescript
import {
  TicketDashboard,
  TicketSettingsPanel,
  TicketCreationForm,
  TicketDetailView,
} from '@/components/tickets';
```

### Use in Your App

```tsx
// Display ticket dashboard
<TicketDashboard 
  jobId="rca-job-123" 
  autoRefresh={true}
  refreshInterval={60000}
/>

// Show settings panel
<TicketSettingsPanel />

// Create new ticket
<TicketCreationForm
  jobId="rca-job-123"
  onSuccess={() => console.log('Ticket created!')}
/>
```

### State Management

```typescript
import { useTicketStore } from '@/store/ticketStore';

function MyComponent() {
  const { 
    tickets, 
    loading, 
    loadJobTickets,
    updateToggleState 
  } = useTicketStore();

  useEffect(() => {
    loadJobTickets('job-123');
  }, []);

  return <div>{/* Your UI */}</div>;
}
```

## 🔌 API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/tickets/` | POST | Create single ticket |
| `/api/v1/tickets/dispatch` | POST | Create tickets on all enabled platforms |
| `/api/v1/tickets/{job_id}` | GET | List all tickets for job |
| `/api/v1/tickets/settings/state` | GET | Get feature toggle state |
| `/api/v1/tickets/settings/state` | PUT | Update toggle configuration |

## 🔧 Configuration Options

### Feature Toggles

- **ServiceNow**: Enable/disable ServiceNow incident creation
- **Jira**: Enable/disable Jira issue creation
- **Dual-Tracking Mode**: Link Jira issues to ServiceNow incidents

### Field Mappings

Customize field mappings in `config/itsm_config.json`:

```json
{
  "servicenow": {
    "defaults": {
      "assignment_group": "IT Support",
      "priority": "3"
    }
  },
  "jira": {
    "defaults": {
      "project_key": "PROJ",
      "issue_type": "Incident"
    }
  }
}
```

### Templates

Pre-configure ticket templates for common scenarios:

```json
{
  "templates": {
    "servicenow": {
      "critical_alert": {
        "short_description": "Critical: {alert_name}",
        "priority": "1"
      }
    }
  }
}
```

## 🔐 Security

- ✅ All credentials stored in environment variables
- ✅ No secrets in code or configuration files
- ✅ HTTPS for all external API calls
- ✅ API token authentication for Jira
- ✅ OAuth 2.0 support for ServiceNow

## 📊 Field Reference

### ServiceNow Required Fields
- `short_description` (string, max 160 chars)

### ServiceNow Optional Fields
- `description`, `assignment_group`, `assigned_to`, `configuration_item`, `category`, `subcategory`, `priority` (1-5), `state` (1-7)

### Jira Required Fields
- `project_key` (string, e.g., "PROJ")
- `summary` (string, max 255 chars)

### Jira Optional Fields
- `description`, `issue_type`, `assignee`, `priority`, `labels` (array), `components`, `environment`

## 🐛 Troubleshooting

### ServiceNow: 401 Unauthorized
- Verify credentials in `.env`
- Check user has `incident_manager` or `itil` role

### Jira: Project Not Found
- Verify project key (case-sensitive)
- Check user has "Create Issues" permission
- For Cloud: Use email + API token, not username + password

### Tickets Not Creating
1. Check toggle state via API
2. Test with `dry_run: true`
3. Review backend logs
4. Verify environment variables loaded

## 🚀 Advanced Features

### Dual-Tracking Mode

Link Jira issues to ServiceNow incidents:

```bash
curl -X POST "http://localhost:8000/api/v1/tickets/dispatch" \
  -d '{
    "job_id": "rca-job-456",
    "servicenow_payload": {"short_description": "API Outage"},
    "jira_payload": {"project_key": "OPS", "summary": "API Down"}
  }'
```

Result: Jira issue includes "Related ServiceNow Incident: INC0010123"

### Automatic Status Refresh

```typescript
<TicketDashboard 
  jobId="job-123" 
  autoRefresh={true}
  refreshInterval={60000}  // 60 seconds
/>
```

### Custom Templates

Use templates for consistent ticket creation:

```python
from core.tickets.service import TicketService

ticket = ticket_service.create_from_template(
    job_id="job-123",
    template_name="database_incident",
    variables={"db_name": "prod-db-01"}
)
```

## 📈 Performance

- **Ticket Creation**: 1-3 seconds per platform
- **Status Refresh**: 0.5-1 second per ticket
- **Concurrent Operations**: Up to 5 parallel ticket creations
- **Rate Limiting**: Respects external API limits

## 🤝 Contributing

When extending the ITSM integration:

1. Add new fields to `config/itsm_config.json`
2. Update TypeScript types in `ui/src/types/tickets.ts`
3. Extend client adapters in `core/tickets/clients.py`
4. Add tests for new functionality
5. Update documentation

## 📝 License

Part of the Unified RCA Engine project.

## 🙏 Support

- **Documentation**: See `docs/` directory
- **Quick Help**: Review `ITSM_QUICKSTART.md`
- **Logs**: Check `logs/unified_rca_engine.log`
- **Dry Run**: Test with `dry_run: true`

---

**Ready to get started?** 🚀 Follow the [Quick Start Guide](docs/ITSM_QUICKSTART.md) to set up your first integration in 10 minutes!
