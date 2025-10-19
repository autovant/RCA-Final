# Complete Hybrid Startup Guide

## Overview

The new `start-local-hybrid-complete.ps1` script launches **all RCA Engine components** in separate terminal windows for easy monitoring and debugging.

## Components Started

| Component | Port | Window Title | Hot Reload |
|-----------|------|--------------|------------|
| 🚀 Backend API | 8002 | RCA Backend API | ✅ Yes |
| 🎨 Frontend UI | 3000 | RCA Frontend UI | ✅ Yes |
| 👁️ File Watcher | - | File Watcher Service | N/A |
| 🤖 Copilot Proxy | 5001 | GitHub Copilot API Proxy | N/A |
| 🗄️ PostgreSQL | 15432 | (Docker Container) | N/A |
| 🗄️ Redis | 16379 | (Docker Container) | N/A |

## Quick Start

### Start Everything
```powershell
.\start-local-hybrid-complete.ps1
```

### Start Without Optional Components
```powershell
# Skip Copilot proxy
.\start-local-hybrid-complete.ps1 -SkipCopilot

# Skip file watcher
.\start-local-hybrid-complete.ps1 -SkipWatcher

# Skip both
.\start-local-hybrid-complete.ps1 -SkipCopilot -SkipWatcher
```

### Stop Everything
```powershell
.\stop-local-hybrid.ps1
```

## What Each Component Does

### 🚀 Backend API (Port 8002)
- Main FastAPI application
- REST API endpoints
- Database operations
- LLM integrations
- **Access**: http://localhost:8002/docs

### 🎨 Frontend UI (Port 3000)
- Next.js web application
- User interface
- Real-time updates
- **Access**: http://localhost:3000

### 👁️ File Watcher Service
- Monitors directories for new log files
- Automatically creates RCA jobs
- Sends notifications
- **Configured via**: Database settings

### 🤖 Copilot API Proxy (Port 5001)
- OpenAI-compatible API for GitHub Copilot
- Enables using Copilot for LLM operations
- **Access**: http://localhost:5001
- **Optional**: Only needed if using Copilot provider

### 🗄️ Databases
- **PostgreSQL**: Main database (rca_engine_final)
- **Redis**: Caching and pub/sub
- **Running in**: Docker containers via WSL

## Terminal Windows

Each component runs in its own PowerShell window:

### Backend Window
```
═══════════════════════════════════════════════════════
 🚀 RCA Backend API - Port 8002
═══════════════════════════════════════════════════════

📍 API Docs:  http://localhost:8002/docs
❤️  Health:    http://localhost:8002/health
🔄 Hot-reload: Enabled

INFO:     Uvicorn running on http://0.0.0.0:8002
```

### Frontend Window
```
═══════════════════════════════════════════════════════
 🎨 RCA Frontend UI - Port 3000
═══════════════════════════════════════════════════════

🌐 Application: http://localhost:3000
🔧 Backend API: http://localhost:8002
🔄 Hot-reload:  Enabled

▲ Next.js 14.x.x
- Local:        http://localhost:3000
```

### File Watcher Window
```
═══════════════════════════════════════════════════════
 👁️  File Watcher Service
═══════════════════════════════════════════════════════

📂 Monitoring directories for new log files
🔄 Auto-creates RCA jobs when files detected

INFO - Watcher initialized
INFO - Monitoring: /path/to/logs
```

### Copilot Proxy Window
```
═══════════════════════════════════════════════════════
 🤖 GitHub Copilot API Proxy
═══════════════════════════════════════════════════════

🔌 Proxy URL: http://localhost:5001
🎯 OpenAI-compatible API for GitHub Copilot

Server listening on port 5001
```

## Development Workflow

### Making Changes

1. **Backend Changes** (Python):
   - Edit files in `apps/`, `core/`, etc.
   - Changes auto-reload (watch the backend window)
   - No restart needed!

2. **Frontend Changes** (TypeScript/React):
   - Edit files in `ui/src/`
   - Changes auto-reload (watch the frontend window)
   - Browser auto-refreshes!

3. **Configuration Changes** (`.env`):
   - Edit `.env` or `.env.local`
   - Restart affected services (Ctrl+C, then Up Arrow + Enter)

### Debugging

Each window shows real-time logs:
- ✅ Green = Success
- ⚠️ Yellow = Warning
- ❌ Red = Error

### Stopping Services

**Stop all at once:**
```powershell
.\stop-local-hybrid.ps1
```

**Stop individually:**
- Just close the terminal window for that service
- Or press `Ctrl+C` in the window

## Process IDs

Process IDs are saved to `.local-pids.json`:
```json
{
  "Backend": 12345,
  "Frontend": 12346,
  "Watcher": 12347,
  "Copilot": 12348
}
```

Used by `stop-local-hybrid.ps1` to gracefully stop services.

## Troubleshooting

### Backend Won't Start
```powershell
# Check database
wsl docker ps

# Check connectivity
Test-NetConnection 127.0.0.1 -Port 15432

# Restart database
wsl docker restart rca_db
```

### Frontend Won't Start
```powershell
# Check if port 3000 is in use
netstat -ano | findstr :3000

# Reinstall dependencies if needed
cd ui
rm -r node_modules
npm install
```

### File Watcher Not Working
- Check `scripts/file_watcher.py` exists
- Verify backend is running (watcher needs API)
- Check watcher configuration in database

### Copilot Proxy Issues
```powershell
# Install dependencies
cd copilot-to-api-main
npm install

# Check config.json exists
cat config.json
```

### Port Conflicts
If you see `EADDRINUSE` or `WinError 10013`:
```powershell
# Find what's using the port
netstat -ano | findstr :8002
netstat -ano | findstr :3000

# Kill the process (replace PID)
taskkill /F /PID <PID>
```

## Advantages of This Setup

✅ **Easy Monitoring**: Each component in its own window  
✅ **Hot Reload**: Changes apply instantly  
✅ **Independent**: Stop/restart services individually  
✅ **Full Logs**: See everything in real-time  
✅ **Native Performance**: No Docker overhead for app code  
✅ **Easy Debugging**: Clear error messages per service  

## Comparison with Other Scripts

| Script | Backend | Frontend | Watcher | Copilot | Databases |
|--------|---------|----------|---------|---------|-----------|
| `start-local-hybrid.ps1` | ✅ | ✅ | ❌ | ❌ | ✅ |
| `start-local-hybrid-alt-port.ps1` | ✅ (8002) | ✅ | ❌ | ❌ | ✅ |
| **`start-local-hybrid-complete.ps1`** | **✅** | **✅** | **✅** | **✅** | **✅** |

## Configuration Files

### `.env` / `.env.local`
Backend environment variables:
```bash
POSTGRES_HOST=localhost
POSTGRES_PORT=15432
POSTGRES_USER=rca_user
POSTGRES_PASSWORD=rca_password_change_in_production
POSTGRES_DB=rca_engine_final

REDIS_HOST=localhost
REDIS_PORT=16379
```

### `ui/.env.local`
Frontend environment variables:
```bash
NEXT_PUBLIC_API_BASE_URL=http://localhost:8002
```

### `copilot-to-api-main/config.json`
Copilot proxy configuration:
```json
{
  "port": 5001,
  "copilot_token": "your-token-here"
}
```

## System Requirements

- ✅ Windows 10/11 with WSL2
- ✅ PowerShell 7.0+
- ✅ Docker Desktop or WSL Docker
- ✅ Python 3.11+ (with venv)
- ✅ Node.js 18+ (with npm)

## Next Steps

After starting:
1. Wait 10-15 seconds for all services to initialize
2. Open browser to http://localhost:3000
3. Check backend health: http://localhost:8002/health
4. Review API docs: http://localhost:8002/docs

**Happy developing!** 🚀
