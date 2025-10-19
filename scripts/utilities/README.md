# Utility Scripts

This folder contains **6 helper scripts** for specific administrative and maintenance tasks.

## When to Use These Scripts

These utilities are for specific scenarios outside the normal development workflow. Most users won't need them.

## Scripts

### Database Management

#### `create-database.ps1`
**Purpose**: Manually create the PostgreSQL database outside Docker  
**When to use**: Setting up a standalone Postgres instance (not recommended - use Docker)  
**Alternative**: Let `setup-dev-environment.ps1` handle database setup via Docker

#### `install-postgres-redis-direct.ps1`
**Purpose**: Install Postgres and Redis natively on Windows (not via Docker)  
**When to use**: Running without Docker/WSL (not recommended)  
**Alternative**: Use Docker Compose for consistency

### Browser & UI Helpers

#### `open-rca.ps1`
**Purpose**: Open the RCA UI in default browser  
**When to use**: Quick launch to http://localhost:3000  
**Alternative**: Just open browser manually or use `-NoBrowser` flag with startup scripts

### Status & Monitoring

#### `status-local-windows.ps1`
**Purpose**: Check status of services running natively on Windows  
**When to use**: When running backend/UI directly on Windows (legacy setup)  
**Alternative**: `docker ps` for Docker-based setup

#### `verify-port-config.ps1`
**Purpose**: Verify port configuration is correct  
**When to use**: Debugging port conflicts or misconfiguration  
**Alternative**: `netstat -ano | findstr "8000 3000 15432"`

### Testing

#### `test-integration.ps1`
**Purpose**: Run integration tests  
**When to use**: Validating the full stack after changes  
**Alternative**: `python -m pytest tests/integration/`

## Usage Examples

### Quick Database Setup (Not Recommended)
```powershell
# Only if you can't use Docker
.\scripts\utilities\create-database.ps1
```
**Better**: Use `quick-start-dev.ps1` which starts Postgres in Docker

### Check Port Configuration
```powershell
# Verify ports are configured correctly
.\scripts\utilities\verify-port-config.ps1
```

### Open UI Quickly
```powershell
# Launch browser to RCA UI
.\scripts\utilities\open-rca.ps1
```
**Equivalent**: `Start-Process "http://localhost:3000"`

### Run Integration Tests
```powershell
# Run full integration test suite
.\scripts\utilities\test-integration.ps1
```
**Better**: Use pytest directly for more control

## Recommendations

| Task | Script | Better Alternative |
|------|--------|-------------------|
| Database setup | `create-database.ps1` | Use Docker via `quick-start-dev.ps1` |
| Install services | `install-postgres-redis-direct.ps1` | Use Docker Compose |
| Open UI | `open-rca.ps1` | Open browser manually |
| Check status | `status-local-windows.ps1` | `docker ps` or `wsl bash -c "docker ps"` |
| Verify ports | `verify-port-config.ps1` | `netstat -ano | findstr "PORT"` |
| Run tests | `test-integration.ps1` | `python -m pytest tests/` |

## Why These Are "Utilities"

These scripts were created for specific edge cases or legacy workflows. With the current Docker-based setup, most of these tasks are handled automatically or more easily via standard commands.

**Keep them for**:
- Historical reference
- Emergency recovery scenarios
- Non-Docker setups (not recommended)
- Quick helpers when needed

## Need Help?

For normal development workflow, see:
- [`docs/getting-started/quickstart.md`](../../docs/getting-started/quickstart.md)
- [`docs/getting-started/dev-setup.md`](../../docs/getting-started/dev-setup.md)

---

*Organized October 17, 2025 as part of script consolidation*
