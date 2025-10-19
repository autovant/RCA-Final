# RCA Engine - Access Information

## Status: ✅ ALL SERVICES HEALTHY

Your RCA Engine Docker deployment is fully operational!

## Access URLs

### After Windows Restart (Recommended)
Once you restart Windows, the WSL2 mirrored networking will be active:
- UI:       http://localhost:3000
- API:      http://localhost:8000
- API Docs: http://localhost:8000/docs
- Database: localhost:15432

### Immediate Access (Before Restart)
Access via your LAN IP address from WSL2:
- UI:       http://192.168.0.117:3000
- API:      http://192.168.0.117:8000
- API Docs: http://192.168.0.117:8000/docs

**Note**: Replace `192.168.0.117` with the current WSL IP if it changes.
To get current IP: `wsl hostname -I | %{$_.Split()[0]}`

## What Was Fixed

1. ✅ **WSL2 Networking**: Configured mirrored networking mode in `.wslconfig`
2. ✅ **Port Conflict**: Changed PostgreSQL from port 5432 → 15432 (Windows PostgreSQL using 5432)
3. ✅ **Old Containers**: Removed conflicting old Docker containers
4. ✅ **All Services**: rca_core, rca_ui, rca_db, rca_redis all healthy

## Why Restart is Needed

The `.wslconfig` file was created with mirrored networking mode:
```
[wsl2]
networkingMode=mirrored
```

This makes WSL2 ports accessible via Windows localhost, but requires a Windows restart to take effect.

## Alternative: Port Forwarding (If You Can't Restart)

Run PowerShell as Administrator and execute:
```powershell
.\fix-wsl-port-forwarding.ps1
```

This will set up temporary port forwarding from Windows to WSL2.

## Container Management

Start containers:
```powershell
wsl bash -c "cd /mnt/c/Users/syed.shareef/.vscode/repos/RCA\ -\ v7/RCA-Final && docker compose -f deploy/docker/docker-compose.yml up -d"
```

Stop containers:
```powershell
wsl bash -c "cd /mnt/c/Users/syed.shareef/.vscode/repos/RCA\ -\ v7/RCA-Final && docker compose -f deploy/docker/docker-compose.yml down"
```

Check status:
```powershell
wsl bash -c "cd /mnt/c/Users/syed.shareef/.vscode/repos/RCA\ -\ v7/RCA-Final && docker compose -f deploy/docker/docker-compose.yml ps"
```

## Verification

Test from PowerShell (after restart or using LAN IP):
```powershell
# Test API
Invoke-WebRequest -Uri "http://localhost:8000/api/health/live" -UseBasicParsing

# Test UI
Invoke-WebRequest -Uri "http://localhost:3000/" -UseBasicParsing
```

## Files Created

- `C:\Users\syed.shareef\.wslconfig` - WSL2 mirrored networking configuration
- `fix-wsl-port-forwarding.ps1` - Port forwarding script (run as admin if needed)
- `WSL_NETWORKING_FIX.md` - Detailed networking solutions guide
- `ACCESS_INFO.md` - This file

## Support

If you have issues after restart:
1. Check containers are running: See "Container Management" above
2. Verify WSL IP hasn't changed: `wsl hostname -I`
3. Check Windows Firewall isn't blocking ports 3000, 8000
4. Review logs: `wsl bash -c "docker compose -f deploy/docker/docker-compose.yml logs"`
