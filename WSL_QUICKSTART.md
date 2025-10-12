# 🚀 Quick Start - WSL Docker Deployment

## For Windows Users: Docker MUST Use WSL

### Step 1: Open WSL Terminal

```powershell
# From PowerShell, open WSL
wsl
```

If WSL is not installed, run this **first** in PowerShell as Administrator:
```powershell
wsl --install
```
Then restart your computer.

---

### Step 2: Navigate to Project in WSL

```bash
# In WSL terminal, navigate to project
cd "/mnt/c/Users/syed.shareef/.vscode/repos/RCA - v7/RCA-Final/deploy/docker"
```

---

### Step 3: Start Services

```bash
# Start database and Redis
docker-compose up -d db redis

# Wait 30 seconds for DB to initialize
sleep 30

# Start API (first build takes 5 minutes)
docker-compose up -d --build rca_core

# Run database migration
docker-compose exec rca_core alembic upgrade head

# Start monitoring
docker-compose --profile monitoring up -d prometheus grafana
```

---

### Step 4: Verify Deployment

```bash
# Test API health
curl http://localhost:8000/api/v1/health

# Test templates endpoint
curl http://localhost:8000/api/v1/tickets/templates

# Check services are running
docker-compose ps
```

---

### Step 5: Access Services (From Windows Browser)

- **API:** http://localhost:8000
- **API Docs:** http://localhost:8000/docs
- **Grafana:** http://localhost:3001 (admin/admin)
- **Prometheus:** http://localhost:9090

---

## Common Commands (All in WSL)

```bash
# View logs
docker-compose logs -f rca_core

# Restart service
docker-compose restart rca_core

# Stop all
docker-compose down

# Rebuild after code changes
docker-compose up -d --build rca_core
```

---

## Troubleshooting

### Docker not working in PowerShell?
**Solution:** You MUST use WSL. Run `wsl` first, then docker commands.

### "Cannot connect to Docker daemon"?
**Solution:** Make sure Docker Desktop is running and WSL integration is enabled in Docker Desktop settings.

### Slow performance?
**Solution:** Keep project files in WSL filesystem for better performance. Consider moving project to `~/projects/` in WSL.

---

## Next Steps

1. **Configure templates:** Edit `config/itsm_config.json` (can edit in Windows)
2. **Import Grafana dashboard:** See DOCKER_DEPLOYMENT_GUIDE.md Step 8
3. **Configure ITSM credentials:** Edit `deploy/docker/.env` for ServiceNow/Jira

---

**Full Details:** See `DOCKER_DEPLOYMENT_GUIDE.md` for comprehensive instructions.
