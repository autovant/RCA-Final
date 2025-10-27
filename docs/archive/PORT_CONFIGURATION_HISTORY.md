# Port Configuration Issues & Resolutions

This document consolidates all port-related configuration fixes and troubleshooting from the development cycle.

> **Current Configuration**: Backend runs on port **8000** (or 8001 in legacy docs). See [Developer Setup Guide](../getting-started/dev-setup.md) for current configuration.

---

## Issue Timeline

### October 15, 2025 - Port Mismatch Between Frontend and Backend

**Problem**: Frontend configured for port 8000, backend running on port 8001  
**Error**: `GET http://localhost:8000/api/jobs net::ERR_CONNECTION_REFUSED`

#### Root Cause
Configuration files inconsistent across frontend and backend:
- Backend: Running on port 8001
- Frontend: Configured to call port 8000

#### Resolution

**Changed Files**:

1. **`ui/.env.local`**
   - Changed: `NEXT_PUBLIC_API_BASE_URL=http://localhost:8000`
   - To: `NEXT_PUBLIC_API_BASE_URL=http://localhost:8001`

2. **`ui/src/data/jobsPreview.ts`**
   - Changed: Default fallback `"http://localhost:8000"`
   - To: `"http://localhost:8001"`
   - Line: `export const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8001";`

3. **`.env.example`**
   - Changed: `NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1`
   - To: `NEXT_PUBLIC_API_URL=http://localhost:8001/api/v1`

4. **`deploy/docker/.env`**
   - Changed: 
     - `NEXT_PUBLIC_API_URL=http://localhost:8000`
     - `NEXT_PUBLIC_WS_URL=ws://localhost:8000`
   - To: 
     - `NEXT_PUBLIC_API_URL=http://localhost:8001`
     - `NEXT_PUBLIC_WS_URL=ws://localhost:8001`

**Automated Fix**:
Created `start-local-hybrid.ps1` script that:
1. Detects incorrect port configuration
2. Automatically updates `ui/.env.local` to use port 8001
3. Starts both backend and frontend correctly

**Verification**:
Created `verify-port-config.ps1` script to check all port configurations.

---

### WinError 10013 - Port Access Forbidden

**Problem**: `[WinError 10013] An attempt was made to access a socket in a way forbidden by its access permissions`

**Error Context**: Port 8001 held by Windows system service (svchost)

#### Root Cause
Port 8001 conflicts with Windows system services:
- **Hyper-V** dynamic port allocation
- **WinNAT** (Windows NAT for WSL/Docker)
- **Windows Reserved Ports**

#### Solutions Provided

**Option 1: Use Alternative Port (Fastest - Recommended)**
- Created `start-local-hybrid-alt-port.ps1`
- Uses port **8002** instead of 8001
- Automatically updates all configuration
- Starts app immediately

**Access URLs with Alt Port**:
- Frontend: http://localhost:3000
- Backend: http://localhost:8002

**Option 2: Release Port 8001**
```powershell
# Find process using port 8001
netstat -ano | findstr :8001

# Kill the process (replace PID)
taskkill /PID <PID> /F
```

**Option 3: Exclude Port from Dynamic Range**
```powershell
# As Administrator
netsh int ipv4 add excludedportrange protocol=tcp startport=8001 numberofports=1
```

**Option 4: Disable Hyper-V Dynamic Ports** (Not Recommended)
- May impact WSL and Docker
- Only use as last resort

---

## Current Standard Configuration

Based on `quick-start-dev.ps1` and current setup:

**Backend (FastAPI)**:
- Default Port: **8000**
- Alternative Port: 8001 or 8002 (if conflicts)
- Host: 0.0.0.0 (all interfaces)

**Frontend (Next.js)**:
- Port: **3000**
- API Base URL: `http://localhost:8000` (or WSL IP in hybrid mode)

**Database (PostgreSQL)**:
- Internal Port: 5432
- Exposed Port: **15432**
- Host: localhost (Windows) or 172.19.0.3 (Docker network)

**Redis**:
- Internal Port: 6379
- Exposed Port: **16379**
- Host: localhost (Windows) or 172.19.0.2 (Docker network)

---

## Port Selection Guidelines

### Development Ports
- **3000**: Next.js frontend (standard)
- **8000**: FastAPI backend (primary)
- **8001**: FastAPI backend (alternative - legacy)
- **8002**: FastAPI backend (alternative - port conflict resolution)

### Database Ports
- **15432**: PostgreSQL (external access)
- **16379**: Redis (external access)

### Monitoring Ports
- **9090**: Prometheus (optional)
- **3001**: Grafana (optional)

### Reserved/Problematic Ports
Avoid these ports on Windows:
- **8001**: Often reserved by WinNAT/Hyper-V
- **80, 443**: Require administrator privileges
- **3306**: MySQL (may conflict)
- **5432**: PostgreSQL (may conflict with local install)

---

## Troubleshooting Port Issues

### Check Port Availability
```powershell
# Check if port is in use
netstat -ano | findstr :<PORT>

# Test port binding
Test-NetConnection -ComputerName localhost -Port <PORT>
```

### Find Process Using Port
```powershell
# List all processes using ports
Get-NetTCPConnection | Where-Object {$_.State -eq "Listen"} | Select-Object LocalPort, OwningProcess, @{Name="ProcessName";Expression={(Get-Process -Id $_.OwningProcess).ProcessName}}
```

### Release Port
```powershell
# Find PID
$pid = (Get-NetTCPConnection -LocalPort <PORT>).OwningProcess

# Kill process
Stop-Process -Id $pid -Force
```

### Check Windows Reserved Ports
```powershell
netsh interface ipv4 show excludedportrange protocol=tcp
```

---

## Related Documentation

- [Developer Setup Guide](../getting-started/dev-setup.md) - Current port configuration
- [Deployment Topology](../diagrams/deployment.md) - Port mapping diagram
- [Startup Scripts Guide](../../scripts/README.md) - Script documentation
- [Troubleshooting Playbook](../operations/troubleshooting.md) - Common issues

---

**Last Updated**: October 2025 (consolidated from PORT_8001_FIX_SUMMARY, QUICK_FIX_PORT_8001, FIX_PORT_8001_ERROR, PORT_CHANGE_8001)
