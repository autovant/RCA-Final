# Startup & Helper Scripts

The repository has been cleaned up from **58 scripts** down to **8 essential scripts** in the root directory.

## Active Scripts (Root Directory)

These are the only scripts you need for daily development:

### Primary Development Workflow

| Script | Purpose | Usage |
|--------|---------|-------|
| `setup-dev-environment.ps1` | **One-time setup** - Creates venv, installs dependencies, prepares Docker volumes | Run once after cloning: `.\setup-dev-environment.ps1` |
| `quick-start-dev.ps1` | **Daily dev startup** - Launches DB, backend (hot reload), UI, optional worker & Copilot proxy in dedicated terminals | `.\quick-start-dev.ps1` <br> Add `-IncludeWorker`, `-NoWorker`, or `-NoBrowser` |
| `start-dev.ps1` | **Manual startup** - Starts only database containers, prints commands for manual backend/UI launch | Use when you want full control: `.\start-dev.ps1` |
| `stop-dev.ps1` | **Shutdown** - Stops all development services | `.\stop-dev.ps1` |

### Demo/Presentation Mode

| Script | Purpose | Usage |
|--------|---------|-------|
| `START-SIMPLE.ps1` | **One-button demo** - Fast startup for client demos | `.\START-SIMPLE.ps1` |
| `STOP-SIMPLE.ps1` | **Demo shutdown** - Stops demo services | `.\STOP-SIMPLE.ps1` |

### One-Time Setup

| Script | Purpose | Usage |
|--------|---------|-------|
| `ENABLE-NETWORK-ACCESS.ps1` | **Firewall rules** - Adds Windows Firewall exceptions for ports 3000, 8000, 15432, etc. | Run once as Administrator: `.\ENABLE-NETWORK-ACCESS.ps1` |

### Quick Restart

| Script | Purpose | Usage |
|--------|---------|-------|
| `restart-backend.ps1` | **Backend restart** - Quickly cycle the API without touching other services | `.\restart-backend.ps1` |

## Workflow Examples

### First-Time Setup
```powershell
# 1. One-time setup
.\setup-dev-environment.ps1

# 2. Enable firewall (run as Administrator)
.\ENABLE-NETWORK-ACCESS.ps1
```

### Daily Development
```powershell
# Start everything
.\quick-start-dev.ps1

# Work on your code...

# Shutdown
.\stop-dev.ps1
```

### Manual Control (Advanced)
```powershell
# Start only database
.\start-dev.ps1

# In separate terminals:
.\venv\Scripts\activate
python -m uvicorn apps.api.main:app --host 0.0.0.0 --port 8000 --reload

cd ui
npm run dev

# Shutdown
.\stop-dev.ps1
```

### Quick Demo
```powershell
# For presentations/client demos
.\START-SIMPLE.ps1

# When done
.\STOP-SIMPLE.ps1
```

## Archived Scripts

The following script categories have been moved to organized folders:

### `scripts/legacy/` (28 files)
Legacy startup, stop, and setup scripts superseded by the 8 active scripts above:
- Alternative startup approaches (`start-environment.ps1`, `Start-RCA.ps1`, etc.)
- Platform-specific setups (`start-local-windows.ps1`, `start-local-hybrid.ps1`)
- Old batch files (`quick-start-backend.bat`, `start-backend-only.bat`)

See [`scripts/legacy/README.md`](../../scripts/legacy/README.md) for details.

### `scripts/troubleshooting/` (16 files)
Fix and diagnostic scripts for specific issues:
- Port fixes (`fix-port-8001.ps1`, `fix-wsl-port-forwarding.ps1`)
- Firewall repairs (`fix-firewall-wsl-mirrored.ps1`, `FIX-FIREWALL-WSL.ps1`)
- Network cleanup (`cleanup-network.bat`, `cleanup-port-forwarding-hybrid.ps1`)

See [`scripts/troubleshooting/README.md`](../../scripts/troubleshooting/README.md) for usage.

### `scripts/utilities/` (6 files)
Helper scripts for specific tasks:
- Database management (`create-database.ps1`, `install-postgres-redis-direct.ps1`)
- Status checking (`status-local-windows.ps1`, `verify-port-config.ps1`)
- Testing (`test-integration.ps1`)

See [`scripts/utilities/README.md`](../../scripts/utilities/README.md) for details.

## Script Consolidation Summary

**Before**: 58 scripts cluttering the root directory  
**After**: 8 essential scripts + 50 organized in `scripts/` folders

This cleanup ensures:
- ✅ Clear entry points for new developers
- ✅ Reduced confusion about which script to use
- ✅ Historical scripts preserved but organized
- ✅ Documentation aligned with actual workflow

For daily operations, **only use the 8 root scripts**. The archived scripts are for reference or special troubleshooting scenarios.
