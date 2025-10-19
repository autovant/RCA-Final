# 🚨 URGENT: WSL Port Forwarding Issue Detected!

## Problem

The **"Create Account" button does nothing** because:

1. ✅ Backend API is running in WSL Docker
2. ✅ Backend works from within WSL
3. ❌ **Windows cannot reach the backend** (port forwarding issue)

### Evidence:
```powershell
# From WSL - WORKS ✅
wsl bash -c "curl http://localhost:8000/api/health/live"
{"status":"ok","app":"RCA Engine","version":"1.0.0"}

# From Windows PowerShell - FAILS ❌
curl http://localhost:8000/api/health/live
# Timeout...
```

---

## Solution: Fix WSL Port Forwarding

### Option 1: Run the Fix Script (Recommended)

**Must run as Administrator:**

1. **Right-click PowerShell** and select **"Run as Administrator"**
2. Run:
   ```powershell
   cd "c:\Users\syed.shareef\.vscode\repos\RCA - v7\RCA-Final"
   .\fix-wsl-port-forwarding.ps1
   ```

This script will:
- Get WSL2 IP address
- Set up port forwarding for ports 8000, 8001, 3000
- Configure Windows Firewall rules
- Enable port proxy

### Option 2: Manual Port Forwarding

**Run as Administrator:**

```powershell
# Get WSL IP
$wslIP = (wsl hostname -I).Split()[0].Trim()
Write-Host "WSL IP: $wslIP"

# Forward port 8000 (Backend API)
netsh interface portproxy add v4tov4 listenport=8000 listenaddress=0.0.0.0 connectport=8000 connectaddress=$wslIP

# Forward port 3000 (UI)
netsh interface portproxy add v4tov4 listenport=3000 listenaddress=0.0.0.0 connectport=3000 connectaddress=$wslIP

# Add firewall rules
New-NetFirewallRule -DisplayName "WSL2 Port 8000" -Direction Inbound -LocalPort 8000 -Protocol TCP -Action Allow
New-NetFirewallRule -DisplayName "WSL2 Port 3000" -Direction Inbound -LocalPort 3000 -Protocol TCP -Action Allow
```

### Option 3: Access via WSL IP Directly

**No admin required, but temporary:**

1. Get WSL IP:
   ```powershell
   wsl hostname -I
   ```
   
2. Use that IP in your browser:
   ```
   http://172.x.x.x:3000  # UI
   http://172.x.x.x:8000  # API
   ```

---

## How to Verify the Fix

### Test 1: From Windows PowerShell
```powershell
curl http://localhost:8000/api/health/live
```

**Expected Output:**
```json
{"status":"ok","app":"RCA Engine","version":"1.0.0"}
```

### Test 2: In Browser
Visit: http://localhost:8000/api/health/live

Should show JSON response.

### Test 3: Sign Up Form
1. Go to http://localhost:3000
2. Click "Sign Up"
3. Fill in form
4. Click "Create Account"
5. Open browser console (F12)
6. Should see console logs starting with 🔍 and either ✅ success or specific error

---

## Why This Happens

**WSL2 uses a virtualized network** that's separate from Windows. By default:
- WSL can reach Windows ports ✅
- **Windows CANNOT reach WSL ports ❌** (requires port forwarding)

This is a known Windows/WSL2 limitation and affects:
- Docker containers running in WSL
- Any service running in WSL
- Development servers in WSL

---

## Prevention

### Add to Startup (Optional)

To automatically fix port forwarding on reboot:

1. Create a scheduled task:
   ```powershell
   # Run as Administrator
   $action = New-ScheduledTaskAction -Execute "PowerShell.exe" -Argument "-ExecutionPolicy Bypass -File 'c:\Users\syed.shareef\.vscode\repos\RCA - v7\RCA-Final\fix-wsl-port-forwarding.ps1'"
   $trigger = New-ScheduledTaskTrigger -AtStartup
   $principal = New-ScheduledTaskPrincipal -UserId "SYSTEM" -LogonType ServiceAccount -RunLevel Highest
   Register-ScheduledTask -TaskName "WSL Port Forwarding" -Action $action -Trigger $trigger -Principal $principal
   ```

---

## Debugging Enhanced

I've added **console logging** to the signup form:

### What You'll See in Browser Console:

#### Successful Flow:
```
🔍 Signup form submitted {email: "test@example.com", username: "testuser", hasPassword: true}
✅ All validations passed, sending to API...
📍 API Base URL: http://localhost:8000
📤 Sending registration request: {email: "test@example.com", username: "testuser", password: "[HIDDEN]", full_name: "Test User"}
✅ Registration successful: {id: "...", username: "testuser", email: "test@example.com"}
```

#### Network Error (Current Issue):
```
🔍 Signup form submitted {email: "test@example.com", username: "testuser", hasPassword: true}
✅ All validations passed, sending to API...
📍 API Base URL: http://localhost:8000
📤 Sending registration request: {email: "test@example.com", username: "testuser", password: "[HIDDEN]", full_name: "Test User"}
❌ Registration failed: [Error object]
Error details: {message: "Network Error", response: undefined, status: undefined, code: "ERR_NETWORK"}
```

The error will now show:
> "Cannot connect to server. Please ensure the backend is running at http://localhost:8000"

---

## Quick Fix Checklist

- [ ] Close all PowerShell/CMD windows
- [ ] Open PowerShell as **Administrator**
- [ ] Run: `cd "c:\Users\syed.shareef\.vscode\repos\RCA - v7\RCA-Final"`
- [ ] Run: `.\fix-wsl-port-forwarding.ps1`
- [ ] Wait for success message
- [ ] Test: `curl http://localhost:8000/api/health/live`
- [ ] Should see JSON response ✅
- [ ] Refresh browser (Ctrl+Shift+R)
- [ ] Try "Sign Up" again
- [ ] Open console (F12) to see debug logs

---

## Alternative: Use Docker Desktop's WSL Integration

If port forwarding continues to be problematic:

1. Open Docker Desktop settings
2. Go to Resources → WSL Integration
3. Enable integration for your WSL distro
4. This should handle port forwarding automatically

---

## Summary

**Root Cause**: WSL2 network isolation prevents Windows from accessing WSL ports

**Fix**: Run `fix-wsl-port-forwarding.ps1` as Administrator

**Verification**: `curl http://localhost:8000/api/health/live` should work from Windows

**After Fix**: "Create Account" button will work properly!

---

**Last Updated**: October 13, 2025

**Status**: ⚠️ BLOCKING ISSUE - Must fix port forwarding first!
