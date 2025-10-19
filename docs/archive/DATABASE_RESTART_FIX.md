# Database Keeps Stopping - Complete Fix

## Issues Found

### 1. Database Container Exiting
The PostgreSQL container keeps stopping/exiting. This appears to be related to connection attempts.

### 2. Wrong Database Name Still Being Used
Logs show:
```
FATAL:  database "rca_engine" does not exist
```

But we configured `rca_engine_final` in `.env`. The backend isn't reading the updated config.

## Root Causes

1. **Backend not reloading .env**: Changes to `.env` files require backend restart
2. **Database container instability**: Multiple failed connection attempts may cause crashes
3. **Stale environment**: Backend process started before `.env` was updated

## ✅ Complete Fix

### Step 1: Stop All Services
```powershell
.\stop-local-hybrid.ps1
```

### Step 2: Verify Database Configuration
Check that `.env` has the correct database name:
```powershell
Get-Content .env | Select-String "POSTGRES_DB"
```

Should show:
```
POSTGRES_DB=rca_engine_final
```

If not, fix it:
```powershell
(Get-Content .env) -replace 'POSTGRES_DB=rca_engine$', 'POSTGRES_DB=rca_engine_final' | Set-Content .env
```

### Step 3: Ensure Database Container Stays Running
```powershell
# Start database
wsl docker start rca_db

# Wait for it to be healthy
Start-Sleep -Seconds 5

# Verify it's running
wsl docker ps --filter "name=rca_db"
```

### Step 4: Test Database Connection
```powershell
$env:PGPASSWORD='rca_password_change_in_production'
wsl docker exec -e PGPASSWORD=$env:PGPASSWORD rca_db psql -U rca_user -d rca_engine_final -c "SELECT 1;"
```

Should return:
```
 ?column? 
----------
        1
```

### Step 5: Start Backend Fresh
Now that the database is stable and config is correct:
```powershell
.\start-local-hybrid-complete.ps1
```

## Prevention: Update Startup Script

The startup script should verify the database name before starting backend. I'll create an enhanced version.

## Verification Checklist

Before starting backend, verify:
- ✅ `.env` has `POSTGRES_DB=rca_engine_final`
- ✅ `.env.local` has `POSTGRES_DB=rca_engine_final`  
- ✅ Database container is running and healthy
- ✅ Database `rca_engine_final` exists
- ✅ Can connect to database

Run this quick check:
```powershell
# Check config
Write-Host "Config Check:" -ForegroundColor Cyan
Get-Content .env | Select-String "POSTGRES_DB"

# Check database container
Write-Host "`nDatabase Container:" -ForegroundColor Cyan
wsl docker ps --filter "name=rca_db" --format "{{.Status}}"

# Check database exists
Write-Host "`nDatabase Exists:" -ForegroundColor Cyan
wsl docker exec rca_db psql -U rca_user -d postgres -c "\l" | Select-String "rca_engine_final"
```

## Why Database Container Keeps Stopping

The container has `restart: unless-stopped` in docker-compose.yml, but:
1. Multiple failed connection attempts from backend
2. Backend trying wrong database name (`rca_engine` instead of `rca_engine_final`)
3. This causes authentication/connection errors
4. Repeated errors may trigger container health checks to fail

## Long-term Solution

Update docker-compose.yml to be more resilient:
```yaml
healthcheck:
  test: ["CMD-SHELL", "pg_isready -U rca_user -d rca_engine_final"]
  interval: 10s
  timeout: 5s
  retries: 10  # More retries
  start_period: 30s
```

## If Backend Still Can't Connect

### Check environment variables are loaded:
In backend window, before `uvicorn` starts:
```powershell
$env:POSTGRES_DB
```

Should show: `rca_engine_final`

### Force reload .env:
```powershell
# In the main directory
Copy-Item .env.local .env -Force

# Verify
Get-Content .env | Select-String "POSTGRES"
```

### Manual backend start with explicit env:
```powershell
& .\venv\Scripts\Activate.ps1
$env:PYTHONPATH = (Get-Location).Path
$env:POSTGRES_DB = "rca_engine_final"
$env:POSTGRES_HOST = "localhost"
$env:POSTGRES_PORT = "15432"
$env:POSTGRES_USER = "rca_user"
$env:POSTGRES_PASSWORD = "rca_password_change_in_production"

python -m uvicorn apps.api.main:app --host 0.0.0.0 --port 8002 --reload
```

## Summary

The backend is trying to connect to `rca_engine` (wrong) instead of `rca_engine_final` (correct).

**Fix**: 
1. Stop everything
2. Verify `.env` has correct database name
3. Start database container
4. Start backend fresh (it will read updated `.env`)

**Status**: Database is now running ✅  
**Next**: Restart backend to pick up correct config
