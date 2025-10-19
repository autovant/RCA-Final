# 🎯 RCA-Final Deployment - Complete Status & Next Steps

## ✅ What We've Accomplished

### 1. **Database Isolation** 
- ✅ Created separate database: `rca_engine_final`
- ✅ Configured Redis DB 1 (vs DB 0 for other app)
- ✅ Both apps can coexist without conflicts

### 2. **WSL Python Environment**
- ✅ Created Python 3.12 virtual environment in WSL
- ✅ Installed all dependencies (60+ packages)
- ✅ Dependencies compatible and working

### 3. **Database Migrations**
- ✅ Successfully ran Alembic migrations
- ✅ Schema created in `rca_engine_final` database
- ✅ Tables: users, jobs, tickets, files, embeddings, etc.

### 4. **Configuration**
- ✅ `.env` configured for Docker network
- ✅ PostgreSQL: 172.19.0.3:5432
- ✅ Redis: 172.19.0.2:6379
- ✅ Credentials: rca_user / rca_password

### 5. **Scripts Created**
- ✅ `start-backend-wsl.sh` - Backend startup script
- ✅ `start-app.ps1` - Combined startup (Windows launcher)
- ✅ Documentation files

## 📊 Current Configuration

```properties
# .env Configuration
POSTGRES_HOST=172.19.0.3  # Docker container IP
POSTGRES_PORT=5432
POSTGRES_USER=rca_user
POSTGRES_PASSWORD=rca_password
POSTGRES_DB=rca_engine_final  # ISOLATED

REDIS_HOST=172.19.0.2  # Docker container IP
REDIS_PORT=6379
REDIS_DB=1  # ISOLATED
```

## 🚀 How to Start the Application

### Method 1: Manual (Two Terminals)

**Terminal 1 - Backend (WSL):**
```bash
wsl bash
cd "/mnt/c/Users/syed.shareef/.vscode/repos/RCA - v7/RCA-Final"
source venv-wsl/bin/activate
python -m uvicorn apps.api.main:app --host 0.0.0.0 --port 8001 --reload
```

**Terminal 2 - Frontend (Windows PowerShell):**
```powershell
cd "C:\Users\syed.shareef\.vscode\repos\RCA - v7\RCA-Final\ui"
npm run dev
```

### Method 2: Automated

```powershell
.\start-app.ps1
```

This will:
1. Start backend in WSL (new window)
2. Start frontend in Windows (new window)
3. Display access URLs

## 🔗 Access URLs

Once running:
- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8001
- **API Documentation**: http://localhost:8001/docs
- **API Redoc**: http://localhost:8001/redoc

## ⚠️ Known Issues & Solutions

### Issue 1: Backend Not Starting in Background
**Symptom**: Backend starts but doesn't stay running
**Solution**: Start in interactive WSL terminal:
```bash
wsl
cd "/mnt/c/Users/syed.shareef/.vscode/repos/RCA - v7/RCA-Final"
source venv-wsl/bin/activate
python -m uvicorn apps.api.main:app --host 0.0.0.0 --port 8001 --reload
```

### Issue 2: "Connection Refused" Errors
**Cause**: Docker containers not running or wrong IPs
**Solution**: 
```powershell
# Check containers are running
wsl docker ps | Select-String "rca"

# If not running, start from other RCA app directory
# Get fresh container IPs:
wsl docker inspect rca_db --format='{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}'
wsl docker inspect rca_redis --format='{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}'
```

### Issue 3: Port 8001 or 3000 Already in Use
**Cause**: Other RCA app is running
**Solution**: Stop the other app first, or change ports

## 🔧 Troubleshooting Commands

**Check Docker Containers:**
```powershell
wsl docker ps
```

**Check Backend Logs:**
```bash
# In WSL terminal where backend is running
# Logs will show in real-time
```

**Test Database Connection:**
```powershell
wsl docker exec -i rca_db psql -U rca_user -d rca_engine_final -c "SELECT COUNT(*) FROM alembic_version;"
```

**Test Redis Connection:**
```powershell
wsl docker exec -i rca_redis redis-cli PING
```

## 📝 What Makes This Setup Work

1. **Backend in WSL** = Direct access to Docker containers (no port forwarding)
2. **Frontend in Windows** = Native development experience with hot-reload
3. **Separate Database** = No conflicts with other RCA app
4. **Docker Network IPs** = Stable, reliable connections

## 🎉 Success Criteria

You'll know it's working when:
- ✅ Backend shows: "Uvicorn running on http://0.0.0.0:8001"
- ✅ Frontend shows: "ready - started server on 0.0.0.0:3000"
- ✅ http://localhost:3000 loads the UI
- ✅ http://localhost:8001/docs shows API documentation
- ✅ No connection errors in console

## 📚 Architecture Summary

```
┌─────────────────────────────────────┐
│  Windows (Your Machine)             │
│                                     │
│  ┌──────────────────┐               │
│  │  Frontend (3000)  │◄──────┐     │
│  │  Next.js          │       │     │
│  └──────────────────┘       │     │
│                              │     │
│  ┌──────────────────────────┴────┐│
│  │       WSL 2 (Ubuntu)          ││
│  │                                ││
│  │  ┌─────────────────────────┐  ││
│  │  │ Backend (8001)          │  ││
│  │  │ FastAPI + uvicorn       │  ││
│  │  └──────────┬──────────────┘  ││
│  │             │                  ││
│  │  ┌──────────▼──────┐  ┌──────▼┐││
│  │  │ PostgreSQL      │  │ Redis │││
│  │  │ rca_engine_final│  │ DB 1  │││
│  │  │ 172.19.0.3:5432 │  │ :6379 │││
│  │  └─────────────────┘  └───────┘││
│  └────────────────────────────────┘│
└─────────────────────────────────────┘
```

## 🚀 Immediate Next Step

**Open a WSL terminal and run:**
```bash
cd "/mnt/c/Users/syed.shareef/.vscode/repos/RCA - v7/RCA-Final"
source venv-wsl/bin/activate
python -m uvicorn apps.api.main:app --host 0.0.0.0 --port 8001 --reload
```

**Then in a new PowerShell window:**
```powershell
cd "C:\Users\syed.shareef\.vscode\repos\RCA - v7\RCA-Final\ui"
npm run dev
```

**That's it! Access http://localhost:3000** 🎉

---

## 📖 Additional Documentation

- `WSL_DEPLOYMENT_SOLUTION.md` - Detailed deployment guide
- `ISOLATION_SUMMARY.md` - Database/Redis isolation details
- `DB_CONNECTION_ISSUE.md` - Why we moved to WSL
- `CHOCOLATEY_PATH_FIX.md` - Native Windows attempts

**You're ready to go! The hard part is done.** 🚀
