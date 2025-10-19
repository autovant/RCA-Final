# Copilot Proxy Port Fix

## Issue
The Copilot API proxy was trying to use port 3000 (default), which conflicts with the frontend.

**Error:**
```
Error: listen EADDRINUSE: address already in use :::3000
```

## Root Cause
The `server.js` file uses:
```javascript
const port = process.env.PORT || 3000;
```

But the startup script wasn't setting the `PORT` environment variable.

## ✅ Fixed

Updated `start-local-hybrid-complete.ps1` to set `PORT=5001` before starting the Copilot proxy:

```powershell
cd copilot-to-api-main
$env:PORT = '5001'
npm start
```

## What to Do Now

### If Copilot Window is Still Open:
1. Press `Ctrl+C` in the Copilot window to stop it
2. Press `Up Arrow` to recall the command
3. Press `Enter` to restart

It will now use port 5001 correctly!

### Or Restart Everything:
```powershell
# Stop all services
.\stop-local-hybrid.ps1

# Start fresh
.\start-local-hybrid-complete.ps1
```

## Verification

After starting, the Copilot window should show:
```
🚀 Copilot API Server running on port 5001
📖 OpenAI-compatible endpoints:
   GET  http://localhost:5001/v1/models
   POST http://localhost:5001/v1/chat/completions
💡 Health check: http://localhost:5001/health
```

Test it:
```powershell
curl http://localhost:5001/health
```

Should return:
```json
{
  "status": "healthy",
  "timestamp": "2025-10-15T...",
  "service": "copilot-api-server"
}
```

## Port Allocation Summary

| Service | Port | Status |
|---------|------|--------|
| Frontend UI | 3000 | ✅ In use |
| Backend API | 8002 | ✅ In use |
| **Copilot Proxy** | **5001** | ✅ **Fixed!** |
| PostgreSQL | 15432 | ✅ In use |
| Redis | 16379 | ✅ In use |

No more conflicts! 🎉

## Alternative: Skip Copilot

If you don't need the Copilot proxy right now:
```powershell
.\start-local-hybrid-complete.ps1 -SkipCopilot
```

This will start everything except the Copilot proxy.
