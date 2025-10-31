# Developer Environment Setup

This guide distills the content from the legacy `DEV_SETUP_SIMPLIFIED.md` into a focused checklist for day-to-day development.

## ⚠️ Critical Prerequisite: Docker in WSL (NOT Docker Desktop)

**This project requires Docker Engine running INSIDE WSL 2, NOT Docker Desktop on Windows.**

### Why WSL Docker?
- Docker Desktop is typically **blocked in enterprise environments**
- All startup scripts use `wsl.exe` to invoke Docker commands inside your WSL distribution
- Database containers (PostgreSQL, Redis) run in WSL's Docker Engine

### Verify Docker in WSL
```powershell
# Test from PowerShell - should show running containers
wsl.exe -e docker ps

# If this fails, Docker is not properly installed/running in WSL
```

### Installing Docker in WSL (if needed)
```bash
# Inside WSL terminal (Ubuntu/Debian):
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER
# Log out and back in, then:
sudo service docker start
```

## Tooling Prerequisites

| Component | Version | Notes |
|-----------|---------|-------|
| Python | 3.11+ | Install with the "Add to PATH" option. |
| Node.js | 18+ | Required for the Next.js UI. |
| **WSL 2 + Docker Engine** | **Latest** | **Docker must run INSIDE WSL, not Docker Desktop.** Run `wsl.exe -e docker ps` to confirm. |
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

### Docker-Related Issues

- **"ERROR: WSL is not available"**
  - Enable WSL 2: `wsl --install` (requires admin, reboot)
  - Verify: `wsl.exe --version`

- **"ERROR: docker compose is not available inside WSL"**
  - Docker not installed in WSL distribution
  - Inside WSL: `curl -fsSL https://get.docker.com -o get-docker.sh && sudo sh get-docker.sh`
  - Add user to docker group: `sudo usermod -aG docker $USER` (log out/in)
  - Start Docker: `sudo service docker start`

- **"ERROR: Unable to translate repository path into WSL"**
  - WSL cannot access Windows filesystem
  - Check mount: `wsl.exe -e ls /mnt/c/Users` (should show your user folder)
  - Verify WSL path translation: `wsl.exe wslpath -a "C:\Users"`

- **Scripts fail with "container name already in use"**
  - Old containers still running: `wsl.exe -e docker ps -a`
  - Remove all RCA containers: `wsl.exe -e docker rm -f $(docker ps -aq --filter name=rca_)`
  - Or use: `.\STOP-SIMPLE.ps1` then retry

- **"Cannot connect to Docker daemon"**
  - Docker service not running in WSL
  - Start it: `wsl.exe -e sudo service docker start`
  - Auto-start (Ubuntu): add to `~/.bashrc`: `if [ ! -S /var/run/docker.sock ]; then sudo service docker start; fi`

### Other Common Issues

- **Rebuild venv**: delete `venv/` and rerun `setup-dev-environment.ps1`
- **Clear Next.js cache**: `Remove-Item -Recurse -Force ui/.next`
- **Docker volume reset**: `wsl.exe -e docker compose -f docker-compose.dev.yml down -v`
- **Firewall prompts**: rerun `.\ENABLE-NETWORK-ACCESS.ps1` as Administrator

For a scripted start-to-finish experience refer back to the [Quickstart Checklist](quickstart.md).
