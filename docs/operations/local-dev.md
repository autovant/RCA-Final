# Local Development Services

This guide covers how the local development helpers provision the database and cache dependencies that back the RCA engine. The `start-dev.ps1` script coordinates Docker for Postgres + pgvector and Redis while the application code runs natively on Windows.

## Required Services

- **Postgres (pgvector)**
  - Container name: `rca_db`
  - Image: `pgvector/pgvector:pg15`
  - Port mapping: `15432 -> 5432`
  - Health check now targets the configured `POSTGRES_DB` (default `rca_engine`) to avoid false negatives.
- **Redis**
  - Container name: `rca_redis`
  - Image: `redis:7-alpine`
  - Port mapping: `16379 -> 6379`

| Service | Compose Target | Enabled by `start-dev.ps1` | Notes |
|---------|----------------|----------------------------|-------|
| Postgres + pgvector | `docker-compose.dev.yml:db` | ✓ | Starts automatically with health checks and seeded init scripts. |
| Redis (cache/queue) | `docker-compose.dev.yml:redis` | ✓ | Launches alongside Postgres; optional but required for telemetry buffering. |
| Ollama (optional) | `docker-compose.dev.yml:ollama` | ✗ *(profile `with_ollama`)* | Only runs when you pass `--profile with_ollama` manually. |

Optional profile `with_ollama` launches `ollama/ollama:latest` when advanced LLM testing is required. It is disabled by default.

## Startup Flow (`start-dev.ps1`)

1. Verifies the Windows virtual environment (`venv/`) and `.env` are present.
2. Confirms Docker is reachable via WSL and cleans up lingering `rca_db` / `rca_redis` containers.
3. Runs `docker compose -f docker-compose.dev.yml up -d db redis` to ensure Postgres and Redis are online.
4. Waits up to 30 attempts for the Postgres health check to report `healthy`.
5. Executes Alembic migrations using the virtual environment interpreter.

If you need to rebuild the data volumes, set `RESET_DB_STATE=true` before running the script. This removes the `postgres_data` and `redis_data` Docker volumes.

## Manual Checks

- Inspect running containers: `wsl.exe -e docker ps | Select-String rca_`
- Verify Postgres connectivity: `psql "postgres://rca_user:rca_password_change_in_production@127.0.0.1:15432/rca_engine" -c '\l'`
- Verify Redis connectivity: `redis-cli -h 127.0.0.1 -p 16379 ping`

## Troubleshooting

- **Health check failures**: Confirm the `POSTGRES_DB` value in `.env` matches the Docker compose environment. The health check now reads this value, so mismatches typically indicate misconfigured `.env` or cached compose state. Run `docker compose -f docker-compose.dev.yml down --volumes` to reset if needed.
- **Docker access errors**: Ensure the Docker daemon is running inside WSL and retry. The startup script exits early when `docker ps` fails, so you may need to start the service manually (`wsl.exe -e sudo service docker start`).
- **Port conflicts**: Another local Postgres or Redis instance may occupy ports `15432` or `16379`. Stop the conflicting service, or adjust the `ports` mapping in `docker-compose.dev.yml`.
