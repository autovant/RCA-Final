# Documentation Archive

Legacy notes, fix logs, and historical reports have been relocated here to declutter the active documentation set. Nothing has been deleted—refer back to these files whenever you need a paper trail of past incidents or investigations.

## 📚 Consolidated History Documents (Start Here)

**These comprehensive documents consolidate multiple related files for easier reference:**

1. **[HISTORICAL_NOTES.md](HISTORICAL_NOTES.md)** ⭐ 
   - **Complete categorized index** of all **86 archive documents**
   - Organized by topic: Deployment, Networking, Database, Features, Testing, Demo/Showcase, UI/UX, etc.
   - Includes consolidation summary and duplicate tracking
   - **Recently updated** (Oct 2025) with 16 new completion reports and status files

2. **[DEPLOYMENT_HISTORY.md](DEPLOYMENT_HISTORY.md)**
   - Complete deployment timeline and milestones
   - Performance optimizations (Oct 23, 2025)
   - WSL architecture and hybrid deployment
   - Database isolation and environment setup
   - Consolidates: `DEPLOYMENT_COMPLETE.md`, `DEPLOYMENT-COMPLETE.md`, `DEPLOYMENT_STATUS_FINAL.md`

3. **[WSL_NETWORKING_HISTORY.md](WSL_NETWORKING_HISTORY.md)**
   - Complete WSL 2 networking guide
   - NAT mode vs mirrored networking
   - Port forwarding setup and troubleshooting
   - Network topology diagrams
   - Consolidates: `WSL_NETWORKING_RESOLVED.md`, `WSL_NETWORKING_FIX.md`, `WSL_NETWORKING_SOLUTION.md`, `FIX_PORT_FORWARDING_NOW.md`, `WSL_PORT_FORWARDING_FIX_REQUIRED.md`

4. **[PORT_CONFIGURATION_HISTORY.md](PORT_CONFIGURATION_HISTORY.md)**
   - Port configuration issues and resolutions
   - Port 8000/8001/8002 changes
   - WinError 10013 solutions
   - Port selection guidelines
   - Consolidates: `PORT_8001_FIX_SUMMARY.md`, `QUICK_FIX_PORT_8001.md`, `FIX_PORT_8001_ERROR.md`, `PORT_CHANGE_8001.md`

**Archive Reduction**: 19 duplicate files consolidated into 3 comprehensive history documents (October 2025)

---

## Categories

- **Fix Logs & Incident Write-ups** – Files containing "FIX", "RESOLVED", "SUMMARY", or dated notes (e.g. `BACKEND_ROUTING_RESOLVED.md`, `DATABASE_CONNECTION_FIXED.md`).
- **Legacy Setup Guides** – Superseded instructions such as `DEV_SETUP_SIMPLIFIED.md`, `DOCKER_DEPLOYMENT_GUIDE.md`, and `RUN_UI_IN_WINDOWS.md`.
- **Operational Diaries** – Implementation status updates, feature completion reports, and end-to-end test reports.
- **Platform Experiments** – Documents covering specific environment attempts (WSL networking, hybrid startup flows, firewall workarounds).

---

## Current Documentation (Up-to-Date)

The latest, maintained documentation now lives in:

- [`docs/index.md`](../index.md) – Complete documentation index
- [`docs/getting-started/`](../getting-started/) – Quickstart & dev setup guides
- [`docs/deployment/`](../deployment/) – Production deployment guide
- [`docs/operations/`](../operations/) – Scripts and troubleshooting playbooks
- [`docs/reference/`](../reference/) – Features, architecture, API docs
- [`docs/diagrams/`](../diagrams/) – Mermaid architecture and flow diagrams
- [`scripts/README.md`](../../scripts/README.md) – All utility scripts documented

---

## Usage Guidelines

**When to reference archive documents:**
- Understanding historical context for current issues
- Researching previously resolved problems
- Onboarding new developers (see deployment/networking history)
- Documenting lessons learned

**If you find a document here that should be maintained going forward:**
1. Move it back into the appropriate `docs/` section
2. Update the content to reflect current state
3. Link it from `docs/index.md`
4. Remove outdated information

**Before creating new documentation:**
- Check if a similar issue is documented here
- Reference archive documents for context
- Avoid duplicating content—link to archive instead
