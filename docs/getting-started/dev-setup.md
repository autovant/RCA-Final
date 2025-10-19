# Developer Environment Setup

This guide distills the content from the legacy `DEV_SETUP_SIMPLIFIED.md` into a focused checklist for day-to-day development.

## Tooling Prerequisites

| Component | Version | Notes |
|-----------|---------|-------|
| Python | 3.11+ | Install with the "Add to PATH" option. |
| Node.js | 18+ | Required for the Next.js UI. |
| WSL 2 + Docker Engine | Latest | Run `wsl.exe -e docker ps` to confirm Docker is reachable. |
| Git | Latest | Ensure `core.autocrlf` is set to `true` on Windows. |

## One-Time Setup

```powershell
# From repository root
.\setup-dev-environment.ps1
```

What the script does:
- Creates/refreshes `venv/`
- Installs Python requirements (dev + prod)
- Installs UI dependencies (runs `npm install` in `ui/`)
- Seeds local configuration (copies `.env.example` → `.env` if missing)
- Ensures Docker volumes exist for Postgres/Redis

If you need to rerun the bootstrap without re-installing npm packages:
```powershell
.\setup-dev-environment.ps1 -SkipNodeInstall
```

## Managing Services Manually

1. **Databases (Postgres/Redis)**
   ```powershell
   .\start-dev.ps1
   ```
   This brings up the Docker compose stack defined in `docker-compose.dev.yml`.

2. **Backend API (FastAPI + Uvicorn)**
   ```powershell
   .\venv\Scripts\activate
   python -m uvicorn apps.api.main:app --host 0.0.0.0 --port 8000 --reload
   ```

3. **Async Worker (Celery alternative)**
   ```powershell
   python -m apps.worker.main
   ```

4. **Frontend UI (Next.js)**
   ```powershell
   cd ui
   npm run dev
   ```

All three processes use hot reload. Keep them in dedicated terminals for clear logs.

## Database Utilities

- Generate migration: `alembic revision -m "describe change"`
- Apply migrations: `alembic upgrade head`
- Inspect health: `wsl.exe -e docker ps --filter name=rca_db`

## Environment Variables

Primary overrides live in `.env`. Key values:

```bash
POSTGRES_HOST=localhost
POSTGRES_PORT=15432
POSTGRES_USER=rca_user
POSTGRES_PASSWORD=<set me>
JWT_SECRET_KEY=<32+ characters>
DEFAULT_PROVIDER=copilot
GITHUB_TOKEN=<token with Copilot scope>
```

UI overrides live in `ui/.env.local` (defaults to `http://localhost:8000`).

## When Things Break

- **Rebuild venv**: delete `venv/` and rerun `setup-dev-environment.ps1`
- **Clear Next.js cache**: `Remove-Item -Recurse -Force ui/.next`
- **Docker volume reset**: `wsl.exe -e docker compose -f docker-compose.dev.yml down -v`
- **Firewall prompts**: rerun `.\ENABLE-NETWORK-ACCESS.ps1` as Administrator

For a scripted start-to-finish experience refer back to the [Quickstart Checklist](quickstart.md).
