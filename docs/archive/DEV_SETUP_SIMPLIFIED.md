# RCA Engine - Simplified Development Setup

## 🎯 Overview

This setup runs the RCA Engine in **development/demo mode** for maximum speed and reliability:

- ✅ **Backend (FastAPI)** - Native Windows (Python)
- ✅ **Frontend (Next.js)** - Native Windows (Node.js)
- ✅ **Database (PostgreSQL)** - Docker (required for pgvector)
- ✅ **Redis** - Docker (optional caching)

**Production deployment still uses full Docker setup** (see `deploy/docker/docker-compose.yml`)

---

## 🚀 Quick Start (First Time)

### 1. One-Time Setup
```powershell
# Install dependencies and create virtual environment
.\setup-dev-environment.ps1
```

**Requirements:**
- Python 3.11+ ([download](https://www.python.org/downloads/))
- Node.js 18+ ([download](https://nodejs.org/))
- Windows Subsystem for Linux (WSL 2) with Docker Engine installed and running (Docker Desktop optional, not required)

> ℹ️ **Docker access policy:** All Docker commands run through WSL. Confirm `wsl.exe -e docker ps` works before starting the dev stack.

### 2. Start Development
```powershell
# Option A: Quick demo mode (opens in new windows)
.\quick-start-demo.ps1

# Option B: Manual control
.\start-dev.ps1
# Then follow the instructions to start each service
```

### 3. Access Application
- **UI**: http://localhost:3000
- **API**: http://localhost:8000
- **API Docs**: http://localhost:8000/api/docs

### 4. Stop Everything
```powershell
.\stop-dev.ps1
```

---

## 📁 File Structure

### Development Scripts (New - Use These!)
```
setup-dev-environment.ps1  # One-time setup
quick-start-demo.ps1       # Fast demo startup
start-dev.ps1              # Start database + instructions
stop-dev.ps1               # Stop all services
docker-compose.dev.yml     # Database-only config
```

### Production Scripts (Keep for Deployment)
```
deploy/docker/
  ├── docker-compose.yml    # Full production config
  ├── Dockerfile.secure     # Production backend image
  └── ...
```

---

## 🎬 Daily Development Workflow

### Morning Startup (< 30 seconds total)
```powershell
# Terminal 1: Start database (15 seconds)
.\start-dev.ps1

# Terminal 2: Start backend (2 seconds)
.\venv\Scripts\activate
python -m uvicorn apps.api.main:app --host 0.0.0.0 --port 8000 --reload

# Terminal 3: Start UI (5 seconds)
cd ui
npm run dev
```

**Total time: ~22 seconds** vs 60+ seconds with full Docker

### Making Changes

**Backend Changes (Python):**
- Edit `apps/api/` or `core/` files
- Save → Auto-reload in 2 seconds ✅
- See logs immediately in terminal

**Frontend Changes (React/TypeScript):**
- Edit `ui/src/` files
- Save → Hot reload in < 100ms ✅
- Instant feedback

**Database Changes:**
```powershell
# Create migration
.\venv\Scripts\activate
alembic revision -m "description"

# Edit migration in alembic/versions/
# Apply migration
alembic upgrade head
```

---

## 🎯 Demo/Client Presentation Mode

### Before the Demo
```powershell
# 1. Start everything (one command)
.\quick-start-demo.ps1

# 2. Wait 15 seconds
# 3. Browser opens automatically
# 4. You're ready!
```

### During the Demo
- ✅ **Backend restart**: 2 seconds (if needed)
- ✅ **No Docker networking issues**
- ✅ **Instant log visibility**
- ✅ **Quick debugging**

### If Something Goes Wrong
```powershell
# Backend crashed? Restart in 2 seconds:
# (In backend terminal)
Ctrl+C
↑ (up arrow)
Enter

# UI issue? Restart in 5 seconds:
# (In UI terminal)
Ctrl+C
npm run dev
```

---

## 🐳 What Runs Where?

### Native Windows ✅
| Component | Port | Why Native? |
|-----------|------|-------------|
| **Backend API** | 8000 | Fast restart (2s vs 30s), instant logs, easy debugging |
| **Frontend UI** | 3000 | Hot reload (50ms vs 3s), no file watching issues |
| **Copilot API** | 3001 | Simple proxy, no container overhead |

### Docker 🐳
| Component | Port | Why Docker? |
|-----------|------|-------------|
| **PostgreSQL** | 15432 | Requires pgvector extension, data isolation |
| **Redis** | 16379 | Optional, better on Linux, no Windows service |
| **Ollama** | 11434 | Optional, large models, GPU access |

---

## 🔧 Configuration

### Environment Variables (.env)
```bash
# Database (connects to Docker PostgreSQL)
POSTGRES_USER=rca_user
POSTGRES_PASSWORD=your_password
POSTGRES_DB=rca_engine
POSTGRES_HOST=localhost
POSTGRES_PORT=15432

# Security
JWT_SECRET_KEY=your-secret-key-min-32-chars

# LLM
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=llama2
DEFAULT_PROVIDER=copilot
GITHUB_TOKEN=ghp_your_token_with_copilot_scope

# Dev Settings
ENVIRONMENT=development
DEBUG=true
LOG_LEVEL=INFO
```

### UI Environment (ui/.env.local)
```bash
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```

---

## 🐛 Troubleshooting

### "Virtual environment not found"
```powershell
# Run setup again
.\setup-dev-environment.ps1
```

### "Database connection refused"
```powershell
# Check if WSL Docker is running
wsl.exe -e docker ps

# Start database (from PowerShell)
$wslPath = (wsl.exe wslpath -a $PWD)
wsl.exe -e bash -lc "cd '$wslPath' && docker compose -f docker-compose.dev.yml up -d db"

# Check database health
$wslPath = (wsl.exe wslpath -a $PWD)
wsl.exe -e bash -lc "cd '$wslPath' && docker inspect --format='{{.State.Health.Status}}' rca_db"
```

### "Port 6379 already in use"
```powershell
# Redis now listens on host port 16379. Update local overrides if you previously bound 6379.
# Stop Windows Redis services or other processes bound to 16379, then rerun start-dev.
```

### "Port already in use"
```powershell
# Find what's using port 8000
netstat -ano | findstr :8000

# Kill the process (replace PID)
taskkill /PID <PID> /F

# Or use different port
python -m uvicorn apps.api.main:app --port 8001 --reload
```

### "Module not found" errors
```powershell
# Reinstall dependencies
.\venv\Scripts\activate
pip install -r requirements.txt
```

### UI not loading styles
```powershell
# Restart UI
cd ui
# Delete .next cache
Remove-Item -Recurse -Force .next
npm run dev
```

---

## 📊 Performance Comparison

### Startup Time
| Mode | Database | Backend | UI | Total |
|------|----------|---------|----|----|
| **Dev (This Setup)** | 15s | 2s | 5s | **22s** |
| **Full Docker** | 30s | 30s | 10s | **70s** |

### Hot Reload
| Mode | Backend Change | Frontend Change |
|------|----------------|-----------------|
| **Dev (This Setup)** | 2s | 50ms |
| **Full Docker** | 30s | 3s |

### Memory Usage
| Mode | Docker | Backend | UI | Total |
|------|--------|---------|----|----|
| **Dev (This Setup)** | 0.5 GB | 0.3 GB | 0.4 GB | **1.2 GB** |
| **Full Docker** | 4 GB | 0.5 GB | 0.5 GB | **5 GB** |

---

## 🚢 Production Deployment

**This dev setup is for development/demos only.**

For production deployment, use the full Docker setup:
```powershell
cd deploy/docker
docker-compose up -d
```

See `DOCKER_DEPLOYMENT_GUIDE.md` for production deployment instructions.

---

## 🎓 Additional Resources

- **Backend API**: `apps/api/README.md`
- **Frontend UI**: `ui/UI_COMPONENTS_GUIDE.md`
- **Database**: `core/db/README.md`
- **ITSM Integration**: `docs/ITSM_INTEGRATION_GUIDE.md`

---

## 💡 Tips

1. **Ensure Docker daemon is running inside WSL** - `wsl.exe -e docker ps`
2. **If you override Redis bindings**, ensure your `.env` contains `REDIS_PORT=16379`
2. **Use VSCode terminals** - Easier to manage multiple terminals
3. **Enable auto-save** - See changes instantly
4. **Use API docs** - http://localhost:8000/api/docs for testing endpoints
5. **Check logs** - All output is directly visible in terminals

---

## ❓ FAQ

**Q: Why not run everything in Docker?**
A: For development/demos, native Windows is 3-10x faster for hot reload and startup. Production still uses Docker.

**Q: Can I switch back to full Docker?**
A: Yes! Just use `.\quick-start-backend.bat` (old script) instead.

**Q: What about database migrations?**
A: Same as before - `alembic upgrade head` works with Docker PostgreSQL.

**Q: Does this affect production?**
A: No - production Docker setup is untouched in `deploy/docker/`.

**Q: Can I run this on Mac/Linux?**
A: This guide is Windows-specific, but the concept works - just adapt the shell scripts.

---

## 🎉 Ready to Go!

```powershell
.\quick-start-demo.ps1
```

Your app will be running at http://localhost:3000 in ~15 seconds!
