# WSL2 Docker Port Forwarding - Complete Solution

## Problem Summary
PostgreSQL and Redis containers running in WSL2 Docker were not accessible from Windows at `localhost:15432` and `localhost:16379` due to WSL2 networking issues.

## Root Cause
1. **Mirrored networking mode** in `.wslconfig` doesn't work properly with Docker bridge networks
2. Docker containers use internal bridge networks (172.x.x.x) that aren't directly accessible from Windows
3. WSL2's dynamic IP addressing requires port forwarding rules to be updated when WSL restarts

## Solution Implemented

### 1. Configure WSL for NAT Mode (Not Mirrored)
File: `C:\Users\<your-username>\.wslconfig`
```ini
[wsl2]
# Comment out mirrored networking - it doesn't work with Docker bridge mode
#networkingMode=mirrored

# Use default NAT mode for better Docker compatibility
memory=8GB
processors=4
```

### 2. Set Up Port Forwarding
Run the script: `fix-docker-port-forwarding.ps1` as Administrator

This script:
- Restarts WSL if network mode changed
- Gets the current WSL IP address
- Creates `netsh` port forwarding rules from Windows to WSL
- Configures Windows Firewall to allow the connections

**Ports forwarded:**
- `15432` → PostgreSQL
- `16379` → Redis
- `8001` → FastAPI Backend
- `3000` → Next.js Frontend
- `11434` → Ollama (optional)

### 3. Configure Environment Variables
File: `.env` (minimal configuration)
```bash
JWT_SECRET_KEY=your-secret-key-here-change-in-production-minimum-32-characters-long
POSTGRES_HOST=localhost
POSTGRES_PORT=15432
POSTGRES_USER=rca_user
POSTGRES_PASSWORD=rca_password_change_in_production
POSTGRES_DB=rca_engine
REDIS_HOST=localhost
REDIS_PORT=16379
LOG_LEVEL=INFO
```

## Verification

### Check WSL IP and Port Forwarding
```powershell
# Get WSL IP
wsl hostname -I

# View port forwarding rules
netsh interface portproxy show v4tov4

# Test PostgreSQL connection
Test-NetConnection -ComputerName localhost -Port 15432
```

### Test Database Connection
```powershell
# Simple socket test
python -c "import socket; s = socket.socket(); s.settimeout(5); result = s.connect_ex(('localhost', 15432)); print(f'Connection: {result} (0=success)'); s.close()"
```

## When to Rerun the Fix

You need to rerun `fix-docker-port-forwarding.ps1` when:
1. WSL is restarted (`wsl --shutdown`)
2. Windows is rebooted
3. Services become unreachable at localhost

**Why?** WSL2's IP address changes on restart, so port forwarding rules need to be updated with the new IP.

## Quick Start Commands

### Manual Container Start (if startup script times out)
```powershell
# Start containers
wsl bash -c "cd /mnt/c/Users/<your-path>/RCA-Final && docker compose -f docker-compose.dev.yml up -d"

# Check status
wsl docker ps

# View logs
wsl docker logs rca_db
wsl docker logs rca_redis
```

### Start Backend and Frontend
```powershell
# Backend (in one terminal)
python -m uvicorn apps.api.main:app --host 0.0.0.0 --port 8001 --reload

# Frontend (in another terminal)
cd ui
npm run dev
```

## Troubleshooting

### Port 15432 not reachable
1. Check containers are running: `wsl docker ps`
2. Verify port forwarding: `netsh interface portproxy show v4tov4`
3. Check WSL IP matches forwarding rules: `wsl hostname -I`
4. If IP changed, rerun: `fix-docker-port-forwarding.ps1`

### Container won't start
```powershell
# Check container logs
wsl docker logs rca_db

# Restart containers
wsl docker compose -f docker-compose.dev.yml restart
```

### Windows Firewall blocking
```powershell
# Check firewall rules
Get-NetFirewallRule -DisplayName "*WSL*" | Select-Object DisplayName, Enabled

# Temporarily disable firewall for testing (as Admin)
Set-NetFirewallProfile -Profile Domain,Public,Private -Enabled False
```

## Files Created

1. **fix-docker-port-forwarding.ps1** - Main fix script (run as Admin)
2. **fix-wsl-networking.ps1** - Alternative diagnostic script
3. **fix-firewall-wsl-mirrored.ps1** - Firewall-only fix
4. **start-databases-wsl-ip.ps1** - Quick start with direct WSL IP

## Success Indicators

✅ Port forwarding configured:
```
Listen on ipv4:             Connect to ipv4:
Address         Port        Address         Port
0.0.0.0         15432       172.28.x.x      15432
0.0.0.0         16379       172.28.x.x      16379
```

✅ Connection test passes:
```
TcpTestSucceeded : True
```

✅ Containers running:
```
rca_db     Up x seconds (healthy)
rca_redis  Up x seconds (healthy)
```

## Alternative: Use WSL IP Directly

If localhost doesn't work, you can connect directly to WSL IP:
```bash
# In .env file
POSTGRES_HOST=172.28.36.28  # Your actual WSL IP
REDIS_HOST=172.28.36.28
```

**Note:** This IP changes on WSL restart, so it's not recommended for long-term use.

## Next Steps

Once port forwarding is working:
1. Run: `./start-environment.ps1` (may show timeout warning but containers will start)
2. Manually verify: `Test-NetConnection -ComputerName localhost -Port 15432`
3. Start backend: `python -m uvicorn apps.api.main:app --host 0.0.0.0 --port 8001 --reload`
4. Start UI: `cd ui && npm run dev`
5. Access at: `http://localhost:3000`

---

**Last Updated:** October 15, 2025
**WSL Version:** WSL 2
**Windows Build:** 26100
**Solution Status:** ✅ Working (port forwarding configured, containers accessible)
