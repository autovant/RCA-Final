# SOLUTION: Access Backend Directly via WSL IP

## Quick Fix (No Admin Required!)

Since Windows port forwarding requires administrator privileges, the **easiest solution** is to configure your application to use the WSL IP directly.

### Current Situation:
- ✅ Backend works in WSL: `wsl bash -c "curl http://localhost:8000/api/health/live"` 
- ❌ Backend NOT accessible from Windows: `curl http://localhost:8000/api/health/live`
- WSL IP Address: **192.168.0.117**

---

## Option 1: Update UI to Use WSL IP (Recommended - No Admin Needed!)

###  Step 1: Create Environment File

Create `ui/.env.local`:

```bash
NEXT_PUBLIC_API_BASE_URL=http://192.168.0.117:8000
```

### Step 2: Restart UI

```powershell
# Stop UI (Ctrl+C in the terminal running it)
# Then restart:
cd ui
npm run dev
```

### Step 3: Test

1. Go to http://localhost:3000 (or 3001)
2. Click "Sign Up"
3. Fill form and click "Create Account"
4. Should now work! ✅

---

## Option 2: Run Port Forwarding Fix as Administrator

If you want `localhost:8000` to work:

### Step 1: Open PowerShell as Administrator

Right-click PowerShell → "Run as Administrator"

### Step 2: Set Up Port Forwarding

```powershell
cd "c:\Users\syed.shareef\.vscode\repos\RCA - v7\RCA-Final"

# Get WSL IP (after WSL restart)
$wslIP = (wsl bash -c "hostname -I").Trim().Split()[0]
Write-Host "WSL IP: $wslIP"

# Set up port forwarding
netsh interface portproxy delete v4tov4 listenport=8000 listenaddress=0.0.0.0
netsh interface portproxy add v4tov4 listenport=8000 listenaddress=0.0.0.0 connectport=8000 connectaddress=$wslIP

netsh interface portproxy delete v4tov4 listenport=3000 listenaddress=0.0.0.0
netsh interface portproxy add v4tov4 listenport=3000 listenaddress=0.0.0.0 connectport=3000 connectaddress=$wslIP

# Add firewall rules
New-NetFirewallRule -DisplayName "WSL2 Port 8000" -Direction Inbound -LocalPort 8000 -Protocol TCP -Action Allow -ErrorAction SilentlyContinue
New-NetFirewallRule -DisplayName "WSL2 Port 3000" -Direction Inbound -LocalPort 3000 -Protocol TCP -Action Allow -ErrorAction SilentlyContinue

# Verify
netsh interface portproxy show all
```

### Step 3: Test

```powershell
curl http://localhost:8000/api/health/live
```

Should return: `{"status":"ok","app":"RCA Engine","version":"1.0.0"}`

---

## Option 3: Use WSL IP in Browser (Temporary Testing)

Just access the UI using the WSL IP:

- UI: http://192.168.0.117:3000
- API: http://192.168.0.117:8000

**Note**: WSL IP changes when WSL restarts!

---

## Why This Happens

1. Docker containers run in WSL2
2. WSL2 has a separate network from Windows
3. Containers bind to `0.0.0.0:8000` in WSL
4. Windows cannot access WSL's `localhost` by default
5. Requires either:
   - Port forwarding (needs admin)
   - Direct WSL IP access (no admin needed)

---

## Recommended Solution Summary

### For Development (Easiest):

Create `ui/.env.local`:
```
NEXT_PUBLIC_API_BASE_URL=http://192.168.0.117:8000
```

Restart UI.

### For Production/Permanent:

Run port forwarding setup as Administrator (see Option 2 above).

---

## Verification Steps

After applying any solution:

1. **Test Backend**:
   ```powershell
   curl http://localhost:8000/api/health/live
   # OR if using WSL IP:
   curl http://192.168.0.117:8000/api/health/live
   ```

2. **Test UI Sign Up**:
   - Open browser
   - Go to UI URL
   - Open Console (F12)
   - Click "Sign Up"
   - Fill form
   - Click "Create Account"
   - Check console logs

3. **Expected Console Output**:
   ```
   🔍 Signup form submitted {email: "...", username: "...", hasPassword: true}
   ✅ All validations passed, sending to API...
   📍 API Base URL: http://192.168.0.117:8000  ← Should show WSL IP
   📤 Sending registration request: {...}
   ✅ Registration successful!
   ```

---

## Troubleshooting

### "Cannot connect to server"
- Check backend is running: `wsl bash -c "docker ps | grep rca_core"`
- Check WSL IP hasn't changed: `wsl bash -c "hostname -I"`
- Update `.env.local` if IP changed

### WSL IP Changed After Restart
```powershell
# Get new IP:
$newIP = (wsl bash -c "hostname -I").Trim().Split()[0]
Write-Host "New WSL IP: $newIP"

# Update .env.local with new IP
# Restart UI
```

### Still Not Working
- Restart WSL: `wsl --shutdown` then wait 5 seconds
- Restart containers: `wsl bash -c "cd /mnt/c/Users/syed.shareef/.vscode/repos/RCA\ -\ v7/RCA-Final && docker compose -f deploy/docker/docker-compose.yml restart"`
- Clear browser cache: Ctrl+Shift+R

---

**Quick Start Command:**

```powershell
# Create env file
"NEXT_PUBLIC_API_BASE_URL=http://192.168.0.117:8000" | Out-File -FilePath "ui/.env.local" -Encoding utf8

# Restart UI
cd ui
npm run dev
```

Then test sign up!

---

**Last Updated**: October 13, 2025  
**Status**: ✅ Solution provided - Use WSL IP directly (no admin needed!)
