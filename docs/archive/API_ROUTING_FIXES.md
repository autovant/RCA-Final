# API Routing Fixes Applied

## Issues Found

The frontend was trying to access the backend API with incorrect configuration:

### 1. **Wrong Port** ❌
- Frontend configured: `http://localhost:8000`
- Backend running on: `http://localhost:8001`
- **Result**: All API calls were hitting the wrong port (404 errors)

### 2. **Wrong API Prefix** ❌
- Frontend using: `/api/v1/tickets`
- Backend expects: `/api/tickets`
- **Result**: 404 Not Found errors

### 3. **Wrong Endpoint Paths** ❌
- Frontend calling: `/api/v1/tickets/toggle`
- Backend expects: `/api/tickets/settings/state`
- **Result**: 422 Unprocessable Entity errors

## Fixes Applied ✅

### Files Changed:

1. **`ui/.env.local`**
   ```env
   NEXT_PUBLIC_API_BASE_URL=http://localhost:8001
   ```
   Changed from port 8000 → 8001

2. **`ui/src/lib/api/tickets.ts`**
   - Changed `NEXT_PUBLIC_API_URL` → `NEXT_PUBLIC_API_BASE_URL`
   - Changed default port from 8000 → 8001
   - Changed base path from `/api/v1` → `/api`
   - Fixed toggle endpoints: `/tickets/toggle` → `/tickets/settings/state`

3. **Port Forwarding Cleanup** ⚠️ **REQUIRED**
   - Removed port 8001 and 3000 forwarding (conflicted with native Windows apps)
   - Kept port 15432 (PostgreSQL) and 16379 (Redis) forwarding for Docker containers
   - **Must run as Administrator**: `.\cleanup-port-forwarding-hybrid.ps1`

## Backend API Structure (Correct)

All API endpoints are under `/api` prefix:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/jobs` | GET | List all jobs |
| `/api/jobs` | POST | Create new job |
| `/api/jobs/{id}` | GET | Get job details |
| `/api/jobs/{id}/events` | GET | Get job events |
| `/api/jobs/{id}/stream` | GET | SSE stream |
| `/api/tickets/{job_id}` | GET | List tickets for job |
| `/api/tickets` | POST | Create ticket |
| `/api/tickets/dispatch` | POST | Batch create tickets |
| `/api/tickets/settings/state` | GET | Get toggle state |
| `/api/tickets/settings/state` | PUT | Update toggle state |
| `/api/summary/{id}` | GET | Get RCA summary |
| `/api/conversation/{id}` | GET | Get conversation |
| `/api/files/jobs/{id}` | GET | List job files |

## Next Steps

### 1. **CRITICAL**: Remove Port Forwarding Conflicts ⚠️

**Run this first as Administrator:**
```powershell
.\cleanup-port-forwarding-hybrid.ps1
```

**Why?** The port forwarding rules for 8001 and 3000 were set up for Docker containers, but in hybrid mode, the backend and frontend run natively on Windows. These forwarding rules prevent the native apps from binding to those ports.

### 2. Restart Services

After cleaning up port forwarding:
```powershell
.\stop-local-windows.ps1
.\start-local-hybrid.ps1
```

### 2. Clear Browser Cache

The browser may have cached the failed API calls:
- Press **Ctrl+Shift+R** (hard refresh)
- Or open DevTools → Network tab → Check "Disable cache"

### 3. Verify API Access

Once restarted, check that the frontend can reach the backend:
- Open: http://localhost:3000
- Open DevTools → Console
- You should see successful API calls to `localhost:8001`

## Expected Result

After restart, all API calls should succeed:
- ✅ `/api/jobs` returns job list
- ✅ `/api/tickets/settings/state` returns toggle state
- ✅ `/api/tickets/{job_id}` returns tickets (or uses fallback demo data gracefully)
- ✅ No more 404 or 422 errors in console

## Notes

- The "demo-job" errors are **expected** when no real jobs exist yet
- The frontend gracefully falls back to sample tickets in this case
- Once you create a real job, select it, and the ticket API will work properly
