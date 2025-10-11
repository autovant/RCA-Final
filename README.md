# RCA Insight Engine

Unified, Python-first root-cause analysis (RCA) platform delivering multi-turn LLM reasoning, conversation traceability, configurable privacy controls, and ITSM-ready integrations.

---

## Features

- **Conversational RCA Pipeline** – FastAPI API + async worker orchestrate chunking, embeddings (pgvector), retrieval, and multi-turn LLM analysis with persistent conversation history.
- **Multi-provider LLM support** – Plug-in adapters for Ollama/local, OpenAI, and AWS Bedrock with per-job model overrides.
- **PII/Sensitive Data Redaction** – Configurable regex-based sanitizer runs before summarisation/embeddings, capturing redaction hit counts for downstream audit.
- **Structured Outputs** – Every job emits Markdown, HTML, and JSON bundles including severity, recommended actions, and ticket metadata.
- **ITSM Ticketing** – Modular ticket service stores previews or created tickets (Jira/ServiceNow), with dry-run mode and profile-based credentials.
- **File Watcher & SSE Streams** – Central watcher configuration, event bus, and `/api/watcher/events` SSE endpoint for live ingestion dashboards.
- **Traceability & Metrics** – Job events, conversation turns, Prometheus metrics, and structured logging for full observability.
- **React/Next.js Demo UI** – Upload artefacts, configure watchers, monitor SSE streams, and review RCA outputs from a companion UI (see `ui/`).

---

## Architecture Overview

```
┌───────────────┐    ┌───────────────┐    ┌──────────────┐
│ File Uploads  │    │ Watcher Events│    │ API Clients  │
└──────┬────────┘    └──────┬────────┘    └──────┬───────┘
       │                     │                   │
       ▼                     ▼                   ▼
┌────────────────────────────────────────────────────────┐
│                  FastAPI Application                    │
│  - Auth / Files / Jobs / Summary / Tickets / Watcher    │
│  - SSE streams for job + watcher events                 │
└────────┬───────────────────────────────┬───────────────┘
         │                               │
         │ enqueue jobs                  │ metrics/logging
         ▼                               ▼
┌───────────────────────┐        ┌────────────────────┐
│ Async Worker (Celery) │        │ Observability Stack │
│ - Chunk + embed files │        │ - Prometheus        │
│ - PII redaction       │        │ - Structured logs   │
│ - LLM orchestration   │        └────────────────────┘
│ - Ticket callbacks    │
└─────────┬─────────────┘
          │      ┌────────────────────┐
          │      │ LLM Providers      │
          │      │ (Ollama/OpenAI/etc)│
          │      └────────────────────┘
          ▼
┌──────────────────────────────────────────────┐
│ PostgreSQL (pgvector) + Optional Redis       │
│  - jobs / files / documents / conversation   │
│  - watcher config & events                   │
│  - ticket metadata                           │
└──────────────────────────────────────────────┘
```

---

## Getting Started

### 1. Clone & configure

```bash
git clone https://github.com/<org>/unified_rca_engine.git
cd unified_rca_engine
cp .env.example .env
# update secrets, database host, LLM keys, and privacy settings as needed
```

### 2. Run services locally (Docker Compose)

```bash
docker compose -f deploy/docker/docker-compose.yml up --build
```

Services exposed by default:

| Service          | Port | Notes                                   |
|------------------|------|-----------------------------------------|
| API (Gunicorn)   | 8000 | FastAPI endpoints `/api/...`            |
| Metrics          | 8001 | Prometheus scrape endpoint              |
| UI (Next.js)     | 3000 | Demo dashboard                          |
| Postgres         | 5432 | pgvector-enabled database               |
| Redis (optional) | 6379 | Event bus / rate limiting               |

### 3. Launch worker & UI for local dev

```bash
python -m apps.worker.main          # background processing
cd ui && npm install && npm run dev # Next.js dashboard
```

### 4. Verify health

```bash
curl http://localhost:8000/api/health/liveness
curl http://localhost:8000/api/health/readiness
curl http://localhost:8000/api/status
```

---

## Key API Endpoints

| Route                               | Description                                             |
|-------------------------------------|---------------------------------------------------------|
| `POST /api/jobs/`                   | Create RCA job (supports per-job provider & ticketing)  |
| `GET /api/jobs/{id}`                | Job status snapshot                                     |
| `GET /api/jobs/{id}/events`         | Historical events                                       |
| `GET /api/jobs/{id}/stream`         | SSE stream (alias for `/api/sse/jobs/{id}`)             |
| `GET /api/summary/{id}`             | Markdown / HTML / JSON RCA outputs                      |
| `GET /api/conversation/{id}`        | Full conversation history                               |
| `GET /api/files/jobs/{job_id}`      | Uploaded artefacts for a job                            |
| `GET /api/tickets/{job_id}`         | Tickets linked to a job                                 |
| `POST /api/tickets`                 | Record ticket preview or creation                       |
| `GET /api/watcher/config`           | Current watcher settings                                |
| `PUT /api/watcher/config`           | Update watcher settings                                 |
| `GET /api/watcher/events`           | Watcher SSE stream                                      |
| `GET /api/watcher/status`           | Aggregated watcher metrics                              |
| `GET /metrics`                      | Prometheus-compatible metrics                           |

Swagger (`/api/docs`) available when `DEBUG=true`.

---

## Configuration Highlights

| Setting                         | Default        | Description                                             |
|---------------------------------|----------------|---------------------------------------------------------|
| `PII_REDACTION_ENABLED`         | `true`         | Enable automatic PII masking                            |
| `PII_REDACTION_REPLACEMENT`     | `[REDACTED]`   | Replacement token                                       |
| `PII_REDACTION_PATTERNS`        | JSON/List      | `label::regex` entries controlling redaction rules      |
| `DEFAULT_PROVIDER`              | `ollama`       | Fallback LLM provider                                   |
| `MAX_FILE_SIZE_MB`              | `100`          | Upload guardrail                                        |
| `WATCH_FOLDER`                  | `watch-folder` | Default watcher root (may be overridden via API)        |
| `METRICS_ENABLED`               | `true`         | Toggle Prometheus exporter                              |
| `CORS_ALLOW_ORIGINS`            | `["*"]`        | Adjust for production                                   |

Additional settings are documented inline in `core/config.py` and mirrored in `.env.example`.

---

## Development & Testing

```bash
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate
pip install -r requirements.txt

python -m pytest           # unit tests
scripts/setup.sh           # optional helper for local environment bootstrap
```

Linting hooks / type checks can be integrated per your CI strategy (e.g. `ruff`, `mypy`, `bandit`, `pip-audit`).

---

## Project Structure Highlights

```
core/
  config.py        # Settings + typed views (security, privacy, etc.)
  db/              # SQLAlchemy models & async DB manager
  jobs/            # Job service + processor + event bus integration
  llm/             # Provider factory & embedding service
  privacy/         # PII redaction utilities
  security/        # Auth + middleware
apps/
  api/             # FastAPI app, routers, middleware
  worker/          # Async worker entrypoint
ui/                # Next.js demo frontend
deploy/            # Dockerfiles, compose stack, scripts
tests/             # Pytest suite
```

---

## Upgrading / Extending

- **Adding PII Rules**: extend `PII_REDACTION_PATTERNS` in env or via deployment secrets. Patterns accept `label::regex`.
- **Custom LLM Provider**: implement `BaseLLMProvider` subclass under `core/llm/providers/` and register via `LLMProviderFactory.register_provider`.
- **Ticket Platforms**: extend `core/tickets/service.py` to integrate additional systems and expose new API routes or background tasks.
- **Watcher Backends**: the watcher service currently persists configuration/events; plug your own filesystem or object storage listener emitting into `core.watchers.watcher_event_bus`.

---

## License & Contributing

Contributions welcome! Please open issues/PRs with tests and documentation updates. Ensure sensitive configuration values are stored securely (secrets manager or CI variables) before deploying to production.

---

© 2025 RCA Insight Engine Team. All rights reserved.
