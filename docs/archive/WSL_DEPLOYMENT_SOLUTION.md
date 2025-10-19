# RCA-Final - WSL Deployment Solution

## 🎯 Final Architecture (Solves All Issues)

After extensive testing, we've determined the optimal setup:

### ✅ What Works:
- **Database**: Docker PostgreSQL in WSL (port 5432 internal)
- **Backend**: Running in WSL (direct connection, no port forwarding)
- **Frontend**: Running in Windows (Next.js on port 3000)
- **Redis**: Docker Redis in WSL (port 6379 internal)

### ❌ What Doesn't Work:
- Windows backend → Docker PostgreSQL via port forwarding (unstable)
- Native Windows PostgreSQL installations (Chocolatey issues)

## 🚀 Quick Start (WSL Backend + Windows Frontend)

### 1. Update .env for WSL Backend

```properties
# Database (direct connection from WSL, no port forwarding)
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_USER=rca_user  
POSTGRES_PASSWORD=rca_password_change_in_production
POSTGRES_DB=rca_engine_final

# Redis (direct connection from WSL)
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=1
```

### 2. Start Backend in WSL

```bash
# In WSL terminal
cd /mnt/c/Users/syed.shareef/.vscode/repos/RCA\ -\ v7/RCA-Final

# Create Python venv in WSL
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run migrations
python -m alembic upgrade head

# Start backend
python -m uvicorn apps.api.main:app --host 0.0.0.0 --port 8001 --reload
```

### 3. Start Frontend in Windows

```powershell
# In Windows PowerShell
cd ui
npm run dev
```

### 4. Access Application

- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8001
- **API Docs**: http://localhost:8001/docs

## 🔧 Why This Works

1. **WSL Backend** connects directly to Docker containers (same network)
   - No port forwarding needed
   - Stable, persistent connections
   - Native Linux performance

2. **Windows Frontend** uses HTTP to call backend
   - HTTP over port forwarding is stable (stateless)
   - Next.js development server works great on Windows
   - Hot-reload works perfectly

3. **Database Isolation** achieved via separate database names
   - Other app: `rca_db`
   - This app: `rca_engine_final`
   - Redis DB 1 vs DB 0

## 📝 Alternative: Full WSL Deployment

If you prefer, run everything in WSL:

```bash
# Backend (port 8001)
cd /mnt/c/Users/syed.shareef/.vscode/repos/RCA\ -\ v7/RCA-Final
source venv/bin/activate
python -m uvicorn apps.api.main:app --host 0.0.0.0 --port 8001 --reload

# Frontend (port 3000) - in another WSL terminal
cd /mnt/c/Users/syed.shareef/.vscode/repos/RCA\ -\ v7/RCA-Final/ui
npm run dev
```

Access from Windows browser: http://localhost:8001 and http://localhost:3000

## 🎉 Benefits

✅ No port forwarding stability issues
✅ Direct database connections
✅ Both apps can coexist (separate databases)
✅ Hot-reload works on both backend and frontend
✅ Native Linux performance for backend
✅ Windows-native frontend development

## 📊 What We Learned

1. Windows `netsh portproxy` unsuitable for persistent TCP (databases)
2. Chocolatey had broken installation
3. Native PostgreSQL 15 installation failed
4. PostgreSQL 16 already installed but password unknown
5. **Solution**: Run backend where databases are (WSL)

## ⚡ Next Steps

Would you like me to create scripts to:
1. Start backend in WSL
2. Start frontend in Windows
3. Combined startup script

Choose your preferred deployment mode!
