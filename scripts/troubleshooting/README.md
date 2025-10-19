# Troubleshooting Scripts

This folder contains **16 scripts** that were created to fix specific issues encountered during development. These are **diagnostic and repair utilities** for when things go wrong.

## When to Use These Scripts

Most issues should now be handled by the consolidated workflow (`quick-start-dev.ps1` + `stop-dev.ps1`) and the guidance in [`docs/operations/troubleshooting.md`](../../docs/operations/troubleshooting.md).

Use these scripts when:
- Standard startup fails with port/networking errors
- Firewall rules need manual adjustment
- WSL port forwarding breaks
- Docker networking needs reset
- Debugging specific connectivity issues

## Categories

### Port & Forwarding Fixes (9 scripts)
Scripts that address port conflicts and forwarding issues:

- `fix-docker-port-forwarding.ps1` - Reset Docker port forwarding
- `fix-port-8001.ps1` - Fix port 8001 conflicts
- `fix-wsl-port-forwarding.ps1` - Repair WSL forwarding
- `update-port-8001.ps1` - Update port 8001 configuration
- `update-port-forwarding-8001.ps1` - Update 8001 forwarding
- `cleanup-port-forwarding-hybrid.ps1` - Clean hybrid port rules
- `add-firewall-rule-8001.ps1` - Add firewall exception for 8001
- `fix-ports.bat` - Batch port fixer
- `cleanup-network.bat` - Network cleanup utility

**When needed**: Port conflicts, "address already in use" errors

### Firewall & Networking Fixes (5 scripts)
Scripts for firewall and WSL networking issues:

- `fix-firewall-wsl-mirrored.ps1` - Fix WSL mirrored networking firewall
- `FIX-FIREWALL-WSL.ps1` - General WSL firewall fix
- `fix-wsl-networking.ps1` - Repair WSL network stack
- `fix-localhost.ps1` - Fix localhost resolution
- `ENABLE-WSL-MIRRORED-NETWORKING.ps1` - Enable WSL mirrored mode (specific to WSL config)

**When needed**: Cannot connect to localhost, WSL networking broken, firewall blocking

### Test & Diagnostic Scripts (2 scripts)
- `TEST-FIREWALL-DISABLE.ps1` - Test with firewall disabled (diagnostic only)
- `TEST-NETWORK.ps1` - Network connectivity test

**When needed**: Diagnosing connectivity issues

## Common Scenarios

### Scenario 1: "Port 8000 already in use"
```powershell
# Option 1: Use stop script first
.\stop-dev.ps1

# Option 2: If that fails, use port fix
.\scripts\troubleshooting\fix-ports.bat
```

### Scenario 2: "Cannot connect to localhost:8000"
```powershell
# Check if it's a firewall issue
.\scripts\troubleshooting\TEST-NETWORK.ps1

# If firewall is the problem
.\ENABLE-NETWORK-ACCESS.ps1  # (in root)

# If WSL networking is broken
.\scripts\troubleshooting\fix-wsl-networking.ps1
```

### Scenario 3: "Docker networking not working"
```powershell
# Reset Docker port forwarding
.\scripts\troubleshooting\fix-docker-port-forwarding.ps1

# Clean up stale network rules
.\scripts\troubleshooting\cleanup-network.bat
```

### Scenario 4: WSL Mirrored Networking Issues
```powershell
# If using WSL mirrored networking mode
.\scripts\troubleshooting\ENABLE-WSL-MIRRORED-NETWORKING.ps1
.\scripts\troubleshooting\fix-firewall-wsl-mirrored.ps1
```

## Best Practice

**Try the standard workflow first**:
1. Run `stop-dev.ps1` to clean up
2. Run `quick-start-dev.ps1` to restart
3. Check [`docs/operations/troubleshooting.md`](../../docs/operations/troubleshooting.md)
4. **Only then** use these specialized scripts

## Script Descriptions

| Script | Purpose | Risk Level |
|--------|---------|------------|
| `fix-docker-port-forwarding.ps1` | Reset Docker port rules | Low |
| `fix-wsl-port-forwarding.ps1` | Reset WSL port rules | Low |
| `cleanup-port-forwarding-hybrid.ps1` | Remove old hybrid rules | Low |
| `cleanup-network.bat` | Clean network config | Low |
| `fix-firewall-wsl-mirrored.ps1` | Fix WSL firewall | **Medium** - modifies firewall |
| `FIX-FIREWALL-WSL.ps1` | General firewall fix | **Medium** - modifies firewall |
| `TEST-FIREWALL-DISABLE.ps1` | Disable firewall temporarily | **High** - security risk |
| `ENABLE-WSL-MIRRORED-NETWORKING.ps1` | Enable mirrored mode | **Medium** - changes WSL config |

## Need Help?

If these scripts don't solve your issue:
1. Check [`docs/operations/troubleshooting.md`](../../docs/operations/troubleshooting.md)
2. Review Docker logs: `wsl bash -c "docker logs rca_core"`
3. Verify WSL is running: `wsl --list --verbose`
4. Restart Docker Desktop

---

*Archived October 17, 2025 - These scripts address historical issues and should rarely be needed with the current workflow*
