# RCA Engine - Troubleshooting Access Issues

## Problem Summary
The RCA Engine Docker containers are running correctly inside WSL2, but Windows cannot access them via localhost or the WSL IP address. This is due to WSL2 network isolation.

## Root Cause
1. Docker is running natively in WSL2 (not Docker Desktop)
2. WSL2 uses a virtualized network that is isolated from Windows
3. Mirrored networking mode requires a Windows restart to take effect
4. Windows Firewall is blocking direct connections to WSL2 IP addresses

## Solution: Port Forwarding

### Quick Fix (Immediate Access)

Run the port forwarding script as Administrator:
```powershell
.\fix-localhost.ps1
```

This will:
1. Get the current WSL2 IP address
2. Set up Windows port proxy rules to forward localhost → WSL2
3. Configure Windows Firewall to allow the ports
4. Test the connection and open the browser

### What Gets Configured

**Port Forwarding Rules:**
- Port 3000 → WSL UI (Next.js)
- Port 8000 → WSL API (FastAPI)
- Port 8001 → WSL Metrics  
- Port 15432 → WSL PostgreSQL

**Firewall Rules:**
- Allow inbound TCP on ports 3000, 8000, 8001, 15432

### Verification

After running the script, test access:
```powershell
# Test UI
Invoke-WebRequest -Uri "http://localhost:3000/" -UseBasicParsing

# Test API
Invoke-WebRequest -Uri "http://localhost:8000/api/health/live" -UseBasicParsing
```

Or simply open in browser:
- UI: http://localhost:3000
- API Docs: http://localhost:8000/docs

## Long-Term Solution: Mirrored Networking

### Option 1: Windows Restart (Recommended)
The `.wslconfig` file has already been created with mirrored networking mode:
```
C:\Users\syed.shareef\.wslconfig
```

**Simply restart Windows** and mirrored networking will be enabled permanently. This eliminates the need to run port forwarding scripts.

### Option 2: Use Docker Desktop
Install Docker Desktop for Windows, which handles WSL2 networking automatically without requiring port forwarding or mirrored mode.

## Troubleshooting

### Port Forwarding Not Working

1. **Check if script ran successfully:**
   ```powershell
   netsh interface portproxy show v4tov4
   ```
   Should show all 4 port forwarding rules.

2. **Check firewall rules:**
   ```powershell
   Get-NetFirewallRule -DisplayName "RCA Engine*" | Select-Object DisplayName, Enabled
   ```

3. **Verify containers are running:**
   ```powershell
   wsl bash -c "docker compose -f deploy/docker/docker-compose.yml ps"
   ```
   All should show "healthy" status.

### WSL IP Changed

If you restart WSL2, the IP address may change. Re-run the fix script:
```powershell
.\fix-localhost.ps1
```

### Still Can't Connect

1. **Test from within WSL (should work):**
   ```powershell
   wsl bash -c "curl http://localhost:3000"
   ```

2. **Check Windows can ping WSL:**
   ```powershell
   $wslIP = (wsl hostname -I).Split()[0]
   Test-Connection -ComputerName $wslIP -Count 2
   ```

3. **Restart Docker containers:**
   ```powershell
   wsl bash -c "cd /mnt/c/Users/syed.shareef/.vscode/repos/RCA\ -\ v7/RCA-Final && docker compose -f deploy/docker/docker-compose.yml restart"
   ```

4. **Check Docker logs for errors:**
   ```powershell
   wsl bash -c "docker compose -f deploy/docker/docker-compose.yml logs --tail=50"
   ```

## Manual Port Forwarding

If the script doesn't work, manually run these commands in an **Administrator PowerShell**:

```powershell
# Get WSL IP
$wslIP = (wsl hostname -I).Split()[0].Trim()

# Add port forwarding
netsh interface portproxy add v4tov4 listenport=3000 listenaddress=0.0.0.0 connectport=3000 connectaddress=$wslIP
netsh interface portproxy add v4tov4 listenport=8000 listenaddress=0.0.0.0 connectport=8000 connectaddress=$wslIP
netsh interface portproxy add v4tov4 listenport=8001 listenaddress=0.0.0.0 connectport=8001 connectaddress=$wslIP
netsh interface portproxy add v4tov4 listenport=15432 listenaddress=0.0.0.0 connectport=15432 connectaddress=$wslIP

# Add firewall rules
netsh advfirewall firewall add rule name="RCA Engine UI" dir=in action=allow protocol=TCP localport=3000
netsh advfirewall firewall add rule name="RCA Engine API" dir=in action=allow protocol=TCP localport=8000
netsh advfirewall firewall add rule name="RCA Engine Metrics" dir=in action=allow protocol=TCP localport=8001
netsh advfirewall firewall add rule name="RCA Engine DB" dir=in action=allow protocol=TCP localport=15432
```

## Remove Port Forwarding

To remove the port forwarding rules (if switching to Docker Desktop or mirrored mode):

```powershell
# Remove port proxies
netsh interface portproxy delete v4tov4 listenport=3000 listenaddress=0.0.0.0
netsh interface portproxy delete v4tov4 listenport=8000 listenaddress=0.0.0.0
netsh interface portproxy delete v4tov4 listenport=8001 listenaddress=0.0.0.0
netsh interface portproxy delete v4tov4 listenport=15432 listenaddress=0.0.0.0

# Remove firewall rules
netsh advfirewall firewall delete rule name="RCA Engine UI"
netsh advfirewall firewall delete rule name="RCA Engine API"
netsh advfirewall firewall delete rule name="RCA Engine Metrics"
netsh advfirewall firewall delete rule name="RCA Engine DB"
```

## Files Created

- `fix-localhost.ps1` - Launcher script (run this one)
- `setup-ports-admin.ps1` - Admin script that does the actual work
- `fix-ports.bat` - Batch file alternative
- `TROUBLESHOOTING_ACCESS.md` - This file

## Summary

**Immediate Fix:** Run `.\fix-localhost.ps1` as Administrator

**Permanent Fix:** Restart Windows (mirrored networking already configured)

**Access URLs:** 
- http://localhost:3000 (UI)
- http://localhost:8000 (API)
- http://localhost:8000/docs (API Documentation)
