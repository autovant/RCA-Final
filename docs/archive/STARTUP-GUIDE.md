# 🚀 RCA-Final - Complete Startup Guide

## ✅ Prerequisites

- ✅ Docker containers running in WSL (rca_db, rca_redis)
- ✅ Python venv in WSL (`venv-wsl`)
- ✅ Node.js installed in Windows
- ✅ Database migrations completed

---

## 🎯 Quick Start (3 Steps)

### **Step 1: Setup Port Forwarding (Run as Administrator)**

```powershell
# Right-click PowerShell and "Run as Administrator"
cd "C:\Users\syed.shareef\.vscode\repos\RCA - v7\RCA-Final"
.\setup-port-8001.ps1
```

This creates port forwarding: `localhost:8001` → `WSL:8001`

---

### **Step 2: Start Backend (WSL Terminal)**

Open a new terminal window and run:

```bash
wsl
cd "/mnt/c/Users/syed.shareef/.vscode/repos/RCA - v7/RCA-Final"
source venv-wsl/bin/activate
python -m uvicorn apps.api.main:app --host 0.0.0.0 --port 8001 --reload
```

Wait for: `INFO: Application startup complete.`

**OR** use the batch file:
```cmd
start-backend-simple.bat
```

---

### **Step 3: Start Frontend (Windows PowerShell)**

Open a new PowerShell window and run:

```powershell
cd "C:\Users\syed.shareef\.vscode\repos\RCA - v7\RCA-Final\ui"
npm run dev
```

Wait for: `ready - started server on 0.0.0.0:3000`

---

## 🌐 Access the Application

- **Frontend UI**: http://localhost:3000
- **Backend API**: http://localhost:8001
- **API Documentation**: http://localhost:8001/docs
- **API Redoc**: http://localhost:8001/redoc

---

## 🛑 Stopping the Application

1. Press `Ctrl+C` in the Backend terminal (WSL)
2. Press `Ctrl+C` in the Frontend terminal (Windows)

---

## 🔧 Troubleshooting

### Backend not accessible on localhost:8001?

**Cause**: Port forwarding not setup or WSL IP changed

**Fix**: Run `setup-port-8001.ps1` as Administrator

### Frontend shows CORS errors?

**Cause**: Backend CORS configuration

**Fix**: Already fixed! CORS allows all origins in development mode.

### Database connection errors?

**Check Docker containers**:
```bash
wsl docker ps
```

You should see: `rca_db` and `rca_redis`

**If not running**, start them from your other RCA app directory:
```bash
cd <other-rca-app-directory>
docker-compose up -d
```

### Port 8001 or 3000 already in use?

**Kill processes on those ports**:
```powershell
# Port 8001
Get-NetTCPConnection -LocalPort 8001 | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force }

# Port 3000
Get-NetTCPConnection -LocalPort 3000 | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force }

# In WSL (for backend)
wsl pkill -f "uvicorn.*apps.api.main"
```

---

## 📊 Database & Redis Isolation

This app uses:
- **Database**: `rca_engine_final` (isolated from other RCA app's `rca_db`)
- **Redis DB**: `1` (isolated from other RCA app's DB `0`)

Both apps can run simultaneously without conflicts! 🎉

---

## 🎨 One-Click Startup (Automated - Experimental)

For automated startup:

```powershell
.\Start-RCA.ps1
```

**Note**: This is experimental. The manual 3-step process above is more reliable.

---

## 📝 Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Windows (localhost)                  │
│                                                         │
│  ┌─────────────────┐         ┌────────────────────┐   │
│  │   Frontend      │         │  Port Forwarding   │   │
│  │   (Next.js)     │◄────────┤  localhost:8001    │   │
│  │   Port: 3000    │         │  → WSL:8001        │   │
│  └─────────────────┘         └────────────────────┘   │
└─────────────────────────────────────────────────────────┘
                                       │
                                       ↓
┌─────────────────────────────────────────────────────────┐
│                    WSL2 (Ubuntu)                        │
│                                                         │
│  ┌─────────────────┐      ┌────────────────────────┐  │
│  │   Backend       │◄─────┤   Docker Network       │  │
│  │   (FastAPI)     │      │   172.19.0.0/24        │  │
│  │   Port: 8001    │      │                        │  │
│  └─────────────────┘      │  ┌──────────────────┐ │  │
│                           │  │  PostgreSQL      │ │  │
│                           │  │  172.19.0.3:5432 │ │  │
│                           │  │  DB: rca_engine  │ │  │
│                           │  │      _final      │ │  │
│                           │  └──────────────────┘ │  │
│                           │                        │  │
│                           │  ┌──────────────────┐ │  │
│                           │  │  Redis           │ │  │
│                           │  │  172.19.0.2:6379 │ │  │
│                           │  │  DB: 1           │ │  │
│                           │  └──────────────────┘ │  │
│                           └────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
```

---

## ✨ Success Checklist

- [ ] Docker containers running (`rca_db`, `rca_redis`)
- [ ] Port forwarding setup (run `setup-port-8001.ps1` as admin)
- [ ] Backend running in WSL terminal
- [ ] Frontend running in Windows terminal
- [ ] http://localhost:3000 loads successfully
- [ ] http://localhost:8001/docs shows API documentation
- [ ] No CORS errors in browser console

---

## 🎉 You're All Set!

The application should now be fully operational. Enjoy using RCA-Final! 🚀

For issues or questions, check the troubleshooting section above.
