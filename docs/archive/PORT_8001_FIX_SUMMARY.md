# Port Configuration Fix Summary

**Date**: October 15, 2025  
**Issue**: Frontend was trying to connect to backend on port 8000, but backend runs on port 8001

## Changes Made

### 1. Frontend Configuration Files

#### `ui\.env.local`
- **Changed**: `NEXT_PUBLIC_API_BASE_URL=http://localhost:8000`
- **To**: `NEXT_PUBLIC_API_BASE_URL=http://localhost:8001`

#### `ui\src\data\jobsPreview.ts`
- **Changed**: Default fallback `"http://localhost:8000"`
- **To**: `"http://localhost:8001"`
- **Line**: `export const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8001";`

### 2. Example/Template Configuration Files

#### `.env.example`
- **Changed**: `NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1`
- **To**: `NEXT_PUBLIC_API_URL=http://localhost:8001/api/v1`

#### `deploy\docker\.env`
- **Changed**: 
  - `NEXT_PUBLIC_API_URL=http://localhost:8000`
  - `NEXT_PUBLIC_WS_URL=ws://localhost:8000`
- **To**: 
  - `NEXT_PUBLIC_API_URL=http://localhost:8001`
  - `NEXT_PUBLIC_WS_URL=ws://localhost:8001`

### 3. Startup Script Enhancement

#### `start-local-hybrid.ps1`
Added automatic UI configuration check and repair:
- Now checks if `ui\.env.local` exists
- Detects if it has the wrong port (8000)
- Automatically creates or updates it to use port 8001
- Provides clear feedback about the fix

## What Was Fixed

1. ❌ **Error**: `GET http://localhost:8000/api/jobs net::ERR_CONNECTION_REFUSED`
2. ✅ **Fixed**: Frontend now correctly connects to `http://localhost:8001/api/jobs`

## Port Configuration Standard

**Backend API**: Port **8001**
- Health check: `http://localhost:8001/health`
- API docs: `http://localhost:8001/docs`
- API base: `http://localhost:8001/api`

**Frontend UI**: Port **3000**
- Application: `http://localhost:3000`

**Databases** (Docker containers):
- PostgreSQL: Port **15432** (mapped from 5432)
- Redis: Port **16379** (mapped from 6379)

## How to Apply Fixes

### Option 1: Re-run Startup Script (Automatic)
```powershell
.\start-local-hybrid.ps1
```
The script now automatically fixes the UI configuration.

### Option 2: Manual Fix (If Needed)
If you need to manually update after pulling code:
```powershell
# Update UI environment
echo "NEXT_PUBLIC_API_BASE_URL=http://localhost:8001" | Out-File -FilePath ui\.env.local -Encoding UTF8

# Restart frontend (if running)
cd ui
npm run dev
```

## Testing the Fix

After starting the application:

1. **Check Backend**:
   ```powershell
   curl http://localhost:8001/health
   ```
   Should return health status.

2. **Check Frontend**:
   - Open browser to `http://localhost:3000`
   - Open browser DevTools Console (F12)
   - Should see successful API calls to `localhost:8001`
   - No more "ERR_CONNECTION_REFUSED" errors

3. **Check Jobs API**:
   ```powershell
   curl http://localhost:8001/api/jobs
   ```
   Should return jobs list (or empty array if no jobs exist).

## Notes

- The backend has always been configured to use port 8001
- The issue was only in frontend configuration files using old port 8000
- Next.js requires a restart to pick up `.env.local` changes
- If you still see errors, clear browser cache or do a hard refresh (Ctrl+Shift+R)

## Related Files

Files that were **correctly** already using 8001:
- `start-local-hybrid.ps1` - Backend startup command
- `ui\src\lib\api\tickets.ts` - Had correct fallback to 8001

Files that had **incorrect** port 8000:
- `ui\.env.local` ❌ → ✅ Fixed
- `ui\src\data\jobsPreview.ts` ❌ → ✅ Fixed
- `.env.example` ❌ → ✅ Fixed
- `deploy\docker\.env` ❌ → ✅ Fixed

## Future Considerations

To prevent this issue:
1. Use a single source of truth for port configuration
2. Consider using environment variable validation on startup
3. Add port configuration to setup documentation
4. Update any CI/CD configurations to use port 8001
