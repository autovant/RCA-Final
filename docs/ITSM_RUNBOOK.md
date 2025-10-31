# ITSM Integration Runbook

**Operational Guide for Site Reliability Engineers and Support Teams**

This runbook provides step-by-step procedures for responding to ITSM integration alerts, troubleshooting common issues, and maintaining system health.

---

## Table of Contents

1. [Alert Response Procedures](#alert-response-procedures)
2. [Common Issues and Solutions](#common-issues-and-solutions)
3. [Metrics Interpretation Guide](#metrics-interpretation-guide)
4. [Troubleshooting Workflows](#troubleshooting-workflows)
5. [Escalation Procedures](#escalation-procedures)
6. [Maintenance Tasks](#maintenance-tasks)

---

## Alert Response Procedures

### 🟡 Alert: HighITSMErrorRate

**Severity:** Warning  
**Trigger:** Error rate > 5% for 5 minutes  
**SLA:** Respond within 15 minutes

#### Symptoms
- Increased ticket creation failures
- Users reporting tickets not created
- Error rate spike in Grafana dashboard

#### Investigation Steps

1. **Check Alert Details**
   ```bash
   # View current error rate in Prometheus
   curl "http://localhost:9090/api/v1/query?query=sum(rate(itsm_ticket_creation_total{outcome='failure'}[5m]))/sum(rate(itsm_ticket_creation_total[5m]))*100"
   ```

2. **Check Application Logs**
   ```bash
   # View recent errors
   docker-compose logs api | grep -i "error" | tail -50
   
   # Filter ITSM-specific errors
   docker-compose logs api | grep "tickets" | grep "ERROR"
   ```

3. **Identify Affected Platform**
   ```promql
   # In Prometheus/Grafana
   sum by (platform) (rate(itsm_ticket_creation_total{outcome="failure"}[5m]))
   ```

4. **Test External Service Connectivity**
   ```bash
   # ServiceNow
   curl -I https://yourcompany.service-now.com/api/now/table/incident
   
   # Jira
   curl -I https://yourcompany.atlassian.net/rest/api/3/myself
   ```

#### Resolution Actions

**If ServiceNow is down:**
- Check ServiceNow status page: https://status.servicenow.com
- Temporarily disable ServiceNow integration if extended outage
- Enable retry logic will handle transient issues automatically

**If Jira is down:**
- Check Jira status: https://status.atlassian.com
- Temporarily disable Jira integration if needed

**If authentication failure:**
- Verify credentials in environment variables
- Rotate API tokens if compromised
- Check for expired ServiceNow sessions

**If validation errors:**
- Review recent payload changes
- Check template configurations
- Validate required fields are being sent

#### Post-Incident Actions
- Document root cause in incident report
- Update monitoring thresholds if false positive
- Review retry logic configuration

---

### 🔴 Alert: CriticalITSMErrorRate

**Severity:** Critical  
**Trigger:** Error rate > 25% for 2 minutes  
**SLA:** Respond immediately (< 5 minutes)

#### Immediate Actions

1. **Page On-Call Engineer**
2. **Check System Health**
   ```bash
   # Check API is responding
   curl http://localhost:8000/api/v1/health
   
   # Check database connectivity
   docker-compose exec api python -c "from core.db.database import engine; print(engine.connect())"
   ```

3. **Disable ITSM Integration (if critical business impact)**
   ```bash
   curl -X PUT "http://localhost:8000/api/v1/tickets/toggle" \
     -H "Content-Type: application/json" \
     -d '{"servicenow_enabled": false, "jira_enabled": false}'
   ```

4. **Review Recent Changes**
   ```bash
   # Check recent deployments
   git log --oneline -10
   
   # Check recent config changes
   git diff HEAD~1 config/
   ```

5. **Rollback if Recent Deployment**
   ```bash
   # Rollback to previous version
   git checkout <previous-commit>
   docker-compose up -d --build api
   ```

#### Follow Standard HighITSMErrorRate Procedure
Continue with investigation steps from HighITSMErrorRate alert.

---

### 🟡 Alert: ExcessiveITSMRetries

**Severity:** Warning  
**Trigger:** > 50 retry attempts/minute for 5 minutes  
**SLA:** Respond within 30 minutes

#### Symptoms
- High retry metric in dashboard
- Slow ticket creation performance
- Network instability

#### Investigation Steps

1. **Check Retry Metrics**
   ```promql
   sum by (platform) (rate(itsm_ticket_retry_attempts_total[5m]))
   ```

2. **Check External Service Health**
   - ServiceNow response times
   - Jira API latency
   - Network connectivity

3. **Review Retry Configuration**
   ```bash
   # Check current settings
   docker-compose exec api env | grep ITSM_
   ```

#### Resolution Actions

**If external service is slow:**
- Increase timeout values temporarily
- Contact service provider if persistent
- Consider circuit breaker implementation

**If network issues:**
- Check DNS resolution
- Verify firewall rules
- Test connectivity from server

**If misconfiguration:**
- Adjust `ITSM_MAX_RETRIES` if too aggressive
- Increase `ITSM_RETRY_DELAY` for backoff
- Review `ITSM_RETRY_BACKOFF` multiplier

#### Tuning Recommendations
```bash
# Conservative settings for unstable networks
ITSM_MAX_RETRIES=5
ITSM_RETRY_DELAY=2.0
ITSM_RETRY_BACKOFF=2.0

# Aggressive settings for stable networks
ITSM_MAX_RETRIES=2
ITSM_RETRY_DELAY=0.5
ITSM_RETRY_BACKOFF=1.5
```

---

### 🟡 Alert: ValidationFailureSpike

**Severity:** Warning  
**Trigger:** > 10 validation errors/minute for 3 minutes  
**SLA:** Respond within 30 minutes

#### Investigation Steps

1. **Identify Problematic Fields**
   ```promql
   topk(10, sum by (field) (rate(itsm_validation_errors_total[5m])))
   ```

2. **Check Recent Template Changes**
   ```bash
   git diff HEAD~1 config/itsm_config.json
   ```

3. **Review Error Details**
   ```bash
   docker-compose logs api | grep "validation" | tail -20
   ```

#### Resolution Actions

**If template issue:**
- Review template variable substitution
- Check required_variables list is accurate
- Validate template payload structure

**If API contract change:**
- Check ServiceNow/Jira API documentation
- Update field validation rules in `core/tickets/validation.py`
- Deploy hotfix with corrected validation

**If user input issue:**
- Add UI validation hints
- Update field placeholder text
- Improve error messages

---

### 🟡 Alert: TemplateRenderingFailures

**Severity:** Warning  
**Trigger:** Any template rendering errors for 1 minute  
**SLA:** Respond within 15 minutes

#### Investigation Steps

1. **Identify Failing Template**
   ```promql
   sum by (template_name) (itsm_template_rendering_errors_total)
   ```

2. **Review Template Configuration**
   ```bash
   # Check template syntax
   cat config/itsm_config.json | jq '.templates.servicenow[] | select(.name=="production_incident")'
   ```

3. **Check Application Logs**
   ```bash
   docker-compose logs api | grep "TemplateRenderError"
   ```

#### Common Template Issues

**Missing variable in template:**
```json
// ❌ Bad: Uses {undefined_var}
"description": "Error: {undefined_var}"

// ✅ Good: Only uses declared variables
"required_variables": ["service_name"],
"description": "Error in: {service_name}"
```

**Invalid JSON syntax:**
```json
// ❌ Bad: Trailing comma
{
  "name": "template",
  "payload": {},  // <- Remove this comma
}

// ✅ Good: Valid JSON
{
  "name": "template",
  "payload": {}
}
```

**Incorrect variable substitution:**
- Variables must be in `{variable_name}` format
- Variables are case-sensitive
- No spaces allowed: `{var name}` ❌ → `{var_name}` ✅

#### Resolution Actions
1. Fix template configuration in `config/itsm_config.json`
2. Validate JSON syntax: `jq '.' config/itsm_config.json`
3. Restart API service: `docker-compose restart api`
4. Test template: Use `/api/v1/tickets/from-template` with dry_run=true

---

### 🟡 Alert: SlowITSMTicketCreation

**Severity:** Warning  
**Trigger:** p95 latency > 5 seconds for 5 minutes  
**SLA:** Respond within 1 hour

#### Investigation Steps

1. **Check Current Latency**
   ```promql
   histogram_quantile(0.95, 
     sum by (le, platform) (
       rate(itsm_ticket_creation_duration_seconds_bucket[5m])
     )
   )
   ```

2. **Compare to Baseline**
   - Normal latency: 1-3 seconds
   - Acceptable: < 5 seconds
   - Slow: > 5 seconds
   - Critical: > 10 seconds

3. **Check External Service Status**
   - ServiceNow Performance Metrics
   - Jira Cloud Status
   - Network latency

4. **Review Database Performance**
   ```bash
   # Check slow queries
   docker-compose exec postgres psql -U user -d rca_db -c "SELECT * FROM pg_stat_statements ORDER BY mean_exec_time DESC LIMIT 10;"
   ```

#### Resolution Actions

**If external service slow:**
- Contact service provider
- Increase timeout temporarily
- Document performance degradation

**If database slow:**
- Check database connections
- Review query performance
- Consider connection pooling adjustment

**If network slow:**
- Check network latency: `ping yourcompany.service-now.com`
- Review network path
- Contact network team if persistent

---

### 🔵 Alert: NoITSMActivity

**Severity:** Info  
**Trigger:** No tickets created for 30 minutes  
**SLA:** Informational (investigate during business hours)

#### Investigation Steps

1. **Verify Expected Behavior**
   - Is this expected during off-hours?
   - Are there active RCA jobs?
   - Has traffic pattern changed?

2. **Check Feature Toggles**
   ```bash
   curl http://localhost:8000/api/v1/tickets/toggle
   ```

3. **Check Recent Deployments**
   - Was there a recent change that might affect traffic?

#### Actions
- If unexpected: Investigate why no tickets are being created
- If expected: Adjust alert threshold or business hours filter
- If toggle disabled: Re-enable if appropriate

---

## Common Issues and Solutions

### Issue: "Connection Timeout" Errors

**Symptoms:**
- Tickets fail to create
- Logs show connection timeout
- External service unreachable

**Diagnosis:**
```bash
# Test connectivity
curl -v -m 10 https://yourcompany.service-now.com

# Check DNS resolution
nslookup yourcompany.service-now.com

# Check firewall rules
telnet yourcompany.service-now.com 443
```

**Solutions:**
1. Increase timeout: Set `SERVICENOW_TIMEOUT=60` or `JIRA_TIMEOUT=60`
2. Check firewall rules: Allow outbound HTTPS (443)
3. Verify VPN connection if required
4. Check proxy settings if behind corporate proxy

---

### Issue: "401 Unauthorized" Errors

**Symptoms:**
- Authentication failures
- Tickets fail with 401 status
- Logs show "Invalid credentials"

**Diagnosis:**
```bash
# Test ServiceNow credentials
curl -u username:password \
  "https://yourcompany.service-now.com/api/now/table/incident?sysparm_limit=1"

# Test Jira credentials
curl -u email@company.com:api_token \
  "https://yourcompany.atlassian.net/rest/api/3/myself"
```

**Solutions:**
1. **Verify credentials in `.env` file**
2. **For Jira Cloud:** Ensure using email + API token (not password)
3. **For ServiceNow:** Check user has proper roles (`incident_manager` or `itil`)
4. **Rotate credentials:**
   - Generate new Jira API token
   - Reset ServiceNow password
   - Update `.env` file
   - Restart API service

---

### Issue: "429 Rate Limit Exceeded" Errors

**Symptoms:**
- Intermittent failures
- HTTP 429 responses
- Logs show "Too many requests"

**Diagnosis:**
```promql
# Check retry rate
sum(rate(itsm_ticket_retry_attempts_total[5m]))

# Check ticket creation rate
sum(rate(itsm_ticket_creation_total[5m]))
```

**Solutions:**
1. **Automatic:** Retry logic with exponential backoff handles this
2. **Manual:** Reduce ticket creation frequency
3. **Configuration:** Increase retry delay
   ```bash
   ITSM_RETRY_DELAY=2.0
   ITSM_RETRY_BACKOFF=3.0
   ```
4. **Contact provider:** Request rate limit increase if legitimate usage

**Platform Rate Limits:**
- ServiceNow: ~1,000 requests/hour
- Jira Cloud: ~10,000 requests/hour
- Jira Server: Varies by configuration

---

### Issue: Template Variables Not Substituting

**Symptoms:**
- Ticket created with `{variable_name}` literal text
- Template rendering errors
- Variables not replaced

**Diagnosis:**
```bash
# Test template rendering
curl -X POST "http://localhost:8000/api/v1/tickets/from-template" \
  -H "Content-Type: application/json" \
  -d '{
    "job_id": "test-123",
    "platform": "servicenow",
    "template_name": "production_incident",
    "variables": {"service_name": "Test API"},
    "dry_run": true
  }' | jq '.'
```

**Common Causes:**
1. Variable name mismatch (case-sensitive)
2. Variable not in `required_variables` list
3. Invalid template syntax

**Solutions:**
1. **Check variable names match exactly**
   ```json
   // Template config
   "required_variables": ["service_name"]  // Must match
   
   // API call
   "variables": {"service_name": "Payment API"}  // Exact match
   ```

2. **Validate template syntax**
   ```bash
   jq '.' config/itsm_config.json  # Should print valid JSON
   ```

3. **Update template configuration**
   - Add missing variables to `required_variables`
   - Fix variable name in template payload
   - Restart API service

---

## Metrics Interpretation Guide

### Understanding Ticket Creation Metrics

#### Success Rate
```promql
sum(rate(itsm_ticket_creation_total{outcome="success"}[5m]))
  / sum(rate(itsm_ticket_creation_total[5m])) * 100
```

**Healthy Ranges:**
- ✅ > 95% - Excellent
- ⚠️ 90-95% - Acceptable, investigate if persistent
- 🔴 < 90% - Critical, immediate action required

---

#### Latency Percentiles

**p50 (Median):**
```promql
histogram_quantile(0.50, 
  rate(itsm_ticket_creation_duration_seconds_bucket[5m]))
```
- ✅ < 2s - Excellent
- ⚠️ 2-3s - Acceptable
- 🔴 > 3s - Slow

**p95:**
```promql
histogram_quantile(0.95, 
  rate(itsm_ticket_creation_duration_seconds_bucket[5m]))
```
- ✅ < 5s - Excellent
- ⚠️ 5-10s - Acceptable
- 🔴 > 10s - Slow

**p99:**
- ✅ < 10s - Excellent
- ⚠️ 10-30s - Acceptable
- 🔴 > 30s - Critical

---

#### Retry Rate

**Healthy Retry Patterns:**
- 0-5 retries/min: Normal (transient network issues)
- 5-10 retries/min: Elevated (monitor)
- 10-50 retries/min: High (investigate)
- \> 50 retries/min: Critical (external service likely down)

---

#### Validation Error Rate

```promql
sum(rate(itsm_validation_errors_total[5m]))
```

**Interpretation:**
- 0-1 errors/min: Normal (user input errors)
- 1-5 errors/min: Elevated (check templates)
- 5-10 errors/min: High (likely configuration issue)
- \> 10 errors/min: Critical (broken template or API change)

---

### SLA Metrics

#### Time to Acknowledge

**Targets:**
- P1 (Critical): < 15 minutes
- P2 (High): < 30 minutes
- P3 (Medium): < 2 hours
- P4 (Low): < 8 hours

**Query:**
```promql
histogram_quantile(0.95,
  rate(itsm_ticket_time_to_acknowledge_seconds_bucket[1h]))
```

---

#### Time to Resolve

**Targets:**
- P1 (Critical): < 4 hours
- P2 (High): < 24 hours
- P3 (Medium): < 72 hours
- P4 (Low): < 1 week

**Query:**
```promql
histogram_quantile(0.95,
  rate(itsm_ticket_time_to_resolve_seconds_bucket[1h]))
```

---

## Troubleshooting Workflows

### Workflow 1: Ticket Creation Failures

```
1. Check error logs
   ├─> Authentication error → Fix credentials
   ├─> Connection timeout → Check network/firewall
   ├─> Validation error → Fix payload
   └─> Rate limit → Wait for backoff

2. Test with dry-run
   └─> Success? Re-enable live mode

3. Verify external service
   ├─> ServiceNow status page
   └─> Jira status page

4. Re-enable integration
   └─> Monitor metrics for 15 minutes
```

---

### Workflow 2: Performance Degradation

```
1. Check latency metrics
   └─> Identify affected platform

2. Test external service
   ├─> ServiceNow response time
   └─> Jira API latency

3. Check database performance
   └─> Slow queries?

4. Review network latency
   └─> Ping external services

5. Temporary mitigation
   ├─> Increase timeout
   ├─> Reduce concurrency
   └─> Enable caching
```

---

### Workflow 3: Template Issues

```
1. Identify failing template
   └─> Check metrics by template_name

2. Validate JSON syntax
   └─> Run: jq '.' config/itsm_config.json

3. Test template rendering
   └─> Use dry-run with sample variables

4. Fix template
   ├─> Update config
   ├─> Restart API
   └─> Re-test

5. Monitor error rate
   └─> Should drop to zero
```

---

## Escalation Procedures

### Level 1: On-Call Engineer (You)
**Response Time:** < 15 minutes  
**Responsibilities:**
- Acknowledge alert
- Initial investigation
- Implement standard remediation
- Document actions in incident ticket

---

### Level 2: Platform Team Lead
**Escalate If:**
- Issue not resolved within 1 hour
- Critical error rate (> 25%)
- External service outage confirmed
- Data integrity concerns

**Contact:** platform-team@company.com

---

### Level 3: Engineering Manager
**Escalate If:**
- Multi-platform failure
- Suspected security breach
- Data loss risk
- Extended outage (> 4 hours)

**Contact:** eng-manager@company.com

---

### External Escalation

**ServiceNow Support:**
- Portal: https://support.servicenow.com
- Premium Support Phone: Check contract
- Severity 1: Critical system down

**Jira/Atlassian Support:**
- Portal: https://support.atlassian.com
- Cloud Status: https://status.atlassian.com
- Priority Support: For enterprise customers

---

## Maintenance Tasks

### Daily Tasks
- [ ] Review Grafana dashboard for anomalies
- [ ] Check alert firing rate
- [ ] Monitor error rate trends

### Weekly Tasks
- [ ] Review slow ticket creation trends
- [ ] Analyze top validation errors
- [ ] Check SLA compliance metrics
- [ ] Review retry patterns

### Monthly Tasks
- [ ] Credential rotation (API tokens)
- [ ] Template configuration review
- [ ] Performance baseline update
- [ ] Alert threshold tuning
- [ ] Runbook accuracy review

### Quarterly Tasks
- [ ] Disaster recovery test
- [ ] External service quota review
- [ ] Integration upgrade planning
- [ ] Documentation update

---

## Quick Reference Commands

```bash
# Check service health
curl http://localhost:8000/api/v1/health

# View recent logs
docker-compose logs api --tail=100 --follow

# Check feature toggles
curl http://localhost:8000/api/v1/tickets/toggle

# Disable ITSM (emergency)
curl -X PUT http://localhost:8000/api/v1/tickets/toggle \
  -H "Content-Type: application/json" \
  -d '{"servicenow_enabled":false,"jira_enabled":false}'

# Test ServiceNow connection
curl -u user:pass https://instance.service-now.com/api/now/table/incident?sysparm_limit=1

# Test Jira connection
curl -u email:token https://company.atlassian.net/rest/api/3/myself

# Check Prometheus metrics
curl http://localhost:9090/api/v1/query?query=itsm_ticket_creation_total

# Restart API service
docker-compose restart api

# View database logs
docker-compose logs postgres --tail=50
```

---

## Additional Resources

- **Full Documentation:** [ITSM Integration Guide](./ITSM_INTEGRATION_GUIDE.md)
- **Quick Start:** [ITSM Quick Start](./ITSM_QUICKSTART.md)
- **Grafana Dashboard:** `deploy/docker/config/grafana/dashboards/itsm_analytics.json`
- **Alert Rules:** `deploy/docker/config/alert_rules.yml`
- **Template Config:** `config/itsm_config.json`

---

**Version:** 1.0  
**Last Updated:** October 2025  
**Maintainer:** Platform Engineering Team
