# RCA Engine - Quick Start Guide

## ✅ Recommended Startup Script

Use this script to start all services:

```powershell
.\Start-Docker.ps1
```

This script will:
- Stop any existing Docker containers
- Start backend services in Docker (API, database, redis)
- Start UI in development mode on Windows (for full error messages)
- Check health status
- Open browser to http://localhost:3000
- Display helpful commands

## 🛑 To Stop Services

```powershell
.\Stop-Docker.ps1
```

## 📊 Service URLs

| Service | URL | Notes |
|---------|-----|-------|
| **Frontend UI** | http://localhost:3000 | Main web interface |
| **Backend API** | http://localhost:8000 | REST API |
| **API Docs** | http://localhost:8000/docs | Swagger documentation |
| **PostgreSQL** | localhost:15432 | Database (user: rca_user, db: rca_db) |
| **Redis** | localhost:16379 | Cache & queue |

## 🔧 Configuration

- **LLM Provider**: GitHub Copilot (configured in `deploy/docker/.env`)
- **Default Model**: gpt-4
- **GitHub Token**: Set in environment variables

## 📝 View Logs

```powershell
# Backend logs (follow mode)
wsl bash -c "docker logs -f rca_core"

# UI logs - check the terminal window that opened automatically
# (UI runs in dev mode on Windows for better error messages)

# Last 50 lines of backend logs
wsl bash -c "docker logs rca_core --tail 50"
```

## 🐛 Troubleshooting

### Containers keep restarting
Check logs for errors:
```powershell
wsl bash -c "docker logs rca_core --tail 100"
```

### Port conflicts
If you get port conflict errors, make sure no other services are using:
- Port 3000 (UI)
- Port 8000 (Backend API)
- Port 15432 (PostgreSQL)
- Port 16379 (Redis)

### Backend not responding
1. Check container is healthy:
   ```powershell
   wsl bash -c "docker ps --filter name=rca_core"
   ```

2. Test health endpoint:
   ```powershell
   Invoke-RestMethod -Uri "http://localhost:8000/api/health/live"
   ```

3. Check logs for errors

## 🚀 Testing GitHub Copilot Integration

1. Navigate to http://localhost:3000
2. Go to "Investigation" page
3. Upload a file (tests file upload fix)
4. Create a new job
5. Provider should default to "Copilot"
6. Model should default to "gpt-4"
7. Start the job and watch it process

Monitor backend logs to see Copilot token refresh:
```powershell
wsl bash -c "docker logs -f rca_core" | Select-String "Copilot"
```

## ❌ Deprecated Scripts

**Do NOT use these scripts** (they expect backend on Windows):
- ❌ `Start-RCA.ps1` - Expects backend running on Windows, tries to kill processes
- ❌ `START-SIMPLE.ps1` - Old configuration, wrong ports
- ❌ `START-ALL-STABLE.ps1` - Pre-Docker configuration

## 💾 Environment Files

- **Docker Environment**: `deploy/docker/.env`
  - Contains: GitHub token, provider settings, database credentials
  
- **UI Environment**: `ui/.env.local`
  - Contains: API URL (http://localhost:8000)

## 🔄 Restart Individual Services

```powershell
# Restart backend only
wsl bash -c "cd '/mnt/c/Users/syed.shareef/.vscode/repos/RCA - v7/RCA-Final/deploy/docker' && docker compose -f docker-compose.yml -f docker-compose.dev.yml restart rca_core"

# Restart UI - just close the terminal window and run:
cd "c:\Users\syed.shareef\.vscode\repos\RCA - v7\RCA-Final\ui"
npm run dev
```

## 📋 System Status Check

```powershell
# Check all containers
wsl bash -c "docker ps --filter name=rca --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'"

# Check which ports are in use
netstat -ano | findstr "8000 3000 15432 16379"
```
