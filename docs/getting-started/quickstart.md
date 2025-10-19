# Quickstart Checklist

Boot the entire RCA Engine stack locally in minutes. This guide assumes you are using Windows with PowerShell.

## First-Time Prep

1. Install prerequisites:
   - Python 3.11+
   - Node.js 18+
   - WSL 2 with Docker Engine (Docker Desktop or native daemon)
2. Clone the repository and copy environment defaults:
   ```powershell
   git clone https://github.com/<org>/RCA-Final.git
   cd RCA-Final
   copy .env.example .env
   ```
3. Run the one-time bootstrap script (creates the virtualenv, installs dependencies, prepares Docker volumes):
   ```powershell
   .\setup-dev-environment.ps1
   ```
4. Optional but recommended on managed networks – allow the local services through Windows Firewall:
   ```powershell
   .\ENABLE-NETWORK-ACCESS.ps1
   ```

## Daily Startup (Pick a Flow)

### Option A – All-in-one demo experience

```powershell
.\quick-start-dev.ps1
```

- Launches database containers, backend API (hot reload), Next.js UI, optional worker, and the Copilot proxy in dedicated terminals.
- Opens http://localhost:3000 automatically unless `-NoBrowser` is supplied.
- Add `-IncludeWorker` to process uploads immediately; use `-NoWorker` if you only need the UI/API for front-end work.

### Option B – Minimal client-facing demo

Designed for “press once, wait 30 seconds, everything just works.”

```powershell
.\START-SIMPLE.ps1
```

Pair with the first-time admin setup script if ports/firewall need alignment:
```powershell
.\ENABLE-NETWORK-ACCESS.ps1  # run once as Administrator
```

### Option C – Manual control for developers

1. Start shared dependencies:
   ```powershell
   .\start-dev.ps1
   ```
2. Backend (hot reload):
   ```powershell
   .\venv\Scripts\activate
   python -m uvicorn apps.api.main:app --host 0.0.0.0 --port 8000 --reload
   ```
3. Frontend (Next.js dev server):
   ```powershell
   cd ui
   npm install  # first run
   npm run dev
   ```
4. Optional background worker:
   ```powershell
   python -m apps.worker.main
   ```

## Stopping Services

- Automated demo/dev stack:
  ```powershell
  .\stop-dev.ps1
  ```
- Simple demo stack:
  ```powershell
  .\STOP-SIMPLE.ps1
  ```
- Individual terminals can be closed with `Ctrl+C`.

## Health & Verification

```powershell
Invoke-RestMethod http://localhost:8000/api/health/live
Invoke-RestMethod http://localhost:8000/api/health/ready
Invoke-WebRequest http://localhost:8000/api/status
```

UI: http://localhost:3000  
API docs: http://localhost:8000/api/docs

## Copilot Proxy

The dev startup script launches a GitHub Copilot compatibility proxy on port 5001. Set `GITHUB_TOKEN` (or `COPILOT_ACCESS_TOKEN`) in `.env`; the proxy now falls back to those environment variables when `copilot-to-api-main/config.json` is missing.

## Troubleshooting Quick Hits

- **Docker not running?** Launch Docker Desktop or ensure the WSL daemon is active (`wsl.exe -e docker ps`).
- **Port conflict on 8000/3000/15432?** Run the matching stop script, or inspect with `netstat -ano | findstr "8000"` and kill the offending PID.
- **Backend refuses connections?** Verify the Postgres container is healthy: `wsl.exe -e docker inspect --format='{{.State.Health.Status}}' rca_db`.
- **Missing dependencies?** Reactivate the virtualenv and rerun `pip install -r requirements.txt` / `npm install` in `ui/`.

For deeper environment configuration, continue with [Developer Environment Setup](dev-setup.md).
