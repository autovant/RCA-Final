# IMMEDIATE FIX REQUIRED - Port Forwarding Broken

## Problem

The port forwarding was set up incorrectly. It's forwarding to "T" instead of the WSL IP:

```
Address         Port        Address         Port
0.0.0.0         8000        T               8000  ← WRONG!
```

This happened because the script couldn't parse the WSL IP correctly.

## SOLUTION - Run as Administrator

### Step 1: Open PowerShell as Administrator

Right-click PowerShell → **"Run as Administrator"**

### Step 2: Clear Bad Rules and Set Up Correctly

```powershell
# Clear all broken port proxy rules
netsh interface portproxy reset

# Get the correct WSL IP
$wslIP = (wsl bash -c "hostname -I | awk '{print `$1}'").Trim()
Write-Host "WSL IP: $wslIP"

# If WSL IP is empty or invalid, restart WSL and try again
if ([string]::IsNullOrWhiteSpace($wslIP) -or $wslIP -notmatch '^\d+\.\d+\.\d+\.\d+$') {
    Write-Host "Restarting WSL..."
    wsl --shutdown
    Start-Sleep -Seconds 5
    $wslIP = (wsl bash -c "hostname -I | awk '{print `$1}'").Trim()
    Write-Host "New WSL IP: $wslIP"
}

# Set up port forwarding correctly
netsh interface portproxy add v4tov4 listenport=8000 listenaddress=0.0.0.0 connectport=8000 connectaddress=$wslIP
netsh interface portproxy add v4tov4 listenport=3000 listenaddress=0.0.0.0 connectport=3000 connectaddress=$wslIP

# Verify
netsh interface portproxy show all

# Add firewall rules
New-NetFirewallRule -DisplayName "WSL2 Port 8000" -Direction Inbound -LocalPort 8000 -Protocol TCP -Action Allow -ErrorAction SilentlyContinue
New-NetFirewallRule -DisplayName "WSL2 Port 3000" -Direction Inbound -LocalPort 3000 -Protocol TCP -Action Allow -ErrorAction SilentlyContinue
```

### Step 3: Test

```powershell
curl http://localhost:8000/api/health/live
```

Should return: `{"status":"ok","app":"RCA Engine","version":"1.0.0"}`

### Step 4: Update UI Environment

```powershell
# Go back to normal PowerShell (no admin needed)
cd "c:\Users\syed.shareef\.vscode\repos\RCA - v7\RCA-Final"

# Update .env.local to use localhost
"NEXT_PUBLIC_API_BASE_URL=http://localhost:8000" | Out-File -FilePath "ui\.env.local" -Encoding utf8

# Restart UI
cd ui
# Stop current UI with Ctrl+C
npm run dev
```

---

## Alternative: Manual IP Entry

If port forwarding doesn't work, you can use the WSL IP directly:

### Get Current WSL IP:
```powershell
wsl bash -c "hostname -I | awk '{print `$1}'"
```

### Update .env.local:
```bash
NEXT_PUBLIC_API_BASE_URL=http://<WSL_IP>:8000
```

### Test from Windows:
```powershell
curl http://<WSL_IP>:8000/api/health/live
```

If this times out, it's a Windows Firewall issue blocking WSL traffic.

---

## Why This Happened

The `fix-wsl-port-forwarding.ps1` script had a bug:
```powershell
$wslIP = (wsl hostname -I).Split()[0].Trim()
```

This parsed incorrectly when WSL returned an error message, resulting in "T" being stored instead of an IP.

---

## Quick Commands

**Check Current Port Proxy:**
```powershell
netsh interface portproxy show all
```

**Clear All Port Proxy Rules:**
```powershell
netsh interface portproxy reset
```

**Get WSL IP:**
```powershell
wsl bash -c "hostname -I | awk '{print \$1}'"
```

**Test Backend from WSL:**
```powershell
wsl bash -c "curl http://localhost:8000/api/health/live"
```

**Test Backend from Windows:**
```powershell
curl http://localhost:8000/api/health/live
```

---

## Current Status

✅ Backend is running in WSL Docker  
✅ Backend works from within WSL  
✅ Containers are healthy  
❌ Port forwarding is broken (forwarding to "T")  
❌ Windows cannot access localhost:8000  
❌ Windows cannot access WSL IP directly (firewall?)

**Action Required**: Run the commands above as Administrator to fix port forwarding.

---

**Last Updated**: October 13, 2025
