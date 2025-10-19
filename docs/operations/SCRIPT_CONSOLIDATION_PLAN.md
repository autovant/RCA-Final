# Script Consolidation Plan

## Problem
58 scripts in root directory (51 `.ps1` + 7 `.bat`) - excessive and confusing.

## Active Scripts (Keep in Root)

These 6 scripts are referenced in the new documentation and form the core workflow:

### Primary Workflow
1. **setup-dev-environment.ps1** - One-time bootstrap (creates venv, installs deps)
2. **quick-start-dev.ps1** - Daily dev startup (DB, API, UI, worker, Copilot proxy)
3. **start-dev.ps1** - Manual startup (just DB containers)
4. **stop-dev.ps1** - Shutdown dev services

### Demo/Presentation
5. **START-SIMPLE.ps1** - One-button demo startup
6. **STOP-SIMPLE.ps1** - One-button demo shutdown

### Firewall (One-Time)
7. **ENABLE-NETWORK-ACCESS.ps1** - Windows firewall rules (run once as admin)

### Restart Utilities (Optional - Keep 1)
8. **restart-backend.ps1** - Quick backend restart

**Total: 8 scripts** (reduced from 58)

---

## Scripts to Relocate

### → `scripts/legacy/` (Superseded Startup Scripts - 13 files)

These were experiments or alternative approaches now replaced by the active scripts:

**Startup Variations:**
- quick-start-demo.ps1 (similar to quick-start-dev.ps1)
- quick-start.ps1 (older version)
- Start-Docker.ps1 (superseded by START-SIMPLE.ps1)
- start-app.ps1 (redundant)
- start-environment.ps1 (complex, superseded)
- START-ALL-STABLE.ps1 (older approach)
- START-BACKEND-HOST-NETWORK.ps1 (networking experiment)
- start-local-hybrid.ps1 (hybrid approach, superseded)
- start-local-hybrid-alt-port.ps1 (port variation)
- start-local-hybrid-complete.ps1 (20KB monster)
- start-local-windows.ps1 (20KB native Windows approach)
- start-databases-wsl-ip.ps1 (specific to WSL IP workaround)
- start-ui-bg.ps1 (use quick-start-dev.ps1 instead)

**Stop Variations:**
- Stop-Docker.ps1 (use stop-dev.ps1)
- stop-local-hybrid.ps1 (matches start-local-hybrid)
- stop-local-windows.ps1 (matches start-local-windows)

**Setup Variations:**
- setup-local-windows.ps1 (20KB, superseded by setup-dev-environment.ps1)
- setup-local-hybrid.ps1 (hybrid setup, superseded)
- setup-network-access.ps1 (older version of ENABLE-NETWORK-ACCESS.ps1)
- setup-ports-admin.ps1 (port-specific setup)
- setup-port-8001.ps1 (port-specific)

**Restart:**
- restart-backend-only.ps1 (keep restart-backend.ps1)

**Batch Files:**
- quick-start-backend.bat (use quick-start-dev.ps1)
- setup-network.bat (use ENABLE-NETWORK-ACCESS.ps1)
- start-backend-only.bat (use start-dev.ps1)
- start-backend-simple.bat (use start-dev.ps1)
- start-ui-windows.bat (use quick-start-dev.ps1)

**Total: ~26 files**

---

### → `scripts/troubleshooting/` (Fix & Diagnostic Scripts - 16 files)

One-off fixes and troubleshooting utilities that addressed specific issues:

**Port/Forwarding Fixes:**
- fix-docker-port-forwarding.ps1
- fix-port-8001.ps1
- fix-wsl-port-forwarding.ps1
- update-port-8001.ps1
- update-port-forwarding-8001.ps1
- cleanup-port-forwarding-hybrid.ps1
- add-firewall-rule-8001.ps1
- fix-ports.bat
- cleanup-network.bat

**Firewall/Networking Fixes:**
- fix-firewall-wsl-mirrored.ps1
- FIX-FIREWALL-WSL.ps1
- fix-wsl-networking.ps1
- fix-localhost.ps1
- ENABLE-WSL-MIRRORED-NETWORKING.ps1 (specific to mirrored mode)

**Test Scripts:**
- TEST-FIREWALL-DISABLE.ps1
- TEST-NETWORK.ps1

**Total: ~16 files**

---

### → `scripts/utilities/` (Utility Scripts - 8 files)

Support utilities for specific tasks:

- create-database.ps1 (manual DB setup)
- install-postgres-redis-direct.ps1 (direct install, not via Docker)
- open-rca.ps1 (browser opener)
- status-local-windows.ps1 (status checker)
- test-integration.ps1 (integration tests - or move to tests/)
- verify-port-config.ps1 (port verification)

**Total: ~6 files**

---

## Execution Plan

### Phase 1: Create Script Inventory Document
Document all scripts with purpose and recommendation.

### Phase 2: Move Scripts
```powershell
# Legacy startup/stop/setup
Move-Item -Path @(
  'quick-start-demo.ps1',
  'quick-start.ps1',
  'Start-Docker.ps1',
  'start-app.ps1',
  'start-environment.ps1',
  'START-ALL-STABLE.ps1',
  'START-BACKEND-HOST-NETWORK.ps1',
  'start-local-hybrid.ps1',
  'start-local-hybrid-alt-port.ps1',
  'start-local-hybrid-complete.ps1',
  'start-local-windows.ps1',
  'start-databases-wsl-ip.ps1',
  'start-ui-bg.ps1',
  'Stop-Docker.ps1',
  'stop-local-hybrid.ps1',
  'stop-local-windows.ps1',
  'setup-local-windows.ps1',
  'setup-local-hybrid.ps1',
  'setup-network-access.ps1',
  'setup-ports-admin.ps1',
  'setup-port-8001.ps1',
  'restart-backend-only.ps1',
  'quick-start-backend.bat',
  'setup-network.bat',
  'start-backend-only.bat',
  'start-backend-simple.bat',
  'start-ui-windows.bat'
) -Destination '.\scripts\legacy\'

# Troubleshooting scripts
Move-Item -Path @(
  'fix-docker-port-forwarding.ps1',
  'fix-firewall-wsl-mirrored.ps1',
  'FIX-FIREWALL-WSL.ps1',
  'fix-localhost.ps1',
  'fix-port-8001.ps1',
  'fix-wsl-networking.ps1',
  'fix-wsl-port-forwarding.ps1',
  'fix-ports.bat',
  'cleanup-port-forwarding-hybrid.ps1',
  'cleanup-network.bat',
  'add-firewall-rule-8001.ps1',
  'update-port-8001.ps1',
  'update-port-forwarding-8001.ps1',
  'ENABLE-WSL-MIRRORED-NETWORKING.ps1',
  'TEST-FIREWALL-DISABLE.ps1',
  'TEST-NETWORK.ps1'
) -Destination '.\scripts\troubleshooting\'

# Utility scripts
Move-Item -Path @(
  'create-database.ps1',
  'install-postgres-redis-direct.ps1',
  'open-rca.ps1',
  'status-local-windows.ps1',
  'test-integration.ps1',
  'verify-port-config.ps1'
) -Destination '.\scripts\utilities\'
```

### Phase 3: Update Documentation
Update `docs/operations/startup-scripts.md` to reflect the simplified structure.

### Phase 4: Create README in Each Scripts Folder
Explain what each category contains and when to use them.

---

## Final Root Directory Structure

```
Root/
├── setup-dev-environment.ps1    # One-time setup
├── quick-start-dev.ps1           # Daily dev startup
├── start-dev.ps1                 # Manual DB startup
├── stop-dev.ps1                  # Shutdown
├── START-SIMPLE.ps1              # Demo startup
├── STOP-SIMPLE.ps1               # Demo shutdown
├── ENABLE-NETWORK-ACCESS.ps1    # Firewall (one-time)
├── restart-backend.ps1           # Quick restart
└── scripts/
    ├── legacy/                   # 26 old scripts
    ├── troubleshooting/          # 16 fix scripts
    └── utilities/                # 6 helper scripts
```

**Root scripts reduced from 58 to 8 (86% reduction)**

---

## Benefits

1. **Clarity** - New users see only 8 relevant scripts
2. **Discoverability** - Clear naming shows the workflow
3. **Maintainability** - Related scripts grouped together
4. **Documentation alignment** - Root scripts match what's documented
5. **History preserved** - Nothing deleted, just organized

---

## Recommendation

**Execute this plan now** to drastically simplify the repository structure while preserving all historical scripts for reference.
