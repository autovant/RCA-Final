/# 🚀 Docker Deployment Guide - Advanced ITSM Integration

## Prerequisites Check ✅

- ✅ Docker installed (v28.4.0)
- ✅ Docker Compose installed (v2.39.2)
- ⚠️ **Docker requires WSL (Windows Subsystem for Linux) on Windows**

---

## Step 1: Set Up WSL and Docker

### Option A: If WSL is Not Installed

1. **Install WSL:**
   ```powershell
   # Run in PowerShell as Administrator
   wsl --install
   ```

2. **Restart your computer** when prompted

3. **Set up Ubuntu** (default WSL distribution):
   - After restart, Ubuntu will open automatically
   - Create a username and password
   - Close Ubuntu terminal

4. **Install Docker Desktop:**
   - Download from https://www.docker.com/products/docker-desktop
   - During installation, ensure "Use WSL 2 instead of Hyper-V" is checked
   - Restart computer if prompted

5. **Start Docker Desktop:**
   - Open Docker Desktop application
   - Wait for it to fully start (whale icon stable in system tray)
   - Docker Desktop will automatically integrate with WSL

### Option B: If WSL is Already Installed

1. **Verify WSL is running:**
   ```powershell
   wsl --list --verbose
   ```
   - Should show Ubuntu or another Linux distribution with VERSION 2

2. **Start Docker Desktop:**
   - Open Docker Desktop application
   - Go to Settings → Resources → WSL Integration
   - Ensure your WSL distribution is enabled
   - Click "Apply & Restart"

3. **Verify Docker in WSL:**
   ```bash
   wsl
   docker --version
   docker ps
   ```
   - Should show Docker version and empty container list (no errors)

---

## Step 2: Access Project in WSL

### Navigate to Project Directory in WSL

```bash
# Open WSL terminal
wsl

# Navigate to your project (Windows paths are mounted under /mnt/)
cd "/mnt/c/Users/syed.shareef/.vscode/repos/RCA - v7/RCA-Final/deploy/docker"

# Verify you're in the right directory
ls -la docker-compose.yml
```

**Note:** From this point forward, **all commands must be run inside the WSL terminal**, not PowerShell.

---

## Step 3: Start Core Services (IN WSL)

**IMPORTANT: All following commands must be run in WSL terminal, not PowerShell**

### Start Database and Redis
```bash
# Make sure you're in the docker directory
cd "/mnt/c/Users/syed.shareef/.vscode/repos/RCA - v7/RCA-Final/deploy/docker"

# Start services
docker-compose up -d db redis
```

**Expected output:**
```
[+] Running 2/2
 ✔ Container rca_db      Started
 ✔ Container rca_redis   Started
```

**Wait ~30 seconds for database to initialize**

### Verify services are running
```bash
docker-compose ps
```

You should see `db` and `redis` with status "Up"

---

## Step 4: Build and Start API Service (IN WSL)

```bash
docker-compose up -d --build rca_core
```

**Note:** First build will take 3-5 minutes as it installs all Python dependencies.

**Expected output:**
```
[+] Building ... (may take a few minutes)
[+] Running 1/1
 ✔ Container rca_core    Started
```

### Check API logs
```bash
docker-compose logs -f rca_core
```

Press `Ctrl+C` to stop following logs once you see:
```
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000
```

---

## Step 5: Run Database Migration (IN WSL)

### Execute Alembic migration inside the API container
```bash
docker-compose exec rca_core alembic upgrade head
```

**Expected output:**
```
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade 60f3f78cb7d9 -> 70a4e9f6d8c2, Add SLA tracking fields to tickets table
```

### Verify migration applied
```bash
docker-compose exec rca_core alembic current
```

**Expected output:**
```
70a4e9f6d8c2 (head)
```

---

## Step 6: Verify API is Working (IN WSL)

### Test health endpoint
```bash
curl http://localhost:8000/api/v1/health
```

**Expected response:**
```json
{"status":"healthy","timestamp":"..."}
```

### Test templates endpoint
```bash
curl http://localhost:8000/api/v1/tickets/templates
```

**Expected response:**
```json
{
  "templates": [],
  "count": 0
}
```
*(Empty because no templates configured yet)*

### Check metrics endpoint (includes ITSM metrics)
```bash
curl http://localhost:8001/metrics | grep "itsm"
```

**Expected output:**
```
# HELP itsm_ticket_creation_total Total number of ITSM ticket creation attempts
# TYPE itsm_ticket_creation_total counter
itsm_ticket_creation_total{outcome="success",platform="servicenow"} 0.0
...
```

---

## Step 7: Start Monitoring Stack (IN WSL)

### Start Prometheus and Grafana
```bash
docker-compose --profile monitoring up -d prometheus grafana
```

**Expected output:**
```
[+] Running 2/2
 ✔ Container rca_prometheus  Started
 ✔ Container rca_grafana     Started
```

### Verify monitoring services
```bash
docker-compose ps
```

You should see `rca_prometheus` and `rca_grafana` with status "Up"

### Test Prometheus
```bash
curl http://localhost:9090/-/healthy
```

**Expected:** `Prometheus Server is Healthy.`

### Test Grafana
Open browser: **http://localhost:3001**
- **Username:** admin
- **Password:** admin (as configured in .env)

You'll be prompted to change the password on first login.

---

## Step 8: Import Grafana Dashboard

### Option A: Via Grafana UI (Recommended)
1. Access Grafana at http://localhost:3001
2. Login with admin/admin
3. Click **"+"** (top menu) → **"Import"**
4. Click **"Upload JSON file"**
5. Select file: `C:\Users\syed.shareef\.vscode\repos\RCA - v7\RCA-Final\deploy\docker\config\grafana\dashboards\itsm_analytics.json`
6. Select datasource: **Prometheus**
7. Click **"Import"**

### Option B: Via API (IN WSL)
```bash
curl -X POST http://localhost:3001/api/dashboards/db \
  -H "Content-Type: application/json" \
  -u admin:admin \
  -d @config/grafana/dashboards/itsm_analytics.json
```

---

## Step 9: Verify Prometheus Alerts (IN WSL)

### Check alerts are loaded
```bash
curl http://localhost:9090/api/v1/rules | jq '.data'
```

### View alerts in UI
Open browser: **http://localhost:9090/alerts**

You should see 7 ITSM alerts:
- HighITSMErrorRate
- CriticalITSMErrorRate
- ExcessiveITSMRetries
- ValidationFailureSpike
- TemplateRenderingFailures
- SlowITSMTicketCreation
- NoITSMActivity

---

## Step 10: Configure Templates (Optional - IN WSL)

### Check current template configuration
```bash
cat ../../config/itsm_config.json
```

If the file doesn't exist or needs templates, create/update it:

```bash
cd ../..  # Back to project root
```

Create `config/itsm_config.json` using your preferred editor (nano, vi, or edit in Windows and save):
```json
{
  "templates": {
    "servicenow": [
      {
        "name": "production_incident",
        "description": "Production incident template for critical service failures",
        "required_variables": ["service_name", "error_message", "impact"],
        "payload": {
          "short_description": "Production Incident: {service_name}",
          "description": "Critical error in {service_name}:\n\n{error_message}\n\nImpact: {impact}",
          "priority": 1,
          "urgency": 1,
          "impact": 1,
          "category": "Software",
          "subcategory": "Application"
        }
      }
    ],
    "jira": [
      {
        "name": "bug_report",
        "description": "Standard bug report template",
        "required_variables": ["summary", "description", "severity"],
        "payload": {
          "summary": "{summary}",
          "description": "{description}\n\nSeverity: {severity}",
          "issuetype": {"name": "Bug"},
          "priority": {"name": "High"}
        }
      }
    ]
  }
}
```

### Restart API to load templates
```bash
cd deploy/docker
docker-compose restart rca_core
```

### Verify templates loaded
```bash
curl http://localhost:8000/api/v1/tickets/templates
```

**Expected response:**
```json
{
  "templates": [
    {
      "name": "production_incident",
      "platform": "servicenow",
      "description": "Production incident template for critical service failures",
      "required_variables": ["service_name", "error_message", "impact"],
      "field_count": 7
    },
    {
      "name": "bug_report",
      "platform": "jira",
      "description": "Standard bug report template",
      "required_variables": ["summary", "description", "severity"],
      "field_count": 3
    }
  ],
  "count": 2
}
```

---

## Step 11: Test Template Creation with Dry-Run (IN WSL)

```bash
curl -X POST http://localhost:8000/api/v1/tickets/from-template \
  -H "Content-Type: application/json" \
  -d '{
    "job_id": "test-deployment-123",
    "platform": "servicenow",
    "template_name": "production_incident",
    "variables": {
      "service_name": "Payment API",
      "error_message": "500 Internal Server Error - Database connection failed",
      "impact": "Multiple customers unable to process payments"
    },
    "dry_run": true
  }'
```

**Expected response:**
```json
{
  "id": "...",
  "job_id": "test-deployment-123",
  "platform": "servicenow",
  "template_name": "production_incident",
  "status": "pending",
  "dry_run": true,
  "created_at": "...",
  "payload": {
    "short_description": "Production Incident: Payment API",
    "description": "Critical error in Payment API:\n\n500 Internal Server Error - Database connection failed\n\nImpact: Multiple customers unable to process payments",
    ...
  }
}
```

---

## Step 12: Access Services

### Core Services
- **API:** http://localhost:8000
- **API Docs (OpenAPI):** http://localhost:8000/docs
- **API Metrics:** http://localhost:8001/metrics

### Monitoring Services
- **Grafana:** http://localhost:3001 (admin/admin)
- **Prometheus:** http://localhost:9090
- **Prometheus Alerts:** http://localhost:9090/alerts

### Database
- **PostgreSQL:** localhost:5432
  - Database: `rca_engine`
  - User: `rca_user`
  - Password: `rca_password_change_in_production`

---

## Troubleshooting

### Issue: Docker commands not working in PowerShell

**Solution:** You must use WSL for Docker on Windows.
```bash
# Open WSL terminal
wsl

# Then run docker commands
docker ps
```

### Issue: API container won't start

**Check logs (IN WSL):**
```bash
docker-compose logs rca_core
```

**Common issues:**
- Database not ready: Wait 30 seconds and try again
- Port already in use: Check if another service is using port 8000
- Build failed: Check for syntax errors in code

### Issue: Migration fails

**Check database connection (IN WSL):**
```bash
docker-compose exec rca_core python -c "from core.db.database import engine; print('DB Connected')"
```

**Manually connect to database (IN WSL):**
```bash
docker-compose exec db psql -U rca_user -d rca_engine
```

### Issue: Grafana dashboard not showing data

1. Check Prometheus is scraping metrics:
   - Go to http://localhost:9090/targets
   - Verify `rca_core` target is "UP"

2. Check metrics are being exposed:
   ```powershell
  curl http://localhost:8001/metrics
   ```

3. Re-import dashboard

### Issue: Templates not loading

1. Verify config file exists (IN WSL):
   ```bash
   test -f ../../config/itsm_config.json && echo "File exists" || echo "File not found"
   ```

2. Validate JSON syntax (IN WSL):
   ```bash
   cat ../../config/itsm_config.json | jq '.'
   ```

3. Check API logs for errors (IN WSL):
   ```bash
   docker-compose logs rca_core | grep "template"
   ```

---

## Useful Commands (ALL IN WSL)

**Remember: Open WSL terminal first with `wsl` command**

### View all running containers
```bash
docker-compose ps
```

### View logs for all services
```bash
docker-compose logs -f
```

### View logs for specific service
```bash
docker-compose logs -f rca_core
```

### Restart a service
```bash
docker-compose restart rca_core
```

### Stop all services
```bash
docker-compose down
```

### Stop all services and remove volumes (CAUTION: Deletes data!)
```bash
docker-compose down -v
```

### Rebuild API after code changes
```bash
docker-compose up -d --build rca_core
```

### Execute commands inside containers
```bash
# Python shell
docker-compose exec rca_core python

# Bash shell
docker-compose exec rca_core bash

# Database shell
docker-compose exec db psql -U rca_user -d rca_engine
```

---

## Next Steps After Deployment

1. **Configure ITSM Credentials** (if using ServiceNow/Jira):
   - Edit `deploy/docker/.env` (can edit in Windows, changes reflected in WSL)
   - Uncomment and fill in SERVICENOW_* and JIRA_* variables
   - Restart API in WSL: `docker-compose restart rca_core`

2. **Set Up UI** (if needed - IN WSL):
   ```bash
   docker-compose up -d ui
   ```
   - Access at http://localhost:3000 (from Windows browser)

3. **Review Monitoring** (access from Windows browser):
   - Check Grafana dashboard: http://localhost:3001
   - Review Prometheus alerts: http://localhost:9090/alerts
   - Set up Alertmanager for notifications

4. **Create Test Tickets** (IN WSL):
   - Test template creation
   - Verify SLA tracking
   - Check metrics update

5. **Security Hardening**:
   - Change default passwords in .env
   - Configure SSL/TLS for production
   - Set up proper authentication

---

## Deployment Checklist

- [ ] Docker Desktop started
- [ ] Core services running (db, redis, rca_core)
- [ ] Database migration applied (70a4e9f6d8c2)
- [ ] API health check passes
- [ ] Templates endpoint accessible
- [ ] Metrics endpoint shows ITSM metrics
- [ ] Monitoring stack running (prometheus, grafana)
- [ ] Grafana dashboard imported
- [ ] Prometheus alerts loaded
- [ ] Template configuration created
- [ ] Dry-run template test successful

---

## Support

For issues or questions:
- **Documentation:** See `IMPLEMENTATION_COMPLETE.md` for full feature details
- **Runbook:** See `docs/ITSM_RUNBOOK.md` for operational procedures
- **Quick Start:** See `docs/ITSM_QUICKSTART.md` for usage guide

---

**Deployment Version:** 1.0  
**Last Updated:** October 12, 2025  
**Status:** Ready for Deployment
