# Port 8001 Access Error - WinError 10013

## Error Message
```
ERROR: [WinError 10013] An attempt was made to access a socket in a way forbidden by its access permissions
```

## Root Cause
Port 8001 is being held by a Windows system service (svchost). This is common with:
- **Hyper-V** dynamic port allocation
- **WinNAT** (Windows NAT for WSL/Docker)
- **Windows Reserved Ports**

## 🚀 Quick Solutions (Choose One)

### Option 1: Use Alternative Port (Fastest - Recommended)
This avoids the Windows conflict entirely:

```powershell
.\start-local-hybrid-alt-port.ps1
```

This script:
- Uses port **8002** instead of 8001
- Automatically updates all configuration
- Starts your app immediately

✅ **Access your app:**
- Frontend: http://localhost:3000
- Backend: http://localhost:8002

---

### Option 2: Fix Port 8001 (Requires Admin)
If you need to use port 8001 specifically:

```powershell
# Run PowerShell as Administrator
.\fix-port-8001.ps1
```

This script will:
1. Stop processes using port 8001
2. Check for port exclusions
3. Reset WinNAT if needed
4. Configure firewall rules
5. Verify port is available

⚠️ **Requires**: Administrator privileges  
⚠️ **May need**: Computer restart

---

### Option 3: Manual Quick Fix

#### Kill the process using port 8001:
```powershell
# Find the process
netstat -ano | findstr :8001

# Kill it (replace <PID> with the actual process ID)
taskkill /F /PID <PID>
```

If it's a system service that keeps coming back:

#### Restart WinNAT (as Administrator):
```powershell
net stop winnat
net start winnat
```

---

## 🔍 Diagnostic Commands

Check what's using the port:
```powershell
netstat -ano | findstr :8001
Get-Process -Id <PID>
```

Check port exclusions:
```powershell
netsh interface ipv4 show excludedportrange protocol=tcp
```

Test if port is accessible:
```powershell
Test-NetConnection -ComputerName 127.0.0.1 -Port 8001
```

---

## 📊 Port Usage Reference

| Service | Standard Port | Alternative Port |
|---------|--------------|------------------|
| Backend API | 8001 | 8002 |
| Frontend UI | 3000 | 3000 |
| PostgreSQL | 15432 | 15432 |
| Redis | 16379 | 16379 |

---

## ✅ Verification After Fix

### Test backend:
```powershell
# For standard port
curl http://localhost:8001/health

# For alternative port
curl http://localhost:8002/health
```

### Test in browser:
1. Open http://localhost:3000
2. Press F12 for DevTools
3. Check Console - should see successful API calls
4. No "ERR_CONNECTION_REFUSED" errors

---

## 🛠️ Permanent Solutions

### Exclude port from Hyper-V dynamic range:
```powershell
# Run as Administrator
netsh int ipv4 add excludedportrange protocol=tcp startport=8001 numberofports=1
```

### Disable Hyper-V (if not needed):
```powershell
# Run as Administrator  
bcdedit /set hypervisorlaunchtype off
# Restart computer
```

---

## 💡 Why This Happens

Windows 10/11 with **Hyper-V** or **WSL2** enabled reserves dynamic port ranges for NAT. Sometimes these ranges include port 8001.

The `svchost` process you see is Windows managing these virtual networks. It's not malicious - just Windows trying to help!

---

## 📝 Files Changed by Alternative Port Script

When using port 8002:
- `ui\.env.local` → `NEXT_PUBLIC_API_BASE_URL=http://localhost:8002`

That's it! The script handles everything else automatically.

---

## 🔄 Switching Back to Port 8001

If you fix the port issue and want to go back to 8001:

```powershell
# Update UI config
echo "NEXT_PUBLIC_API_BASE_URL=http://localhost:8001" | Out-File ui\.env.local -Encoding UTF8

# Use normal startup
.\start-local-hybrid.ps1
```

---

## 📞 Still Having Issues?

Try these in order:

1. **Close ALL PowerShell windows** and start fresh
2. **Restart your computer** (clears all port locks)
3. **Use the alternative port** (port 8002 - most reliable)
4. **Check Windows Event Viewer** for port conflict errors
5. **Temporarily disable antivirus** (may block port access)

---

## Summary Table

| Solution | Speed | Admin Required | Reliability |
|----------|-------|----------------|-------------|
| Alternative Port (8002) | ⚡ Instant | ❌ No | ✅ High |
| Fix Script | 🕐 2-5 min | ✅ Yes | ⚠️ Medium |
| Manual Fix | 🕐 1-3 min | ✅ Yes | ⚠️ Medium |
| Restart Computer | 🕐 5 min | ❌ No | ✅ High |

**Recommendation**: Use the alternative port script for fastest results! 🚀
