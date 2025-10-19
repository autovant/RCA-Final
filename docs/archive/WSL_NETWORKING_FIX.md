# WSL2 Network Configuration Guide
# This file explains how to fix WSL2 Docker port forwarding issues

## Problem
When running Docker inside WSL2 (not Docker Desktop), ports exposed by containers
are not accessible from Windows via localhost.

## Solutions

### Option 1: Quick Fix - Port Forwarding Script (Temporary)
Run the provided PowerShell script as Administrator:
```powershell
# Open PowerShell as Administrator
.\fix-wsl-port-forwarding.ps1
```

**Note:** This needs to be run again if WSL2 restarts, as the IP may change.

### Option 2: Configure WSL2 for Mirrored Networking (Permanent - Windows 11 22H2+)
1. Create/edit `C:\Users\<YourUsername>\.wslconfig`:
```ini
[wsl2]
networkingMode=mirrored
dnsTunneling=true
firewall=true
autoProxy=true
```

2. Restart WSL2:
```powershell
wsl --shutdown
```

3. Start WSL2 again and verify:
```bash
wsl hostname -I
```

### Option 3: Use WSL IP Directly
Access services using the WSL2 IP address instead of localhost:

1. Get WSL IP:
```powershell
wsl hostname -I
```

2. Access services:
- UI: `http://<WSL-IP>:3000`
- API: `http://<WSL-IP>:8000`

### Option 4: Switch to Docker Desktop
Install Docker Desktop for Windows, which handles WSL2 networking automatically.

## Current WSL2 IP Address
Run this to get the current IP:
```powershell
wsl hostname -I | %{$_.Split()[0]}
```

## Recommended Solution
For Windows 11 users: Use **Option 2** (Mirrored Networking) for a permanent fix.
For Windows 10 users: Use **Option 1** (Port Forwarding Script) or **Option 4** (Docker Desktop).

## Verifying Access
After applying any fix, test with:
```powershell
# Test UI
Invoke-WebRequest -Uri "http://localhost:3000" -UseBasicParsing

# Test API
Invoke-WebRequest -Uri "http://localhost:8000/api/health/live" -UseBasicParsing
```
