# WSL 2 Networking Configuration & Troubleshooting

This document consolidates all WSL 2 networking issues, solutions, and configuration guidance from the development cycle.

> **Current Guide**: See [Developer Setup Guide](../getting-started/dev-setup.md) and [Deployment Topology](../diagrams/deployment.md) for current network configuration.

---

## Problem Overview

### Issue
Docker containers running in WSL 2 (PostgreSQL, Redis) not accessible from Windows via `localhost`.

**Symptoms**:
- PostgreSQL at `localhost:15432` - connection refused
- Redis at `localhost:16379` - connection refused
- Backend API at `localhost:8000` or `localhost:8001` - connection issues

### Root Causes

1. **Mirrored Networking Incompatibility**
   - `.wslconfig` with `networkingMode=mirrored` doesn't work with Docker bridge networks
   - Docker uses internal bridge networks (172.x.x.x IPs)
   - Not directly routable from Windows

2. **Dynamic IP Addressing**
   - WSL 2 IP address changes after Windows restart
   - Port forwarding rules become stale
   - Requires reconfiguration

3. **Missing Port Forwarding**
   - WSL 2 NAT mode requires explicit port forwarding rules
   - Windows firewall may block connections

---

## Solutions Implemented

### ✅ Solution 1: WSL NAT Mode + Port Forwarding (Recommended)

**Status**: Working - Implemented October 15, 2025

#### Step 1: Configure WSL for NAT Mode

**File**: `C:\Users\<your-username>\.wslconfig`

```ini
[wsl2]
# Disable mirrored networking - incompatible with Docker
# networkingMode=mirrored

# Use default NAT mode for Docker compatibility
memory=8GB
processors=4
```

**Apply Changes**:
```powershell
wsl --shutdown
# Wait 8 seconds for shutdown
# Restart WSL by opening any WSL terminal
```

#### Step 2: Set Up Port Forwarding

**Script Created**: `fix-docker-port-forwarding.ps1`

**Run as Administrator**:
```powershell
.\fix-docker-port-forwarding.ps1
```

**What It Does**:
1. Detects current WSL IP address
2. Creates `netsh` port forwarding rules
3. Configures Windows Firewall rules
4. Verifies connectivity

**Ports Forwarded**:
- `15432` → PostgreSQL (internal 5432)
- `16379` → Redis (internal 6379)
- `8000` or `8001` → FastAPI Backend
- `3000` → Next.js Frontend
- `11434` → Ollama (optional)

**netsh Rules Created**:
```powershell
Listen on ipv4:             Connect to ipv4:
Address         Port        Address         Port
0.0.0.0         15432       <WSL_IP>        15432
0.0.0.0         16379       <WSL_IP>        16379
0.0.0.0         8001        <WSL_IP>        8001
0.0.0.0         3000        <WSL_IP>        3000
```

#### Step 3: Configure Windows Firewall

**Script Created**: `ENABLE-NETWORK-ACCESS.ps1`

**Run as Administrator**:
```powershell
.\ENABLE-NETWORK-ACCESS.ps1
```

**Firewall Rules Added**:
- Allow inbound TCP on port 15432 (PostgreSQL)
- Allow inbound TCP on port 16379 (Redis)
- Allow inbound TCP on port 8000/8001 (Backend API)
- Allow inbound TCP on port 3000 (Frontend)

#### Step 4: Minimal Environment Configuration

**File**: `.env`

```bash
# Database
POSTGRES_HOST=localhost
POSTGRES_PORT=15432
POSTGRES_USER=rca_user
POSTGRES_PASSWORD=rca_password_change_in_production
POSTGRES_DB=rca_engine

# Redis
REDIS_HOST=localhost
REDIS_PORT=16379
REDIS_DB=0

# Security
JWT_SECRET_KEY=your-secret-key-minimum-32-characters-long

# API
API_HOST=0.0.0.0
API_PORT=8000
```

---

### ✅ Solution 2: Direct WSL IP Access (Alternative)

**When to Use**: If port forwarding is problematic or blocked by policy

#### Get WSL IP Address
```powershell
wsl hostname -I
# Example output: 172.28.36.28
```

#### Update Frontend Configuration

**File**: `ui/.env.local`
```bash
NEXT_PUBLIC_API_BASE_URL=http://172.28.36.28:8001
```

**File**: `ui/src/data/jobsPreview.ts`
```typescript
export const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://172.28.36.28:8001";
```

#### Access URLs
- Frontend: `http://<WSL_IP>:3000`
- Backend API: `http://<WSL_IP>:8000` or `8001`
- PostgreSQL: `<WSL_IP>:15432`
- Redis: `<WSL_IP>:16379`

**Pros**:
- No port forwarding needed
- More direct connection
- CORS must allow WSL IP

**Cons**:
- IP changes after Windows restart
- Must update configuration manually
- Less convenient than localhost

---

### ❌ Solution 3: Mirrored Networking (Not Recommended)

**Status**: Doesn't work with Docker bridge networks

**Requirements**:
- Windows 11 22H2 or later
- Not compatible with Docker's bridge networking

**File**: `C:\Users\<your-username>\.wslconfig`
```ini
[wsl2]
networkingMode=mirrored  # ❌ Breaks Docker
dnsTunneling=true
firewall=true
autoProxy=true
```

**Why It Fails**:
- Docker uses bridge networks (172.x.x.x)
- Mirrored mode doesn't route to bridge networks
- Containers become unreachable

---

## Verification & Testing

### Test Port Connectivity
```powershell
# Test PostgreSQL port
Test-NetConnection -ComputerName localhost -Port 15432

# Test Redis port
Test-NetConnection -ComputerName localhost -Port 16379

# Test Backend API
Test-NetConnection -ComputerName localhost -Port 8000
```

### Check Port Forwarding Rules
```powershell
# List all port forwarding rules
netsh interface portproxy show all
```

### Check WSL IP Address
```powershell
# From PowerShell
wsl hostname -I

# From WSL terminal
hostname -I
ip addr show eth0
```

### Test Database Connection
```bash
# From WSL terminal
psql -h localhost -p 15432 -U rca_user -d rca_engine

# From Windows (requires psql installed)
psql -h localhost -p 15432 -U rca_user -d rca_engine
```

---

## Troubleshooting

### Port Forwarding Stops Working

**Symptom**: After Windows restart, can't connect to `localhost:15432`

**Cause**: WSL IP address changed

**Fix**:
```powershell
# Re-run port forwarding script as Administrator
.\fix-docker-port-forwarding.ps1
```

### Firewall Blocking Connections

**Symptom**: Firewall prompts or connection timeouts

**Fix**:
```powershell
# Re-run firewall configuration as Administrator
.\ENABLE-NETWORK-ACCESS.ps1
```

### Remove Stale Port Forwarding Rules

```powershell
# Remove specific rule
netsh interface portproxy delete v4tov4 listenport=15432 listenaddress=0.0.0.0

# Remove all rules
netsh interface portproxy reset
```

### Docker Containers Not Starting

**Symptom**: Containers fail to start or can't bind to ports

**Check**:
```bash
# Inside WSL
docker ps
docker logs <container_name>

# Check port availability
sudo netstat -tulpn | grep :5432
```

---

## Best Practices

### Development Workflow

1. **Start Docker Services**:
   ```powershell
   .\start-dev.ps1  # Starts Docker containers via WSL
   ```

2. **Configure Port Forwarding** (once per Windows restart):
   ```powershell
   .\fix-docker-port-forwarding.ps1
   ```

3. **Start Application**:
   ```powershell
   .\quick-start-dev.ps1
   ```

### After Windows Restart

1. Check WSL IP: `wsl hostname -I`
2. Update port forwarding: `.\fix-docker-port-forwarding.ps1`
3. If using direct IP: Update `ui/.env.local` with new WSL IP

### Production Deployment

- **Don't use port forwarding** - deploy entirely in Linux
- **Use Docker Compose** - internal networking handles routing
- **Reverse proxy** (nginx/Traefik) for external access

---

## Network Topology

```
┌─────────────────────────────────────┐
│  Windows Host                       │
│                                     │
│  ┌──────────────────────────────┐  │
│  │ Frontend (Next.js)           │  │
│  │ Port: 3000                   │  │
│  │ Calls: localhost:8000        │  │
│  └──────────┬───────────────────┘  │
│             │                       │
│             ↓ Port Forwarding       │
│  ┌──────────────────────────────┐  │
│  │ netsh portproxy              │  │
│  │ 0.0.0.0:8000 → WSL_IP:8000   │  │
│  │ 0.0.0.0:15432 → WSL_IP:15432 │  │
│  │ 0.0.0.0:16379 → WSL_IP:16379 │  │
│  └──────────┬───────────────────┘  │
└─────────────┼───────────────────────┘
              │
              ↓ WSL NAT
┌─────────────────────────────────────┐
│  WSL 2 (Ubuntu)                     │
│  IP: 172.28.36.28 (dynamic)         │
│                                     │
│  ┌──────────────────────────────┐  │
│  │ Backend (FastAPI)            │  │
│  │ Port: 8000                   │  │
│  │ Calls: localhost:15432       │  │
│  └──────────┬───────────────────┘  │
│             │                       │
│             ↓ Docker Bridge         │
│  ┌──────────────────────────────┐  │
│  │ Docker Network (172.19.0.0)  │  │
│  │                              │  │
│  │ PostgreSQL: 172.19.0.3:5432  │  │
│  │ → Exposed: 15432             │  │
│  │                              │  │
│  │ Redis: 172.19.0.2:6379       │  │
│  │ → Exposed: 16379             │  │
│  └──────────────────────────────┘  │
└─────────────────────────────────────┘
```

---

## Related Files

**Scripts**:
- `fix-docker-port-forwarding.ps1` - Port forwarding automation
- `ENABLE-NETWORK-ACCESS.ps1` - Firewall configuration
- `start-dev.ps1` - Docker services startup
- `quick-start-dev.ps1` - Full stack startup

**Configuration**:
- `C:\Users\<user>\.wslconfig` - WSL 2 configuration
- `.env` - Environment variables
- `ui/.env.local` - Frontend API configuration

---

## Related Documentation

- [Deployment Topology Diagram](../diagrams/deployment.md) - Visual network map
- [Developer Setup Guide](../getting-started/dev-setup.md) - Complete setup
- [Startup Scripts Guide](../../scripts/README.md) - Script documentation
- [Troubleshooting Playbook](../operations/troubleshooting.md) - Common issues

---

**Last Updated**: October 2025 (consolidated from WSL_NETWORKING_RESOLVED, WSL_NETWORKING_FIX, WSL_NETWORKING_SOLUTION, FIX_PORT_FORWARDING_NOW, WSL_PORT_FORWARDING_FIX_REQUIRED)
