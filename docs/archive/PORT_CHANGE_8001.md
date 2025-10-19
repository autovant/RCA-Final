# Port Change Summary: 8000 → 8001

## Changes Made

### 1. Docker Compose Configuration
**File:** `deploy/docker/docker-compose.yml`

Changed port mappings:
- API: `8000:8000` → `8001:8000` (Windows:Container)
- Metrics: `8001:8001` → `8002:8001`

Updated environment variables:
- `NEXT_PUBLIC_API_URL`: `http://localhost:8000` → `http://localhost:8001`
- `NEXT_PUBLIC_WS_URL`: `ws://localhost:8000` → `ws://localhost:8001`

### 2. UI Environment Configuration
**File:** `ui/.env.local`

Changed:
```
NEXT_PUBLIC_API_BASE_URL=http://localhost:8001
```

### 3. Port Forwarding Script
**File:** `fix-wsl-port-forwarding.ps1`

Updated ports array:
- Removed: `8000`
- Added: `8001` for API
- Updated: `8002` for Metrics

### 4. Quick Update Script
**File:** `update-port-forwarding-8001.ps1` (NEW)

Created a quick script to switch port forwarding from 8000 to 8001.

## Next Steps

### ⚠️ Required Action (Must Run as Administrator):

**Option 1: Full Port Forwarding Setup**
```powershell
# Right-click PowerShell → Run as Administrator
.\fix-wsl-port-forwarding.ps1
```

**Option 2: Quick Port Update**
```powershell
# Right-click PowerShell → Run as Administrator
.\update-port-forwarding-8001.ps1
```

**Option 3: Manual Commands (if scripts don't work)**
```powershell
# In Administrator PowerShell:
$wslIP = (wsl hostname -I).Split()[0].Trim()
netsh interface portproxy delete v4tov4 listenport=8000 listenaddress=0.0.0.0
netsh interface portproxy add v4tov4 listenport=8001 listenaddress=0.0.0.0 connectport=8001 connectaddress=$wslIP
```

### 2. Restart UI (if running)
```powershell
# In the UI terminal (Ctrl+C to stop, then):
cd ui
npm run dev
```

### 3. Add Windows Firewall Rule (if needed)
```powershell
# In Administrator PowerShell:
New-NetFirewallRule -DisplayName "WSL Backend 8001" -Direction Inbound -LocalPort 8001 -Protocol TCP -Action Allow
```

## Verification

### Test Backend from Windows:
```powershell
curl http://localhost:8001/api/health/live
```

Expected response:
```json
{"status":"ok","app":"RCA Engine","version":"1.0.0"}
```

### Test Backend from WSL:
```powershell
wsl bash -c "curl http://localhost:8001/api/health/live"
```

### Test Registration Endpoint:
```powershell
curl -X POST http://localhost:8001/api/auth/register -H "Content-Type: application/json" -d '{\"username\":\"testuser\",\"email\":\"test@example.com\",\"password\":\"TestPass123\",\"full_name\":\"Test User\"}'
```

## Current Status

✅ Docker containers restarted on port 8001
✅ Backend accessible from WSL on port 8001
✅ UI configuration updated
✅ Port forwarding scripts updated
⚠️ Port forwarding needs to be run as Administrator
⚠️ UI needs to be restarted to pick up new .env.local

## URLs After Port Change

- **API:** http://localhost:8001
- **API Docs:** http://localhost:8001/docs
- **API Health:** http://localhost:8001/api/health/live
- **Metrics:** http://localhost:8002/metrics
- **UI:** http://localhost:3000 (unchanged)

## Why Port 8001?

Port 8000 was experiencing rate limiting issues from testing. Using port 8001 provides:
- Fresh rate limiting counters
- Clearer separation from other services
- Avoids conflicts with common development tools

## Troubleshooting

### If "Connection Refused":
1. Check containers are running: `wsl bash -c "docker ps"`
2. Run port forwarding script as Administrator
3. Check firewall rules

### If "Rate Limit Exceeded":
Rate limits reset every 10 minutes. Wait or restart containers:
```powershell
wsl bash -c "docker restart rca_core"
```

### If UI Can't Connect:
1. Verify UI is using new port: Check browser Network tab
2. Restart UI: Stop with Ctrl+C and run `npm run dev` again
3. Clear browser cache
