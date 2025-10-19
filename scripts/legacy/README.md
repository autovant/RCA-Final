# Legacy Scripts

This folder contains **27 scripts** that were superseded by the simplified workflow in the root directory.

## Why These Were Archived

These scripts represent various experiments, alternative approaches, and platform-specific solutions developed over time. They've been replaced by a consolidated set of 8 scripts in the root that cover all use cases more cleanly.

## Categories

### Startup Variations (13 scripts)
Experiments with different startup approaches before settling on the current workflow:

- `quick-start-demo.ps1` - Similar to current quick-start-dev.ps1
- `quick-start.ps1` - Older version
- `Start-Docker.ps1` - Docker-only startup
- `Start-RCA.ps1` - RCA-specific launcher
- `start-app.ps1` - Application starter
- `start-environment.ps1` - Complex environment orchestration (17KB)
- `START-ALL-STABLE.ps1` - "Stable" version
- `START-BACKEND-HOST-NETWORK.ps1` - Host network mode experiment
- `start-local-hybrid.ps1` - Hybrid Windows/Docker approach (12KB)
- `start-local-hybrid-alt-port.ps1` - Port variation
- `start-local-hybrid-complete.ps1` - Full hybrid setup (18KB)
- `start-local-windows.ps1` - Native Windows approach (20KB)
- `start-databases-wsl-ip.ps1` - WSL IP-specific startup
- `start-ui-bg.ps1` - Background UI startup

**Current replacement**: `quick-start-dev.ps1` or `START-SIMPLE.ps1`

### Stop Scripts (3 scripts)
- `Stop-Docker.ps1`
- `stop-local-hybrid.ps1`
- `stop-local-windows.ps1`

**Current replacement**: `stop-dev.ps1` or `STOP-SIMPLE.ps1`

### Setup Variations (6 scripts)
- `setup-local-windows.ps1` (20KB native setup)
- `setup-local-hybrid.ps1` (hybrid setup)
- `setup-network-access.ps1` (older firewall setup)
- `setup-ports-admin.ps1` (port-specific)
- `setup-port-8001.ps1` (single port)
- `setup-network.bat` (batch version)

**Current replacement**: `setup-dev-environment.ps1` + `ENABLE-NETWORK-ACCESS.ps1`

### Restart Scripts (1 script)
- `restart-backend-only.ps1`

**Current replacement**: `restart-backend.ps1`

### Batch Files (4 files)
- `quick-start-backend.bat`
- `start-backend-only.bat`
- `start-backend-simple.bat`
- `start-ui-windows.bat`

**Current replacement**: PowerShell equivalents in root

## When to Use These Scripts

**Short answer: You shouldn't need to.**

The current workflow handles all scenarios these scripts addressed. However, they're preserved here for:

1. **Historical reference** - Understanding past approaches
2. **Troubleshooting** - If the current scripts fail, these show alternative methods
3. **Migration guidance** - If moving from an old setup

## Migration from Legacy Scripts

If you were using any of these scripts:

| **Old Script** | **New Script** | **Notes** |
|----------------|----------------|-----------|
| `Start-RCA.ps1` | `quick-start-dev.ps1` | Consolidated workflow |
| `start-local-windows.ps1` | `quick-start-dev.ps1` | Simplified 20KB → 7KB |
| `start-environment.ps1` | `quick-start-dev.ps1` | More reliable |
| `setup-local-windows.ps1` | `setup-dev-environment.ps1` | Cleaner setup |
| `Stop-Docker.ps1` | `stop-dev.ps1` | Matches new startup |

## Need Help?

Refer to:
- [`docs/getting-started/quickstart.md`](../../docs/getting-started/quickstart.md) - Current workflow
- [`docs/operations/startup-scripts.md`](../../docs/operations/startup-scripts.md) - Script reference
- [`docs/operations/troubleshooting.md`](../../docs/operations/troubleshooting.md) - Common issues

---

*Scripts archived October 17, 2025 as part of repository cleanup*
