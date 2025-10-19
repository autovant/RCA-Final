# Deployment Guide

This guide consolidates the legacy Docker deployment notes and checklists into a single workflow suitable for staging or production.

## Prerequisites

- Docker Engine 24.x+ and Docker Compose v2.x (Desktop integration or server installation)
- WSL 2 enabled on Windows hosts
- GitHub Personal Access Token with the Copilot scope (`GITHUB_TOKEN`)
- TLS certificates for public deployments (reverse proxy not covered here)
- Optional: access to monitoring stack ports (Grafana/Prometheus)

## 1. Prepare the Host

1. Enable WSL and install a Linux distribution (`wsl --install`).
2. Install and start Docker Desktop (ensure WSL integration is enabled for your distro).
3. Clone the repository and copy the deployment environment template:
   ```bash
   git clone https://github.com/<org>/RCA-Final.git
   cd RCA-Final/deploy/docker
   cp .env.example .env
   ```
4. Populate `.env` with:
   - `GITHUB_TOKEN`
   - Database credentials (used both by Postgres and the backend)
   - Grafana admin password (if monitoring enabled)

## 2. Launch the Core Stack

> Run the following commands from inside WSL or a Linux shell. Windows PowerShell/Command Prompt is **not** supported.

```bash
cd /mnt/c/Users/syed.shareef/.vscode/repos/RCA - v7/RCA-Final/deploy/docker

# Start database + redis first
docker compose up -d db redis
# optional: include ollama if running on GPU host
docker compose up -d ollama

# Build and start the application container
docker compose up -d --build rca_core
```

Watch logs until startup completes:
```bash
docker compose logs -f rca_core
```
Look for `Application startup complete.`

## 3. Database Migrations

```bash
docker compose exec rca_core alembic upgrade head
```

Run `docker compose exec rca_core alembic current` to confirm the active revision.

## 4. Frontend (Next.js) Deployment Options

| Mode | Description | Command |
|------|-------------|---------|
| Static build served by Node (default) | Uses the container defined in `docker-compose.yml` | `docker compose up -d rca_ui` |
| External hosting (Vercel/Static) | Build artifacts locally and deploy separately | `npm run build && npm run export` inside `ui/` |

Ensure `NEXT_PUBLIC_API_BASE_URL` points to the public API endpoint.

## 5. Monitoring Stack (Optional)

Enable Prometheus and Grafana using the `monitoring` profile:
```bash
docker compose --profile monitoring up -d prometheus grafana
```

- Prometheus: http://<host>:9090
- Grafana: http://<host>:3001 (default credentials `admin / admin` — change on first login)
- Import dashboards from `deploy/docker/config/grafana/dashboards/`

## 6. Post-Deployment Validation

1. Health checks:
   ```bash
   curl http://<host>:8000/api/health/live
   curl http://<host>:8000/api/health/ready
   curl http://<host>:8001/metrics | head
   ```
2. SSE stream:
   ```bash
   curl http://<host>:8000/api/sse/jobs/<job_id>
   ```
3. Upload a sample file via the UI and confirm the investigation pipeline runs end-to-end.

## 7. Operational Scripts

Located in `deploy/` and root scripts folder:
- `deploy.sh` – convenience wrapper for Linux hosts
- `cleanup-network.bat` / `cleanup-port-forwarding-hybrid.ps1` – remove conflicting Windows rules (legacy)
- `start-environment.ps1` – orchestrated multi-window startup used for hybrid demos

## 8. Common Issues

| Symptom | Resolution |
|---------|------------|
| Containers restart continuously | Inspect `docker compose logs <service>`; verify secrets in `.env`. |
| Port already in use | Adjust host port bindings in `docker-compose.yml` or free the port via `netstat`/`taskkill`. |
| `alembic upgrade` fails | Ensure Postgres credentials match `.env`; rerun `docker compose up -d db`. |
| Copilot proxy errors | Confirm `GITHUB_TOKEN` is set; the proxy now falls back to environment variables if `config.json` is absent. |

## 9. Next Steps

- Configure ITSM templates in `config/itsm_config.json`
- Enable background workers (`docker compose up -d worker`) if processing high volume
- Integrate with your observability platform by scraping the Prometheus metrics endpoint

For historical deployment experiments and previous fix logs, refer to [`docs/archive/`](../archive/README.md).
