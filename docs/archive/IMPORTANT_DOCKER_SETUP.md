# ⚠️ CRITICAL: Docker Setup for RCA Engine

## 🚨 IMPORTANT: Always Use WSL for Docker Commands

**DO NOT run Docker commands directly from Windows PowerShell or CMD!**

### Why?

This project is configured to use Docker through **WSL (Windows Subsystem for Linux)**, not Docker Desktop on Windows directly. Running Docker commands from Windows PowerShell will result in authentication errors and port binding issues.

---

## ✅ Correct Way to Start Backend

### Method 1: Using the Provided Batch Script (Recommended)

```powershell
# From Windows PowerShell in project root:
cd "c:\Users\syed.shareef\.vscode\repos\RCA - v7\RCA-Final"
.\quick-start-backend.bat
```

This script automatically:
- Runs Docker commands through WSL
- Restarts containers to clear port bindings
- Starts database, Redis, and Ollama
- Starts the RCA API server

### Method 2: Manual WSL Commands

```powershell
# From Windows PowerShell, execute commands in WSL:
wsl bash -c "cd /mnt/c/Users/syed.shareef/.vscode/repos/RCA\ -\ v7/RCA-Final && docker compose -f deploy/docker/docker-compose.yml up -d"
```

### Method 3: Direct WSL Terminal

```bash
# Open WSL terminal first, then:
cd /mnt/c/Users/syed.shareef/.vscode/repos/RCA\ -\ v7/RCA-Final
docker compose -f deploy/docker/docker-compose.yml up -d
```

---

## ❌ WRONG: Commands That Will Fail

### DON'T Do This:
```powershell
# ❌ WRONG - Running Docker from Windows PowerShell directly
docker ps
docker compose up
python -m uvicorn apps.api.main:app --port 8000
```

**Error you'll see:**
```
Error response from daemon: Sign in to continue using Docker Desktop. 
Membership in the [perficientinc] organization is required.
```

---

## 🔍 How to Verify Backend is Running

### Step 1: Check Containers via WSL
```powershell
# From Windows PowerShell:
wsl bash -c "docker ps"
```

**Expected Output:**
```
CONTAINER ID   IMAGE       STATUS         PORTS                    NAMES
xxxxxxxxxxxx   rca_core    Up X minutes   0.0.0.0:8000->8000/tcp   rca_core
xxxxxxxxxxxx   postgres    Up X minutes   5432/tcp                 rca_db
xxxxxxxxxxxx   redis       Up X minutes   6379/tcp                 rca_redis
xxxxxxxxxxxx   ollama      Up X minutes   11434/tcp                rca_ollama
```

### Step 2: Check API Endpoint
```powershell
# Wait 10-15 seconds after starting, then:
curl http://localhost:8000/docs
# Or:
Invoke-RestMethod -Uri "http://localhost:8000/docs" -Method Get
```

### Step 3: Check Container Logs
```powershell
# View API logs through WSL:
wsl bash -c "docker logs rca_core --tail 50"
```

---

## 🐛 Common Issues and Solutions

### Issue 1: "Sign in to Docker Desktop" Error

**Cause**: Trying to run Docker commands from Windows PowerShell directly

**Solution**: Always use WSL:
```powershell
wsl bash -c "docker ps"
```

### Issue 2: Port 8000 Already in Use

**Cause**: Previous container still running

**Solution**:
```powershell
# Restart containers via WSL:
wsl bash -c "cd /mnt/c/Users/syed.shareef/.vscode/repos/RCA\ -\ v7/RCA-Final && docker compose -f deploy/docker/docker-compose.yml restart"
```

### Issue 3: Backend Not Responding

**Cause**: Container might be starting up (can take 10-30 seconds)

**Solution**:
```powershell
# Check logs for startup progress:
wsl bash -c "docker logs rca_core -f"
# Press Ctrl+C to stop following logs
```

### Issue 4: Database Connection Errors

**Cause**: PostgreSQL container not fully started

**Solution**:
```powershell
# Restart backend services in order:
wsl bash -c "cd /mnt/c/Users/syed.shareef/.vscode/repos/RCA\ -\ v7/RCA-Final && docker compose -f deploy/docker/docker-compose.yml up -d db redis ollama"
# Wait 10 seconds
Start-Sleep -Seconds 10
# Then start API:
wsl bash -c "cd /mnt/c/Users/syed.shareef/.vscode/repos/RCA\ -\ v7/RCA-Final && docker compose -f deploy/docker/docker-compose.yml up -d rca_core"
```

---

## 📋 Quick Reference Commands

### Start Backend (Recommended)
```powershell
.\quick-start-backend.bat
```

### Stop Backend
```powershell
wsl bash -c "cd /mnt/c/Users/syed.shareef/.vscode/repos/RCA\ -\ v7/RCA-Final && docker compose -f deploy/docker/docker-compose.yml down"
```

### Restart Backend
```powershell
wsl bash -c "cd /mnt/c/Users/syed.shareef/.vscode/repos/RCA\ -\ v7/RCA-Final && docker compose -f deploy/docker/docker-compose.yml restart"
```

### View Logs
```powershell
# All services:
wsl bash -c "cd /mnt/c/Users/syed.shareef/.vscode/repos/RCA\ -\ v7/RCA-Final && docker compose -f deploy/docker/docker-compose.yml logs --tail 50"

# Just API:
wsl bash -c "docker logs rca_core --tail 50"
```

### Check Container Status
```powershell
wsl bash -c "docker ps"
```

---

## 🎯 Complete Startup Sequence

### 1. Start Backend
```powershell
cd "c:\Users\syed.shareef\.vscode\repos\RCA - v7\RCA-Final"
.\quick-start-backend.bat
```

Wait 15-20 seconds for containers to fully start.

### 2. Verify Backend
```powershell
# Check containers:
wsl bash -c "docker ps"

# Check API health:
curl http://localhost:8000/docs
```

### 3. Start Frontend
```powershell
cd "c:\Users\syed.shareef\.vscode\repos\RCA - v7\RCA-Final"
.\start-ui-windows.bat
```

### 4. Access Application
- **UI**: http://localhost:3000 (or 3001 if 3000 is in use)
- **API Docs**: http://localhost:8000/docs
- **API Base**: http://localhost:8000

---

## 📝 Key Takeaways

1. ✅ **ALWAYS use WSL** for Docker commands
2. ✅ **Use `quick-start-backend.bat`** for easiest startup
3. ✅ **Wait 15-20 seconds** after starting containers
4. ✅ **Check logs via WSL** if issues occur
5. ❌ **NEVER run `docker` directly** from Windows PowerShell
6. ❌ **NEVER run `python -m uvicorn` directly** (use Docker instead)

---

## 🔗 Related Files

- `quick-start-backend.bat` - Automated backend startup script
- `start-ui-windows.bat` - UI startup script
- `deploy/docker/docker-compose.yml` - Docker configuration
- `WSL_NETWORKING_FIX.md` - Network troubleshooting
- `WSL_QUICKSTART.md` - WSL setup guide

---

**Last Updated**: October 13, 2025

**Status**: ✅ Critical Information - Always Reference This!
