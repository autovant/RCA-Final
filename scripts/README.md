# RCA Engine Scripts

This directory contains utility scripts for development, testing, validation, and operations.

## Directory Structure

```
scripts/
├── README.md (this file)
├── validation/     # Code validation and verification scripts
└── ops/            # Operational scripts (future)
```

## Root-Level Scripts (PowerShell)

These scripts live in the repository root for easy access:

### Development & Startup

#### `quick-start-dev.ps1`
**Purpose**: One-command startup for the entire development environment  
**Usage**:
```powershell
# Full startup (database, API, UI, worker, proxy)
.\quick-start-dev.ps1

# Skip worker
.\quick-start-dev.ps1 -NoWorker

# Skip browser auto-open
.\quick-start-dev.ps1 -NoBrowser

# Skip worker and browser
.\quick-start-dev.ps1 -NoWorker -NoBrowser
```

**What it does**:
1. Starts Docker containers via WSL (PostgreSQL, Redis)
2. Waits for database health check
3. Runs Alembic migrations
4. Starts FastAPI backend (with hot reload)
5. Starts Next.js UI development server
6. Optionally starts async worker
7. Optionally starts Copilot proxy server
8. Opens browser to http://localhost:3000

**When to use**: Daily development, quick demos, testing end-to-end workflows

---

#### `start-dev.ps1`
**Purpose**: Start only Docker services (database + Redis)  
**Usage**:
```powershell
.\start-dev.ps1
```

**What it does**:
- Executes `wsl.exe -e docker compose -f docker-compose.dev.yml up -d`
- Waits for containers to be healthy

**When to use**: When you want to manually start API/UI/worker separately

---

#### `stop-dev.ps1`
**Purpose**: Stop all development services  
**Usage**:
```powershell
.\stop-dev.ps1
```

**What it does**:
- Stops Docker containers
- Terminates any running FastAPI/Next.js processes
- Cleans up background jobs

**When to use**: End of development session, clean shutdown

---

#### `START-SIMPLE.ps1`
**Purpose**: Minimal startup (database only, no worker or proxy)  
**Usage**:
```powershell
.\START-SIMPLE.ps1
```

**When to use**: Lightweight testing, frontend-only development

---

#### `STOP-SIMPLE.ps1`
**Purpose**: Stop simple startup services  
**Usage**:
```powershell
.\STOP-SIMPLE.ps1
```

---

#### `setup-dev-environment.ps1`
**Purpose**: One-time setup of development environment  
**Usage**:
```powershell
# Full setup
.\setup-dev-environment.ps1

# Skip npm install (faster re-runs)
.\setup-dev-environment.ps1 -SkipNodeInstall
```

**What it does**:
1. Creates/refreshes Python virtual environment (`venv/`)
2. Installs Python dependencies (`requirements.txt`, `requirements.prod.txt`)
3. Installs UI dependencies (`cd ui && npm install`)
4. Seeds `.env` file from `.env.example` (if missing)
5. Creates Docker volumes for PostgreSQL and Redis

**When to use**: First-time setup, dependency updates, clean environment rebuild

---

### Deployment

#### `deploy.sh`
**Purpose**: Production deployment script (Linux/WSL)  
**Usage**:
```bash
./deploy.sh
```

**What it does**:
- Builds Docker images
- Runs database migrations
- Deploys containers
- Performs health checks

**When to use**: Production deployments (not for development)

---

#### `restart-backend.ps1`
**Purpose**: Quickly restart FastAPI backend (preserves database)  
**Usage**:
```powershell
.\restart-backend.ps1
```

**When to use**: After backend code changes (if hot reload not working)

---

### Networking & Troubleshooting

#### `ENABLE-NETWORK-ACCESS.ps1`
**Purpose**: Configure Windows firewall rules for WSL network access  
**Usage**:
```powershell
.\ENABLE-NETWORK-ACCESS.ps1
```

**What it does**:
- Adds firewall rules for Docker ports (15432, 16379, 8000, 3000)
- Configures WSL port forwarding
- Enables localhost access from Windows to WSL services

**When to use**: 
- First-time setup
- After Windows updates reset firewall rules
- If you can't access http://localhost:8000 from Windows browser

---

#### `start-backend-wsl.sh`, `start-backend-host-network.sh`
**Purpose**: Start backend with specific network configurations  
**Usage**: (Legacy scripts, prefer `quick-start-dev.ps1`)

---

## Validation Scripts (`scripts/validation/`)

These scripts verify code correctness and configuration:

### `check_class_end.py`
**Purpose**: Verify Python class definitions are properly closed  
**Usage**:
```bash
python scripts/validation/check_class_end.py <file.py>
```

**When to use**: Debugging syntax errors, validating generated code

---

### `check_fields_in_ast.py`
**Purpose**: Analyze Python AST for field definitions  
**Usage**:
```bash
python scripts/validation/check_fields_in_ast.py <file.py>
```

**When to use**: Inspecting Pydantic models, class structure validation

---

### `check_flags.py`
**Purpose**: Verify feature flag configurations  
**Usage**:
```bash
python scripts/validation/check_flags.py
```

**When to use**: Before enabling/disabling features, configuration audits

---

### `verify_flags.py`
**Purpose**: Comprehensive feature flag validation  
**Usage**:
```bash
python scripts/validation/verify_flags.py
```

**When to use**: Post-deployment verification, CI/CD pipelines

---

### `verify_integration.py`
**Purpose**: Verify integrated features work end-to-end  
**Usage**:
```bash
python scripts/validation/verify_integration.py
```

**When to use**: Integration testing, smoke tests after deployment

---

## Common Workflows

### Starting Fresh Development Session
```powershell
# Start everything
.\quick-start-dev.ps1

# Or start services separately
.\start-dev.ps1
.\venv\Scripts\activate
python -m uvicorn apps.api.main:app --host 0.0.0.0 --port 8000 --reload
cd ui && npm run dev
```

### Shutting Down
```powershell
.\stop-dev.ps1
```

### Resetting Database (⚠️ Loses all data)
```powershell
.\stop-dev.ps1
wsl.exe -e docker compose down -v
.\start-dev.ps1
alembic upgrade head
```

### Debugging Docker Issues
```powershell
# Check if Docker is running in WSL
wsl.exe -e docker ps

# View container logs
wsl.exe -e docker logs rca-final-postgres-1
wsl.exe -e docker logs rca-final-redis-1

# Restart Docker service in WSL
wsl.exe -e sudo service docker restart
```

### Running Validation Suite
```bash
# Activate venv
.\venv\Scripts\activate

# Run all validation scripts
python scripts/validation/check_flags.py
python scripts/validation/verify_flags.py
python scripts/validation/verify_integration.py

# Run unit tests
python -m pytest

# Run integration tests
python -m pytest tests/integration/

# Run smoke tests
python -m pytest tests/smoke/
```

## Adding New Scripts

### Naming Conventions
- **PowerShell scripts**: `kebab-case.ps1` or `UPPER-CASE.ps1`
- **Bash scripts**: `kebab-case.sh`
- **Python scripts**: `snake_case.py`

### Location Guidelines
- **Startup/dev scripts**: Repository root (for easy access)
- **Validation scripts**: `scripts/validation/`
- **Operational scripts**: `scripts/ops/` (create if needed)
- **Build scripts**: `scripts/build/` (create if needed)

### Documentation
When adding a new script:
1. Add usage instructions in this README
2. Include inline comments explaining complex logic
3. Add `--help` flag support if script has multiple options
4. Update `.gitignore` if script generates output files

## Related Documentation

- [Developer Setup Guide](../docs/getting-started/dev-setup.md)
- [Deployment Guide](../docs/deployment/deployment-guide.md)
- [Troubleshooting Playbook](../docs/operations/troubleshooting.md)
- [Deployment Topology Diagram](../docs/diagrams/deployment.md)
