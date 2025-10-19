# Pre-Deployment Checklist

**Feature:** Advanced ITSM Integration  
**Version:** 1.0  
**Target Deployment Date:** _________  
**Deployment Lead:** _________

---

## Phase 1: Code Review ✅

- [ ] All 24 tasks implemented and tested
- [ ] Code reviewed by team lead
- [ ] No blocking linter or type errors
- [ ] Unit tests passing (pytest)
- [ ] Integration tests verified
- [ ] Security scan completed
- [ ] Dependencies updated in requirements.txt

**Status:** ✅ COMPLETE

---

## Phase 2: Database Preparation

- [ ] Review migration script: `backend/db/migrations/versions/70a4e9f6d8c2_add_sla_tracking_to_tickets.py`
- [ ] Test migration on staging database
- [ ] Verify rollback procedure works
- [ ] Backup production database
- [ ] Schedule maintenance window (if needed)
- [ ] Run migration: `alembic upgrade head`
- [ ] Verify new columns: `acknowledged_at`, `resolved_at`, `time_to_acknowledge`, `time_to_resolve`

**Estimated Downtime:** < 1 minute (DDL operations)

**Rollback Command:**
```bash
alembic downgrade 60f3f78cb7d9
```

---

## Phase 3: Configuration

### 3.1 Template Configuration
- [ ] Create/update `config/itsm_config.json` with production templates
- [ ] Validate JSON syntax: `jq '.' config/itsm_config.json`
- [ ] Test each template with dry_run=true
- [ ] Document template usage for end users

**Template Checklist:**
- [ ] ServiceNow templates configured (production_incident, etc.)
- [ ] Jira templates configured (bug_report, etc.)
- [ ] All required_variables documented
- [ ] Template descriptions are clear

### 3.2 Environment Variables
- [ ] ServiceNow credentials configured in production .env
- [ ] Jira credentials configured in production .env
- [ ] Timeout values set appropriately
- [ ] Retry configuration tuned for production
- [ ] SSL verification enabled (VERIFY_SSL=true)

**Required Environment Variables:**
```bash
# ServiceNow
SERVICENOW_INSTANCE=yourcompany.service-now.com
SERVICENOW_USERNAME=prod_service_account
SERVICENOW_PASSWORD=<secure_password>
SERVICENOW_TIMEOUT=30

# Jira
JIRA_URL=https://yourcompany.atlassian.net
JIRA_EMAIL=prod_service_account@company.com
JIRA_API_TOKEN=<secure_token>
JIRA_TIMEOUT=30

# ITSM Configuration
ITSM_MAX_RETRIES=3
ITSM_RETRY_DELAY=1.0
ITSM_RETRY_BACKOFF=2.0
```

### 3.3 Feature Toggles
- [ ] Set initial toggle state (enabled/disabled)
- [ ] Test toggle endpoint: `GET /api/v1/tickets/toggle`
- [ ] Test toggle update: `PUT /api/v1/tickets/toggle`

**Recommended Initial State:**
```json
{
  "servicenow_enabled": true,
  "jira_enabled": true
}
```

---

## Phase 4: Monitoring Setup

### 4.1 Prometheus Configuration
- [ ] Deploy Prometheus with alert rules
- [ ] Verify alert rules loaded: `curl http://prometheus:9090/api/v1/rules`
- [ ] Test metrics endpoint: `curl http://api:8001/metrics | grep itsm`
- [ ] Configure Prometheus to scrape API service
- [ ] Verify all 7 ITSM metrics appear

**Metrics to Verify:**
- [ ] `itsm_ticket_creation_total`
- [ ] `itsm_ticket_creation_duration_seconds`
- [ ] `itsm_ticket_retry_attempts_total`
- [ ] `itsm_validation_errors_total`
- [ ] `itsm_template_rendering_errors_total`
- [ ] `itsm_ticket_time_to_acknowledge_seconds`
- [ ] `itsm_ticket_time_to_resolve_seconds`

### 4.2 Grafana Dashboard
- [ ] Deploy Grafana
- [ ] Add Prometheus datasource
- [ ] Import dashboard: `deploy/docker/config/grafana/dashboards/itsm_analytics.json`
- [ ] Verify all 7 panels display data
- [ ] Set up dashboard permissions
- [ ] Share dashboard URL with team

**Dashboard URL:** http://grafana:3001/d/itsm-analytics

### 4.3 Alertmanager
- [ ] Deploy Alertmanager
- [ ] Configure alert routing (email, Slack, PagerDuty)
- [ ] Test alert delivery with test alert
- [ ] Verify on-call schedule configured
- [ ] Document escalation procedures

**Alert Channels:**
- [ ] Email: ops-team@company.com
- [ ] Slack: #alerts-itsm
- [ ] PagerDuty: ITSM Integration service

---

## Phase 5: Frontend Deployment

### 5.1 Build and Deploy
- [ ] Install Node.js dependencies: `npm install`
- [ ] Run TypeScript type check: `npm run type-check`
- [ ] Build production bundle: `npm run build`
- [ ] Test production build locally: `npm start`
- [ ] Deploy to production environment

### 5.2 Frontend Configuration
- [ ] Set `NEXT_PUBLIC_API_URL` to production API
- [ ] Test API connectivity from frontend
- [ ] Verify template dropdown loads
- [ ] Test template creation flow end-to-end
- [ ] Check validation error display

### 5.3 UI Testing
- [ ] Template selection works
- [ ] Variable inputs render correctly
- [ ] TemplatePreview shows completion status
- [ ] Validation errors display inline
- [ ] Manual ticket creation still works
- [ ] Mobile responsive design verified

---

## Phase 6: Integration Testing

### 6.1 ServiceNow Integration
- [ ] Test manual ticket creation
- [ ] Test template-based ticket creation
- [ ] Verify ticket appears in ServiceNow
- [ ] Check ticket link is correct
- [ ] Test SLA tracking (status transitions)
- [ ] Verify retry logic on transient failures

**Test Commands:**
```bash
# List templates
curl http://api:8000/api/v1/tickets/templates?platform=servicenow

# Create from template
curl -X POST http://api:8000/api/v1/tickets/from-template \
  -H "Content-Type: application/json" \
  -d '{
    "job_id": "test-prod-123",
    "platform": "servicenow",
    "template_name": "production_incident",
    "variables": {
      "service_name": "Payment API",
      "error_message": "500 Internal Server Error",
      "impact": "Multiple customers affected"
    }
  }'
```

### 6.2 Jira Integration
- [ ] Test manual ticket creation
- [ ] Test template-based ticket creation
- [ ] Verify issue appears in Jira
- [ ] Check issue link is correct
- [ ] Test SLA tracking
- [ ] Verify retry logic

**Test Commands:**
```bash
# List Jira templates
curl http://api:8000/api/v1/tickets/templates?platform=jira

# Create from Jira template
curl -X POST http://api:8000/api/v1/tickets/from-template \
  -H "Content-Type: application/json" \
  -d '{
    "job_id": "test-prod-456",
    "platform": "jira",
    "template_name": "bug_report",
    "variables": {
      "summary": "Critical bug in payment flow",
      "description": "Users unable to complete checkout",
      "severity": "P1"
    }
  }'
```

### 6.3 Error Handling
- [ ] Test with invalid credentials (should log error, not crash)
- [ ] Test with unreachable ServiceNow/Jira (should retry)
- [ ] Test with rate limiting (should backoff)
- [ ] Test with validation errors (should return 400 with details)
- [ ] Test with missing template variables (should return 400)
- [ ] Test with non-existent template (should return 404)

---

## Phase 7: Performance Testing

### 7.1 Load Testing
- [ ] Baseline performance metrics collected
- [ ] Run load test: 50 tickets/hour for 1 hour
- [ ] Monitor CPU, memory, database connections
- [ ] Verify p95 latency < 5 seconds
- [ ] Check success rate > 95%

**Load Test Command:**
```bash
# Apache Bench test
ab -n 100 -c 10 -T 'application/json' \
  -p test_payload.json \
  http://api:8000/api/v1/tickets/
```

### 7.2 Monitoring During Load Test
- [ ] Watch Grafana dashboard during test
- [ ] Check Prometheus metrics update correctly
- [ ] Verify no memory leaks
- [ ] Check database query performance
- [ ] Monitor external service latency

---

## Phase 8: Documentation Review

- [ ] Review ITSM_INTEGRATION_GUIDE.md for accuracy
- [ ] Review ITSM_QUICKSTART.md for completeness
- [ ] Review ITSM_RUNBOOK.md with SRE team
- [ ] Update OpenAPI documentation: http://api:8000/docs
- [ ] Share documentation links with stakeholders
- [ ] Schedule training session for support team

**Documentation URLs:**
- Integration Guide: `docs/ITSM_INTEGRATION_GUIDE.md`
- Quick Start: `docs/ITSM_QUICKSTART.md`
- Runbook: `docs/ITSM_RUNBOOK.md`
- API Docs: http://api:8000/docs

---

## Phase 9: Security Review

- [ ] Credentials stored securely (not in code)
- [ ] API tokens rotated from development tokens
- [ ] SSL/TLS verification enabled
- [ ] Firewall rules configured for external APIs
- [ ] Least privilege service accounts used
- [ ] Audit logging enabled
- [ ] PII/sensitive data handling reviewed

**Security Checklist:**
- [ ] ServiceNow credentials use dedicated service account
- [ ] Jira API token has minimal required permissions
- [ ] No credentials committed to git repository
- [ ] Environment variables encrypted at rest
- [ ] Network traffic encrypted in transit (HTTPS)

---

## Phase 10: Rollback Planning

### 10.1 Rollback Procedures
- [ ] Document rollback steps
- [ ] Test rollback on staging
- [ ] Identify rollback decision criteria
- [ ] Define rollback authorization process

**Rollback Triggers:**
- Error rate > 25% for > 5 minutes
- Critical bugs affecting ticket creation
- External service incompatibility
- Performance degradation (p95 > 30s)

**Rollback Steps:**
```bash
# 1. Disable feature toggles
curl -X PUT http://api:8000/api/v1/tickets/toggle \
  -H "Content-Type: application/json" \
  -d '{"servicenow_enabled": false, "jira_enabled": false}'

# 2. Revert database migration
alembic downgrade 60f3f78cb7d9

# 3. Deploy previous application version
git checkout <previous-release-tag>
docker-compose up -d --build

# 4. Verify application health
curl http://api:8000/api/v1/health
```

### 10.2 Monitoring Post-Rollback
- [ ] Verify error rate returns to normal
- [ ] Check application logs for issues
- [ ] Confirm database integrity
- [ ] Test core application features still work

---

## Phase 11: Go-Live Execution

### 11.1 Pre-Deployment
- [ ] **T-24 hours:** Announce maintenance window
- [ ] **T-2 hours:** Final backup of production database
- [ ] **T-1 hour:** Freeze deployments (other features)
- [ ] **T-30 min:** Team assembled (Dev, SRE, Support)
- [ ] **T-15 min:** Final smoke tests on staging

### 11.2 Deployment Steps
- [ ] **T-0:** Begin maintenance window
- [ ] **T+2 min:** Deploy API changes (docker-compose up -d --build api)
- [ ] **T+4 min:** Run database migration (alembic upgrade head)
- [ ] **T+6 min:** Deploy monitoring (Prometheus, Grafana, Alertmanager)
- [ ] **T+8 min:** Deploy frontend (UI build + deploy)
- [ ] **T+10 min:** Verify all services healthy
- [ ] **T+12 min:** Enable feature toggles
- [ ] **T+15 min:** Run smoke tests
- [ ] **T+20 min:** End maintenance window

### 11.3 Post-Deployment Verification
- [ ] Health check: `curl http://api:8000/api/v1/health`
- [ ] Metrics endpoint: `curl http://api:8001/metrics | grep itsm`
- [ ] List templates: `curl http://api:8000/api/v1/tickets/templates`
- [ ] Create test ticket (ServiceNow)
- [ ] Create test ticket (Jira)
- [ ] Verify tickets appear in external systems
- [ ] Check Grafana dashboard displays data
- [ ] Confirm alerts loaded in Prometheus

### 11.4 Monitoring Post-Deployment
- [ ] **T+30 min:** Check error rates (should be < 5%)
- [ ] **T+1 hour:** Review Grafana dashboard trends
- [ ] **T+2 hours:** Verify no alerts firing
- [ ] **T+4 hours:** Check SLA metrics updating
- [ ] **T+24 hours:** Review full day metrics
- [ ] **T+1 week:** Analyze weekly trends, tune alerts

---

## Phase 12: User Communication

### 12.1 Pre-Launch Communication
- [ ] Send announcement email to users
- [ ] Update internal wiki/documentation
- [ ] Post in team Slack channels
- [ ] Schedule demo/training session

**Announcement Template:**
```
Subject: New Feature: ITSM Integration with Templates

Hi Team,

We're excited to announce the launch of our Advanced ITSM Integration feature!

🎉 What's New:
- Template-based ticket creation for common scenarios
- Automated SLA tracking (time to acknowledge/resolve)
- Real-time monitoring dashboards
- Improved error handling and retry logic

📚 Resources:
- Quick Start Guide: [link]
- Full Documentation: [link]
- Training Session: [date/time]

🚀 Get Started:
1. Visit the RCA UI
2. Click "Create Ticket"
3. Toggle "Use Template"
4. Select a template and fill variables

Questions? Contact #support-rca

Happy ticket creating!
- Platform Team
```

### 12.2 Post-Launch Support
- [ ] Monitor support channels for questions
- [ ] Collect user feedback
- [ ] Document common questions in FAQ
- [ ] Schedule follow-up training if needed
- [ ] Plan retrospective meeting

---

## Phase 13: Success Criteria

### 13.1 Technical Metrics (Week 1)
- [ ] Ticket creation success rate > 95%
- [ ] p95 latency < 5 seconds
- [ ] Zero critical alerts
- [ ] SLA tracking accuracy > 99%
- [ ] Template usage > 30% of tickets

### 13.2 Business Metrics (Week 1)
- [ ] Reduced manual ticket creation time by > 50%
- [ ] Improved incident response time
- [ ] User satisfaction score > 4/5
- [ ] Zero production incidents caused by integration

### 13.3 Review Schedule
- [ ] **Day 1:** Post-deployment review
- [ ] **Day 3:** Mid-week metrics check
- [ ] **Week 1:** End of week retrospective
- [ ] **Week 4:** Monthly review and optimization

---

## Emergency Contacts

| Role | Name | Contact |
|------|------|---------|
| Deployment Lead | _________ | _________ |
| Backend Engineer | _________ | _________ |
| Frontend Engineer | _________ | _________ |
| SRE On-Call | _________ | _________ |
| Product Owner | _________ | _________ |
| ServiceNow Admin | _________ | _________ |
| Jira Admin | _________ | _________ |

---

## Sign-Off

| Stakeholder | Role | Signature | Date |
|-------------|------|-----------|------|
| _________ | Engineering Manager | _________ | _____ |
| _________ | Product Manager | _________ | _____ |
| _________ | SRE Lead | _________ | _____ |
| _________ | Security Lead | _________ | _____ |
| _________ | QA Lead | _________ | _____ |

---

**Deployment Status:** ⬜ Not Started | ⬜ In Progress | ⬜ Complete | ⬜ Rolled Back

**Notes:**
_______________________________________________________________________
_______________________________________________________________________
_______________________________________________________________________

---

**Version:** 1.0  
**Last Updated:** October 12, 2025  
**Next Review:** Post-Deployment
