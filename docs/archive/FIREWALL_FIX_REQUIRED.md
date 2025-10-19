# FINAL FIX: Windows Firewall Configuration

## Current Status

✅ Port forwarding is configured correctly  
✅ Backend is running in WSL  
✅ WSL can access backend on localhost:8000  
❌ **Windows is blocked by Windows Firewall**  

## Quick Fix (Run as Administrator)

Open PowerShell as Administrator and run:

```powershell
# Add firewall rules for WSL ports
New-NetFirewallRule -DisplayName "WSL2 Port 8000 (Backend)" -Direction Inbound -LocalPort 8000 -Protocol TCP -Action Allow
New-NetFirewallRule -DisplayName "WSL2 Port 3000 (UI)" -Direction Inbound -LocalPort 3000 -Protocol TCP -Action Allow

# Verify
Test-NetConnection -ComputerName localhost -Port 8000
```

## Alternative: Disable Firewall for Private Networks (Temporary)

If you're on a trusted network:

1. Open Windows Defender Firewall
2. Click "Turn Windows Defender Firewall on or off"
3. Turn OFF for "Private network settings"
4. Click OK
5. Test: `curl http://localhost:8000/api/health/live`

**Remember to turn it back on later!**

## Verification

After adding firewall rules, test:

```powershell
# Should work now:
curl http://localhost:8000/api/health/live

# Should return:
# {"status":"ok","app":"RCA Engine","version":"1.0.0"}
```

## Then Restart UI

```powershell
cd ui
# Stop current UI (Ctrl+C if running)
npm run dev
```

## Test Sign Up

1. Go to http://localhost:3000
2. Click "Sign Up"
3. Fill form (watch password checkmarks!)
4. Click "Create Account"
5. Should work! ✅

---

**Status**: Port forwarding configured, firewall rule needed (run as admin)
