# Troubleshooting Playbook

Quick fixes for the most common problems seen during local development and demos.

## Docker & Networking

### Critical: Docker via WSL Only

**Never run Docker commands directly from Windows PowerShell/CMD!** This project uses Docker through WSL.

❌ **Wrong** (will fail):
```powershell
docker ps
docker compose up
```

✅ **Correct**:
```powershell
# Use provided scripts
.\quick-start-dev.ps1

# Or prefix with WSL
wsl bash -c "docker ps"
wsl bash -c "docker compose -f deploy/docker/docker-compose.yml up -d"
```

### Common Docker Issues

- **Docker daemon unavailable** – Start Docker Desktop or restart the WSL service: `wsl --shutdown` followed by relaunching Docker.
- **"Sign in to Docker Desktop" error** – You ran Docker from Windows PowerShell directly. Always use WSL or the provided scripts.
- **Container stuck restarting** – Inspect with `wsl bash -c "docker compose logs <service>"`; authentication failures usually trace back to missing values in `.env` (e.g., `GITHUB_TOKEN`).
- **Port already in use** – Identify the culprit: `netstat -ano | findstr "8000 3000 15432 16379"`, then `taskkill /PID <pid> /F`.
- **WSL networking issues** – If the UI cannot reach the backend, rerun `ENABLE-NETWORK-ACCESS.ps1` as Administrator or reset port forwards via `cleanup-network.bat`.
- **Backend still starting** – Containers need 15-30 seconds to fully initialize. Check logs: `wsl bash -c "docker logs rca_core --tail 50"`.

## Backend API

- **401 responses in dev** – Ensure `LOCAL_DEV_AUTH_TOKEN` matches the `DEV_BEARER_TOKEN` configured for the worker/UI. Regenerate tokens in `.env` and restart the backend.
- **Database connection errors** – Postgres container may not be ready. Check health: `wsl.exe -e docker inspect --format='{{.State.Health.Status}}' rca_db`. Re-run `start-dev.ps1` if needed.
- **Migrations failing** – Confirm credentials in `.env` align with `docker-compose.dev.yml`. Run `alembic upgrade head` inside the running backend container or virtualenv.

## Frontend UI

- **Blank or unstyled UI** – Clear the Next.js cache: `Remove-Item -Recurse -Force ui/.next`, then `npm run dev`.
- **SSE stream stops updating** – Verify the worker is running (if `quick-start-dev.ps1` launched without `-IncludeWorker`, uploads will queue). Check the terminal for heartbeat timestamps.

## Copilot Proxy

- **`config.json` missing error** – The proxy now reads the token from `GITHUB_TOKEN` / `COPILOT_ACCESS_TOKEN`. Re-run `quick-start-dev.ps1` after updating `.env`.
- **Token refresh failures** – PAT must include `copilot` scope. Renew via GitHub settings and restart the proxy terminal.

## Scripts

- **`Virtual environment not found`** – Run `.\setup-dev-environment.ps1` to recreate `venv/`.
- **Firewall prompts keep appearing** – Execute `.\ENABLE-NETWORK-ACCESS.ps1` as Administrator; Windows may have discarded previous rules after updates.

If an issue persists, check historical notes under `docs/archive/` for deeper dives into past networking and port-forwarding fixes.
