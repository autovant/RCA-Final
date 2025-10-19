# RCA Backend API 404 Error - Troubleshooting

## Problem

After running `.\quick-start-dev.ps1`, the UI shows 404 errors when trying to access API endpoints:
- `http://localhost:8001/api/jobs` → 404
- `http://localhost:8001/api/files/upload` → 404

## Root Cause

**Multiple conflicting backend processes running on port 8001**, including:
1. **Correct backend**: `python -m uvicorn apps.api.main:app --host 0.0.0.0 --port 8001`
2. **Old/stale backend**: From previous runs or different launch scripts

The old backends don't have the `/api` prefix routes, causing 404 errors.

## Immediate Fix

### Step 1: Kill All Backend Processes

```powershell
# Kill all Python processes (be careful if you have other Python apps running)
Get-Process python -ErrorAction SilentlyContinue | Stop-Process -Force

# OR kill only processes using port 8001:
$pids = netstat -ano | findstr ":8001.*LISTENING" | ForEach-Object { ($_ -split '\s+')[-1] } | Select-Object -Unique
foreach ($p in $pids) { Stop-Process -Id $p -Force -ErrorAction SilentlyContinue }
```

### Step 2: Verify Port is Free

```powershell
netstat -ano | findstr ":8001"
# Should return empty or only TIME_WAIT connections
```

### Step 3: Restart Clean

```powershell
.\quick-start-dev.ps1 -NoWorker -NoBrowser
```

### Step 4: Verify Correct Backend

```powershell
# Should return: {"message": "RCA Insight Engine", "version": ..., "status": "operational"}
curl http://localhost:8001/api/ | ConvertFrom-Json

# Should show "RCA Engine API" title
(Invoke-WebRequest http://localhost:8001/openapi.json).Content | ConvertFrom-Json | Select-Object -ExpandProperty info
```

## Prevention

### Use the Cleanup Script

Before starting, always run:

```powershell
# Kill all RCA-related processes
.\scripts/troubleshooting/cleanup-processes.ps1

# Then start fresh
.\quick-start-dev.ps1
```

### Check for Orphaned Processes

If you closed terminal windows without stopping services properly, use:

```powershell
# Find all Python processes with RCA-related commands
Get-WmiObject Win32_Process | 
  Where-Object { $_.CommandLine -like "*uvicorn*" -or $_.CommandLine -like "*apps.worker*" } |
  Select-Object ProcessId, CommandLine |
  Format-List
```

## Verification Checklist

✅ **Correct Backend Running**:
```powershell
# Test root endpoint
Invoke-WebRequest http://localhost:8001/api/ | Select-Object StatusCode, Content

# Test health endpoint
Invoke-WebRequest http://localhost:8001/api/health/live | Select-Object StatusCode
```

✅ **No Port Conflicts**:
```powershell
# Should show only ONE process group on 8001
netstat -ano | findstr ":8001.*LISTENING"
```

✅ **UI Can Connect**:
```powershell
# From the UI directory, check network requests
# Or open browser DevTools Network tab and look for successful 200 responses
```

## Related Issues

- **Issue**: UI connects but gets "Not Found" with proper status codes
- **Likely Cause**: Firewall blocking cross-origin requests
- **Fix**: Run `.\ENABLE-NETWORK-ACCESS.ps1` as Administrator

- **Issue**: Port 8001 already in use
- **Likely Cause**: Previous instance didn't shut down cleanly
- **Fix**: Use kill commands above

- **Issue**: WSL path mapping errors
- **Likely Cause**: Docker/WSL not running
- **Fix**: Start Docker Desktop and ensure WSL2 backend is active

## Emergency Reset

If nothing works, nuclear option:

```powershell
# 1. Kill everything Python
Get-Process python -ErrorAction SilentlyContinue | Stop-Process -Force

# 2. Kill Node/npm (UI)
Get-Process node -ErrorAction SilentlyContinue | Stop-Process -Force

# 3. Stop Docker containers
docker stop $(docker ps -q)

# 4. Wait for ports to release
Start-Sleep -Seconds 5

# 5. Fresh start
.\setup-dev-environment.ps1  # Re-run setup if needed
.\quick-start-dev.ps1
```

## Prevention Best Practices

1. **Always use stop script**: Run `.\stop-dev.ps1` before closing terminals
2. **Don't mix scripts**: Don't run multiple start scripts (quick-start, START-SIMPLE, etc.) simultaneously
3. **Check before starting**: Always verify no orphaned processes on ports 8000, 8001, 3000
4. **Use one launcher**: Stick to `quick-start-dev.ps1` for daily development

## See Also

- [Startup Scripts Documentation](../operations/startup-scripts.md)
- [Troubleshooting Guide](../operations/troubleshooting.md)
- Port Cleanup: `scripts/troubleshooting/cleanup-port-forwarding-hybrid.ps1`
- Network Setup: `ENABLE-NETWORK-ACCESS.ps1`
