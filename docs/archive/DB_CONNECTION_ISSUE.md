# CRITICAL ISSUE: Database Connection Through Port Forwarding

## Problem Summary

The hybrid deployment setup faces a **fundamental compatibility issue** with PostgreSQL connections through Windows `netsh` port forwarding:

### Root Cause
- **asyncpg** (PostgreSQL async driver) maintains persistent connections
- **netsh portproxy** in Windows is designed for short-lived HTTP connections
- **Windows networking** drops long-lived TCP connections through port proxy
- **Error**: `ConnectionResetError: [WinError 64] The specified network name is no longer available`

### What We Tried

1. ✅ **Fixed missing dependencies** (`python-json-logger`, `email-validator`, `sse-starlette`)
2. ✅ **Fixed API routing** (port 8000 → 8001, `/api/v1` → `/api`)
3. ✅ **Disabled SSL** for asyncpg (`connect_args={"ssl": False}`)
4. ❌ **Port forwarding remains unstable** for persistent database connections

## Why This Happens

```
Backend (Windows) → localhost:15432 → netsh portproxy → WSL 172.28.36.28:15432 → Docker Container
                                           ↑
                                    BREAKS HERE
```

Windows **netsh portproxy** is not designed for:
- Long-lived database connections
- High-frequency keep-alive packets
- PostgreSQL wire protocol over TCP

## Recommended Solutions

### Option 1: Pure Windows Deployment (RECOMMENDED)
Use the native Windows deployment scripts that install PostgreSQL and Redis as Windows services:

```powershell
# Setup (run once)
.\setup-local-windows.ps1

# Start services
.\start-local-windows.ps1

# Stop services
.\stop-local-windows.ps1

# Check status
.\status-local-windows.ps1
```

**Advantages:**
- ✅ No Docker dependencies
- ✅ No port forwarding issues
- ✅ Native Windows performance
- ✅ Persistent services across reboots
- ✅ Standard PostgreSQL/Redis installations

### Option 2: Full Docker Deployment
Run everything in Docker (including backend and frontend):

```powershell
wsl
cd /mnt/c/Users/syed.shareef/.vscode/repos/RCA\ -\ v7/RCA-Final
docker compose -f docker-compose.dev.yml up
```

**Advantages:**
- ✅ All services in same network (no port forwarding)
- ✅ Consistent environment
- ✅ Easy teardown/rebuild

**Disadvantages:**
- ❌ Slower hot-reload
- ❌ More complex debugging
- ❌ Docker Desktop blocked (need Docker in WSL)

### Option 3: Make Database Connection Optional
Modify the backend to start without database and lazy-load connections:

```python
# In core/db/database.py - Change initialize() to not fail on connection error
async def initialize(self):
    try:
        # ... connection code ...
    except Exception as e:
        logger.warning(f"Database unavailable at startup: {e}")
        logger.info("Backend will retry on first request")
        # Don't raise - let app start anyway
```

**Advantages:**
- ✅ Backend starts immediately
- ✅ Graceful degradation
- ✅ Better for development

**Disadvantages:**
- ❌ Need error handling on every DB call
- ❌ Less obvious when DB is down

## Current State

### Working ✅
- All Python dependencies installed
- API routing fixed
- Frontend configured correctly
- Docker containers running and healthy
- Port forwarding configured (but unstable)

### Not Working ❌
- Backend startup fails due to database connection timeout
- Hybrid deployment cannot maintain stable PostgreSQL connection through port forwarding

## Next Steps

**Choose ONE of the approaches above:**

1. **For simplicity**: Use Option 1 (Pure Windows) - Run `.\setup-local-windows.ps1`
2. **For Docker consistency**: Use Option 2 (Full Docker in WSL)
3. **For hybrid flexibility**: Implement Option 3 (optional database connection)

## Files Modified

- ✅ `requirements.txt` - Added missing dependencies
- ✅ `ui/.env.local` - Fixed API port and base URL
- ✅ `ui/src/lib/api/tickets.ts` - Fixed API endpoints
- ✅ `core/db/database.py` - Added SSL disable for asyncpg
- ✅ `.env` - Configured for hybrid deployment

## Technical Details

### Error Pattern
```
INFO: Starting RCA Engine API...
INFO: Initializing database connection pool...
[23 second timeout]
ERROR: ConnectionResetError: [WinError 64] The specified network name is no longer available
ERROR: Application startup failed. Exiting.
```

### Why Port Forwarding Fails
- Windows `netsh interface portproxy` is a kernel-mode NAT
- Designed for stateless protocols (HTTP)
- PostgreSQL uses stateful wire protocol with connection pooling
- asyncpg maintains persistent connections with keep-alive
- Windows firewall or kernel drops "idle" connections
- Result: Connection reset during PostgreSQL handshake

### Alternative: WSL2 Mirrored Networking
WSL2 mirrored networking would solve this, BUT it's **incompatible with Docker bridge networks**. We tried this earlier and had to revert to NAT mode.

## Documentation Created

- `API_ROUTING_FIXES.md` - API configuration fixes
- `DEPENDENCIES_FIXED.md` - Missing Python packages
- `cleanup-port-forwarding-hybrid.ps1` - Port forwarding cleanup script
- `DB_CONNECTION_ISSUE.md` - This file

## Recommendation

**Use Pure Windows Deployment** (`.\setup-local-windows.ps1`) as it avoids all these networking complexities while providing the best development experience.
