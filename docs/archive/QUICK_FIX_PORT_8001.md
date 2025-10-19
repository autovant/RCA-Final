# Quick Fix Guide - Port 8000 → 8001 Issue

## Problem
Frontend shows: `GET http://localhost:8000/api/jobs net::ERR_CONNECTION_REFUSED`

## Root Cause
Frontend configuration files were using port **8000**, but backend runs on port **8001**.

## ✅ Quick Fix (Recommended)

Just re-run the startup script - it now automatically fixes the configuration:

```powershell
.\start-local-hybrid.ps1
```

The script will:
1. Detect incorrect port configuration
2. Automatically update `ui\.env.local` to use port 8001
3. Start both backend and frontend correctly

## 🔍 Verify the Fix

Run the verification script:

```powershell
.\verify-port-config.ps1
```

This will check:
- ✓ UI environment file uses correct port
- ✓ Source files use correct port
- ✓ Services are running on correct ports

## 🔧 Manual Fix (If Needed)

If the automatic fix doesn't work:

### 1. Stop all running services
Close any PowerShell windows running the backend or frontend.

### 2. Update UI configuration
```powershell
echo "NEXT_PUBLIC_API_BASE_URL=http://localhost:8001" | Out-File -FilePath ui\.env.local -Encoding UTF8 -NoNewline
```

### 3. Clear Next.js cache (if needed)
```powershell
Remove-Item -Recurse -Force ui\.next
```

### 4. Start services
```powershell
.\start-local-hybrid.ps1
```

## 🧪 Test the Fix

1. **Backend health check**:
   ```powershell
   curl http://localhost:8001/health
   ```
   Should return: `{"status":"healthy",...}`

2. **Frontend access**:
   - Open browser: http://localhost:3000
   - Press F12 for DevTools
   - Check Console - should see requests to `localhost:8001`
   - No more "ERR_CONNECTION_REFUSED" errors!

3. **Jobs API**:
   ```powershell
   curl http://localhost:8001/api/jobs
   ```
   Should return jobs data (or empty array `[]`)

## 📝 What Was Changed

All changes have been applied to:
- ✅ `ui\.env.local` 
- ✅ `ui\src\data\jobsPreview.ts`
- ✅ `.env.example`
- ✅ `deploy\docker\.env`
- ✅ `start-local-hybrid.ps1` (added auto-fix)

## ❓ Still Having Issues?

### Issue: "Port already in use"
```powershell
# Find what's using port 8001
netstat -ano | findstr :8001

# Kill the process (replace PID with actual process ID)
taskkill /F /PID <PID>
```

### Issue: "Frontend still shows 8000"
1. Hard refresh the browser: `Ctrl+Shift+R`
2. Clear browser cache
3. Restart the frontend:
   ```powershell
   cd ui
   npm run dev
   ```

### Issue: "Backend not responding"
1. Check if databases are running:
   ```powershell
   wsl docker ps
   ```
2. Check if port forwarding works:
   ```powershell
   Test-NetConnection -ComputerName 127.0.0.1 -Port 15432
   ```

## 📚 Related Documentation

- Full details: `PORT_8001_FIX_SUMMARY.md`
- Startup guide: Comments in `start-local-hybrid.ps1`

## ✨ Changes Summary

| File | Old Value | New Value |
|------|-----------|-----------|
| `ui\.env.local` | `localhost:8000` | `localhost:8001` |
| `ui\src\data\jobsPreview.ts` | `localhost:8000` | `localhost:8001` |
| `.env.example` | `localhost:8000` | `localhost:8001` |

**Result**: Frontend now correctly connects to backend API! 🎉
