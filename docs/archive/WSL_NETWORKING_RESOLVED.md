# ✅ WSL2 Networking Issue - RESOLVED

## Status: **WORKING**

**Date:** October 15, 2025  
**Issue:** PostgreSQL container running in WSL2 Docker not accessible from Windows at `localhost:15432`  
**Resolution:** Port forwarding configured via `netsh` - containers now accessible from Windows

---

## What Was Wrong

1. **Mirrored networking incompatible with Docker**: The `.wslconfig` file had `networkingMode=mirrored` enabled, which doesn't work properly with Docker's bridge networking mode
2. **Docker uses internal bridge networks**: Containers get IPs like `172.19.0.3` which aren't directly routable from Windows
3. **Port forwarding wasn't set up**: WSL2's NAT mode requires explicit port forwarding rules

## Solution Applied

### ✅ Step 1: Fixed WSL Networking Mode
- Disabled mirrored networking in `.wslconfig`
- Restarted WSL to use default NAT mode
- **File modified:** `C:\Users\syed.shareef\.wslconfig`

### ✅ Step 2: Configured Port Forwarding
- Created script: **`fix-docker-port-forwarding.ps1`**
- Runs as Administrator
- Sets up `netsh` port forwarding rules:
  ```
  Listen on ipv4:             Connect to ipv4:
  Address         Port        Address         Port
  0.0.0.0         15432       172.28.36.28    15432
  0.0.0.0         16379       172.28.36.28    16379
  0.0.0.0         8001        172.28.36.28    8001
  0.0.0.0         3000        172.28.36.28    3000
  ```

### ✅ Step 3: Configured Windows Firewall
- Created firewall rules to allow WSL connections
- Ports: 15432 (PostgreSQL), 16379 (Redis), 8001 (API), 3000 (UI)

### ✅ Step 4: Fixed Environment Variables
- Created minimal `.env` file with only required fields
- Removed extra fields that caused Pydantic validation errors
- **File created:** `.env`

## Verification

### Connection Test ✅
```powershell
PS> Test-NetConnection -ComputerName localhost -Port 15432

ComputerName     : localhost
TcpTestSucceeded : True  ✓
```

### Socket Test ✅
```powershell
PS> python -c "import socket; s = socket.socket(); result = s.connect_ex(('localhost', 15432)); print(f'Result: {result}'); s.close()"
Result: 0  ✓  (0 = success)
```

### Containers Running ✅
```
CONTAINER ID   IMAGE                    STATUS
95d9357c3cae   pgvector/pgvector:pg15   Up (healthy)  ✓
85c9160b60cb   redis:7-alpine           Up (healthy)  ✓
```

---

## How to Use

### Option 1: Quick Start (Recommended)
```powershell
.\quick-start.ps1
```
This script:
- Starts Docker containers
- Tests connection
- Offers to auto-start backend and frontend

### Option 2: Full Automated Start
```powershell
.\start-environment.ps1
```
May show timeout warnings, but containers will start successfully.

### Option 3: Manual Start
```powershell
# Start containers
wsl bash -c "cd '/mnt/c/Users/syed.shareef/.vscode/repos/RCA - v7/RCA-Final' && docker compose -f docker-compose.dev.yml up -d"

# Start backend (new terminal)
python -m uvicorn apps.api.main:app --host 0.0.0.0 --port 8001 --reload

# Start frontend (new terminal)
cd ui
npm run dev
```

---

## Important Notes

### When WSL Restarts
The WSL IP address changes when you:
- Run `wsl --shutdown`
- Reboot Windows
- WSL crashes/restarts

**Solution:** Rerun the port forwarding fix:
```powershell
.\fix-docker-port-forwarding.ps1
```
(Run as Administrator)

### Check Port Forwarding Status
```powershell
# View current rules
netsh interface portproxy show v4tov4

# Check WSL IP
wsl hostname -I

# Test connection
Test-NetConnection localhost -Port 15432
```

---

## Files Created/Modified

### New Scripts
- ✅ **`fix-docker-port-forwarding.ps1`** - Main fix (run as Admin when WSL IP changes)
- ✅ **`quick-start.ps1`** - Simple startup script
- ✅ **`fix-wsl-networking.ps1`** - Diagnostic and repair
- ✅ **`fix-firewall-wsl-mirrored.ps1`** - Firewall configuration
- ✅ **`start-databases-wsl-ip.ps1`** - Alternative startup using direct WSL IP

### Configuration Files
- ✅ **`.env`** - Minimal environment configuration (JWT_SECRET_KEY, POSTGRES_*, REDIS_*)
- ✅ **`.wslconfig`** - WSL configuration (mirrored networking disabled)

### Documentation
- ✅ **`WSL_NETWORKING_SOLUTION.md`** - Complete technical documentation
- ✅ **`WSL_NETWORKING_RESOLVED.md`** - This file - quick reference

---

## Troubleshooting

### Problem: "Port 15432 not reachable"
**Solution:**
```powershell
# 1. Check WSL IP hasn't changed
wsl hostname -I

# 2. View current port forwarding
netsh interface portproxy show v4tov4

# 3. If IP doesn't match, rerun fix
.\fix-docker-port-forwarding.ps1
```

### Problem: "Container won't start"
```powershell
# Check logs
wsl docker logs rca_db

# Restart container
wsl docker restart rca_db
```

### Problem: "Alembic migration errors"
- ✅ **FIXED** - `.env` file now has correct minimal configuration
- Database connection is working
- If you see Pydantic validation errors, check `.env` has only these fields:
  - `JWT_SECRET_KEY`
  - `POSTGRES_HOST`, `POSTGRES_PORT`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`
  - `REDIS_HOST`, `REDIS_PORT`
  - `LOG_LEVEL`

---

## Success Criteria - All Met ✅

- [x] WSL2 configured for Docker compatibility (NAT mode)
- [x] Port forwarding rules created
- [x] Windows Firewall configured
- [x] PostgreSQL accessible at `localhost:15432`
- [x] Redis accessible at `localhost:16379`
- [x] Environment variables configured correctly
- [x] Containers start successfully
- [x] Connection tests pass
- [x] Quick-start scripts created

---

## Next Steps

1. **Start the application:**
   ```powershell
   .\quick-start.ps1
   ```

2. **Access the UI:**
   Open browser to `http://localhost:3000`

3. **Access the API:**
   Open browser to `http://localhost:8001/docs`

4. **Remember:** If WSL restarts, rerun `fix-docker-port-forwarding.ps1` as Administrator

---

**Resolution Owner:** GitHub Copilot  
**Verification Status:** ✅ Tested and Working  
**Last Verified:** October 15, 2025
