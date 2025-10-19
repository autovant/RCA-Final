# Complete Startup Fix Summary

## Issues Fixed (In Order)

### 1. ✅ Port 8000 → 8001 Mismatch
**Problem**: Frontend calling `localhost:8000`, backend on `localhost:8001`  
**Error**: `GET http://localhost:8000/api/jobs net::ERR_CONNECTION_REFUSED`

**Fixed**:
- `ui\.env.local` - Updated to use port 8001
- `ui\src\data\jobsPreview.ts` - Default fallback to 8001
- `.env.example` - Documentation updated
- `deploy\docker\.env` - Docker config updated

---

### 2. ✅ Port 8001 Access Denied (Windows)
**Problem**: Port 8001 blocked by Windows service (Hyper-V/WinNAT)  
**Error**: `[WinError 10013] An attempt was made to access a socket in a way forbidden`

**Solution**: Use alternative port 8002
- Created `start-local-hybrid-alt-port.ps1` - Uses port 8002
- Created `fix-port-8001.ps1` - Admin tool to fix port 8001
- Auto-updates UI config to match backend port

---

### 3. ✅ Database Container Not Running
**Problem**: PostgreSQL container in "Created" state but not started  
**Error**: `connection was closed in the middle of operation`

**Fixed**:
- Manually started: `wsl docker start rca_db`
- Updated both startup scripts to auto-start stopped containers
- Added connectivity verification and auto-retry
- Better error messages and diagnostics

---

## 🎯 Current Configuration

### Working Setup
| Component | Port | Status |
|-----------|------|--------|
| Backend API | **8002** | ✅ Ready |
| Frontend UI | **3000** | ✅ Ready |
| PostgreSQL | **15432** | ✅ Running |
| Redis | **16379** | ✅ Running |

### Why Port 8002?
Port 8001 is often blocked by Windows Hyper-V/WinNAT services. Port 8002 avoids these conflicts.

---

## 🚀 How to Start Your App

### Recommended: Use Alternative Port Script
```powershell
.\start-local-hybrid-alt-port.ps1
```

**This script now**:
1. ✅ Checks if database containers exist
2. ✅ Starts stopped containers automatically
3. ✅ Verifies PostgreSQL connectivity
4. ✅ Auto-retries if port forwarding needs refresh
5. ✅ Configures UI to use correct backend port
6. ✅ Starts backend on port 8002
7. ✅ Starts frontend on port 3000

### Alternative: Standard Port (If 8001 Fixed)
```powershell
.\start-local-hybrid.ps1
```

Uses port 8001 (requires admin fix if blocked).

---

## 📝 Files Created/Modified

### Configuration Files
- ✅ `ui\.env.local` - Frontend API endpoint
- ✅ `ui\src\data\jobsPreview.ts` - API base URL
- ✅ `.env.example` - Documentation
- ✅ `deploy\docker\.env` - Docker deployment

### Startup Scripts (Enhanced)
- ✅ `start-local-hybrid.ps1` - Port 8001 version (improved)
- ✅ `start-local-hybrid-alt-port.ps1` - Port 8002 version (NEW)

### Fix/Diagnostic Tools (NEW)
- ✅ `fix-port-8001.ps1` - Admin tool to fix port access
- ✅ `verify-port-config.ps1` - Configuration checker

### Documentation (NEW)
- ✅ `PORT_8001_FIX_SUMMARY.md` - Port mismatch details
- ✅ `QUICK_FIX_PORT_8001.md` - Quick reference
- ✅ `FIX_PORT_8001_ERROR.md` - Windows access error guide
- ✅ `DATABASE_CONNECTION_FIXED.md` - Database startup fix
- ✅ `COMPLETE_STARTUP_FIX_SUMMARY.md` - This file

---

## ✅ What's Improved in Startup Scripts

### Before
- ❌ Only checked if containers were running
- ❌ Would fail if containers existed but stopped
- ❌ No retry logic for port forwarding
- ❌ Poor error messages

### After
- ✅ Checks both running AND stopped containers
- ✅ Auto-starts stopped containers
- ✅ Retries with container restart if connectivity fails
- ✅ Clear status messages and diagnostics
- ✅ Verifies connectivity before proceeding

---

## 🧪 Testing Your Setup

### 1. Check Database Containers
```powershell
wsl docker ps --filter "name=rca_"
```
Should show both `rca_db` and `rca_redis` as **Up**.

### 2. Test Database Connectivity
```powershell
Test-NetConnection -ComputerName 127.0.0.1 -Port 15432
```
Should show `TcpTestSucceeded : True`.

### 3. Test Backend API
After starting backend:
```powershell
curl http://localhost:8002/health
```
Should return health status JSON.

### 4. Test Frontend
Open browser to `http://localhost:3000`
- Press F12 for DevTools
- Check Console - should see API calls to `localhost:8002`
- No connection errors!

---

## 🔧 If You Still Have Issues

### Backend won't start
1. Check database is running: `wsl docker ps`
2. Check logs: `wsl docker logs rca_db --tail 50`
3. Restart database: `wsl docker restart rca_db`
4. Try fresh start: Close all windows, run script again

### Frontend can't reach backend
1. Check `ui\.env.local` has correct port
2. Clear Next.js cache: `Remove-Item -Recurse -Force ui\.next`
3. Hard refresh browser: `Ctrl+Shift+R`
4. Restart frontend

### Port still blocked
1. Use port 8002 (alternative script)
2. Or run admin fix: `.\fix-port-8001.ps1`
3. Or restart computer

---

## 📚 Quick Reference Commands

```powershell
# Start everything (recommended)
.\start-local-hybrid-alt-port.ps1

# Check configuration
.\verify-port-config.ps1

# Fix port access (admin)
.\fix-port-8001.ps1

# Check database status
wsl docker ps

# Start database manually
wsl docker start rca_db rca_redis

# View database logs
wsl docker logs rca_db --tail 50

# Test backend
curl http://localhost:8002/health

# Test database connection
Test-NetConnection 127.0.0.1 -Port 15432
```

---

## 🎉 Success Criteria

When everything is working:
- ✅ No PowerShell errors
- ✅ Backend shows: `INFO: Uvicorn running on http://0.0.0.0:8002`
- ✅ Frontend accessible at `http://localhost:3000`
- ✅ Browser console shows successful API calls
- ✅ No "ERR_CONNECTION_REFUSED" errors
- ✅ No database connection errors

---

## Summary

All three major issues have been identified and fixed:
1. ✅ Port configuration mismatch (8000 vs 8001)
2. ✅ Windows port access restrictions (solved with port 8002)
3. ✅ Database container not auto-starting (fixed in scripts)

**Your app should now start successfully!** 🚀

Just run: `.\start-local-hybrid-alt-port.ps1`
