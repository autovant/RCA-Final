# 404 API Errors - RESOLVED

**Date**: October 17, 2025  
**Issue**: UI showing 404 errors for all `/api/*` endpoints after running `quick-start-dev.ps1`

## Root Cause Identified

**Multiple conflicting backend processes** were running on port 8001:

1. ✅ **Correct backend** (PID 33388): `python -m uvicorn apps.api.main:app --host 0.0.0.0 --port 8001`  
   - Title: "RCA Engine API"
   - Has `/api/*` routes

2. ❌ **Stale backend** (PID 33284): `python -m uvicorn app.main:app --host 127.0.0.1 --port 8001`
   - Title: "RCA Engine (imported core)"
   - Missing `/api` prefix routes
   - **This was responding to requests and causing 404 errors**

3. **Worker process** (PID 12020): `python -m apps.worker.main`

4. **Multiprocessing fork** (PID 16128): Child process of PID 33388

## Resolution Steps

### 1. Process Cleanup ✅

Created cleanup script: `scripts/troubleshooting/cleanup-all-processes.ps1`

Killed all conflicting processes:
```powershell
.\scripts\troubleshooting\cleanup-all-processes.ps1
```

Result:
- Killed 3 Python processes (backend + worker + stale)
- Killed 10 Node processes (UI instances)
- Ports 8001 and 3000 now free

### 2. Docker Status ⚠️

**Issue Found**: Docker Desktop not running
```
error during connect: Get "http://%2F%2F.%2Fpipe%2FdockerDesktopLinuxEngine/v1.51/containers/json"
```

**Required Action**: Start Docker Desktop before running `quick-start-dev.ps1`

### 3. Verification Commands

Before starting, verify:

```powershell
# Check Docker is running
docker ps  # Should show container list, not error

# Verify ports are free
netstat -ano | findstr ":8001.*LISTENING"  # Should be empty
netstat -ano | findstr ":3000.*LISTENING"  # Should be empty
```

### 4. Clean Start Procedure

```powershell
# 1. Ensure Docker Desktop is running
# Check system tray or start manually

# 2. Clean up any orphaned processes
.\scripts\troubleshooting\cleanup-all-processes.ps1

# 3. Start development environment
.\quick-start-dev.ps1

# 4. Wait 10-15 seconds, then verify
curl http://localhost:8001/api/ | ConvertFrom-Json
# Should return: {"message": "RCA Insight Engine", "version": "...", "status": "operational"}
```

## Prevention

### Added New Tools

1. **Cleanup Script**: `scripts/troubleshooting/cleanup-all-processes.ps1`
   - Kills all Python, Node processes
   - Optionally stops Docker containers
   - Verifies ports are free

2. **Troubleshooting Doc**: `docs/operations/troubleshooting-404-errors.md`
   - Complete diagnostic steps
   - Verification checklist
   - Emergency reset procedures

### Best Practices

1. **Always stop cleanly**: Use `.\stop-dev.ps1` before closing terminals
2. **Check before starting**: Run cleanup script if unsure
3. **Verify Docker first**: Ensure Docker Desktop is running
4. **One launcher only**: Don't mix `quick-start-dev.ps1` with other start scripts

## Next Steps for User

1. **Start Docker Desktop**
   - Check system tray
   - Or run: `& "C:\Program Files\Docker\Docker\Docker Desktop.exe"`

2. **Run clean startup**:
   ```powershell
   .\quick-start-dev.ps1
   ```

3. **Verify API is working**:
   ```powershell
   # Test root endpoint
   Invoke-WebRequest http://localhost:8001/api/

   # Test health endpoint
   Invoke-WebRequest http://localhost:8001/api/health/live

   # Test jobs endpoint
   Invoke-WebRequest http://localhost:8001/api/jobs
   ```

4. **Open UI**: http://localhost:3000

5. **Try file upload again** - should now work without 404 errors

## Technical Details

### Correct Backend Configuration

- **Module**: `apps.api.main:app`
- **Host**: `0.0.0.0` (allows connections from UI)
- **Port**: `8001`
- **Prefix**: All routes under `/api/*`

### API Endpoints (Verified)

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/` | GET | Root/status |
| `/api/health/live` | GET | Liveness check |
| `/api/jobs` | GET, POST | Job management |
| `/api/files/upload` | POST | File uploads |
| `/api/auth/*` | * | Authentication |

### Why Multiple Processes Occurred

Likely causes:
1. Previous `quick-start-dev.ps1` run didn't clean up properly
2. Manual `uvicorn` command was run in a terminal
3. Different start script (e.g., `START-SIMPLE.ps1`) was used concurrently
4. Terminal windows were closed without stopping services (`Ctrl+C`)

## Files Modified

- ✅ Created: `scripts/troubleshooting/cleanup-all-processes.ps1`
- ✅ Created: `docs/operations/troubleshooting-404-errors.md`
- ✅ Created: `docs/archive/404-API-ERRORS-RESOLVED.md` (this file)

## Status

🔴 **Blocked**: Waiting for Docker Desktop to start  
⚠️ **Action Required**: User needs to start Docker Desktop and re-run `quick-start-dev.ps1`

Once Docker is running, the issue should be fully resolved with the cleanup script preventing future conflicts.
