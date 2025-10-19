# 📄 Product Requirements Document (PRD)

## RCA Insight Engine — Python-First, Conversational, Multi-LLM, and Multi-Platform ITSM Ready

---

### **1. Project Title**

**RCA Insight Engine**
*A Python-first, LLM-agnostic RCA system with traceability, file watching, and per-session ITSM integration.*

---

### **2. Objective**

Develop a **reusable**, **platform-agnostic**, and **LLM-neutral** engine that:

* Ingests automation logs (Blue Prism, Appian, PEGA, etc.)
* Performs **Root Cause Analysis (RCA)** using contextual multi-turn LLM reasoning
* Persists all **LLM prompts/responses per session**
* Outputs RCA summaries (Markdown, HTML, JSON)
* Automatically creates **tickets in ServiceNow or Jira**, configurable **per session**
* Includes a **React/Next.js demo UI**
* Offers a **configurable File Watcher** for auto-triggering RCA jobs
* Exposes **clean FastAPI endpoints** for external integration

---

### **3. Core Features**

#### 🧠 Conversational RCA Engine

* Multi-turn LLM analysis per job/session
* Contextual memory & conversation persistence (Postgres)
* Semantic chunking and embeddings stored via **pgvector**
* Retrieval orchestration (native Python, Semantic Kernel, or LangChain optional)
* Each RCA run tracked as a **session** with full lineage (prompts, outputs, metadata)

#### 🤖 LLM Provider Layer

* **Primary (Cloud):** Azure OpenAI, Anthropic Claude, AWS Bedrock
* **Fallback (Local):** vLLM, LM Studio, DeepSpeed Chat (Ollama only if explicitly enabled)
* Modular provider interface with token usage tracking & latency metrics

#### 📄 RCA Outputs

* **Markdown** — lightweight, readable summary
* **HTML** — formatted report with embedded evidence
* **JSON** — structured output with:

  * severity, categories, tags, timestamps
  * conversation/thread metadata
  * recommended actions and linked ticket info

#### 🧾 ITSM Ticketing (Per Session)

* Supports **Jira** and **ServiceNow**
* Configurable **per job/session** with credential profiles
* Customizable **templates & field mappings**
* Optional **dry-run mode** for previewing payloads before creation
* Ticket metadata persisted in Postgres (`ticket_id`, platform, URL, payload)

#### 🗂️ File Watcher (Configurable)

* Monitors local or mounted directories for `.log`, `.csv`, `.json`, or `.txt` files
* Trigger RCA jobs automatically upon file detection
* Configurable include/exclude globs, MIME validation, file size limit
* Allowlisted directories only (secure sandboxing)
* SSE updates for live file ingestion & processing activity

#### 🖥️ Demo UI (React/Next.js)

* File upload interface
* RCA summary viewer (Markdown/HTML)
* **Live status via SSE stream**
* Threaded LLM conversation viewer
* **Watcher configuration panel**
* **Ticket configuration controls** per session
* Built with TailwindCSS (dark mode enabled)

---

### **4. System Architecture**

```
                [Automation Logs or File Watcher]
                               ↓
                 [Chunk → Embed → pgvector]
                               ↓
                  [Retriever + Prompt Builder]
                               ↓
                    [LLM Provider Adapter]
                               ↓
                [RCA Outputs: MD / HTML / JSON]
                               ↓
          [ITSM Adapter: ServiceNow / Jira / Appian / PEGA]
                               ↓
                      [Ticketing Platform]
```

**Runtime Components**

* FastAPI API server (Gunicorn + Uvicorn)
* Worker (Celery/Dramatiq) for long-running jobs
* PostgreSQL 15+ with pgvector
* Optional Redis (rate limiting, async locks)
* React/Next.js UI (standalone)
* Docker Compose orchestration

---

### **5. Data Model Overview**

| Entity               | Purpose                                  |
| -------------------- | ---------------------------------------- |
| **Job**              | Represents one RCA analysis session      |
| **File**             | Attached log file(s) for processing      |
| **Document**         | Embedded text chunks with pgvector       |
| **ConversationTurn** | Stores each LLM prompt/response          |
| **JobEvent**         | Event stream for job progress            |
| **Ticket**           | Linked ITSM record metadata              |
| **WatcherConfig**    | File watcher runtime configuration       |
| **ItsmProfile**      | Secure credential profiles for ITSM APIs |
| **WatcherEvent**     | File detection/ingestion logs            |

**Relationships**

* `Job` → many `ConversationTurn`, `File`, `Document`, `JobEvent`, `Ticket`
* `WatcherConfig` (admin-managed) → emits `WatcherEvents`
* `Job.ticketing` → references `ItsmProfile` for credentials

---

### **6. Database Entities (Key Fields)**

#### `jobs`

* `id`, `status`, `type`, `created_at`, `started_at`, `finished_at`
* `input_manifest (jsonb)`
* `outputs (jsonb)`
* `provider`, `model_config`
* `ticketing (jsonb)` → ITSM config
* `source (jsonb)` → watcher path, checksum, etc.

#### `watcher_configs`

* `id`, `enabled`, `roots[]`, `include_globs[]`, `exclude_globs[]`
* `max_file_size_mb`, `allowed_mime_types[]`
* `batch_window_seconds`, `auto_create_jobs`

#### `itsm_profiles`

* `id`, `name`, `platform ('servicenow'|'jira')`
* `base_url`, `auth_method`, `secret_ref`
* `defaults (jsonb)` → project/table defaults

---

### **7. APIs**

| Endpoint                     | Purpose                                        |
| ---------------------------- | ---------------------------------------------- |
| `POST /api/jobs`             | Submit RCA job (supports ITSM config override) |
| `GET /api/jobs/{id}`         | Fetch job status & summary metadata            |
| `GET /api/jobs/{id}/stream`  | **SSE** stream of job events                   |
| `GET /api/summary/{id}`      | Retrieve RCA outputs                           |
| `GET /api/conversation/{id}` | Retrieve conversation history                  |
| `GET /api/tickets/{id}`      | Retrieve ticket info                           |
| `POST /api/tickets`          | Explicit ticket creation (optional)            |
| `GET /api/watcher/config`    | Retrieve watcher config                        |
| `PUT /api/watcher/config`    | Update watcher config (admin only)             |
| `GET /api/watcher/events`    | **SSE** stream of watcher events               |
| `GET /api/watcher/status`    | File watcher status/metrics                    |
| `GET /healthz` / `readyz`    | Liveness/readiness probes                      |
| `GET /metrics`               | Prometheus-compatible metrics                  |

---

### **8. Example API Payloads**

#### **POST /api/jobs**

```json
{
  "job_type": "rca_analysis",
  "input_manifest": { "files": ["file_id_or_url"] },
  "ticketing": {
    "platform": "jira",
    "profile": "jira_dev",
    "dry_run": true,
    "mapping_override": {
      "summary_template": "RCA: {primary_cause} detected in {system}",
      "description_template": "Logs analyzed:\n{evidence}",
      "severity_to_priority": { "critical": "1", "high": "2" },
      "custom_fields": { "labels": ["RPA", "Exception"], "assignee": "opsuser" }
    }
  }
}
```

#### **PUT /api/watcher/config**

```json
{
  "enabled": true,
  "roots": ["/app/watch-folder/inbound"],
  "include_globs": ["**/*.log","**/*.csv"],
  "exclude_globs": ["**/~*"],
  "max_file_size_mb": 150,
  "allowed_mime_types": ["text/plain","application/json"],
  "batch_window_seconds": 5,
  "auto_create_jobs": true
}
```

---

### **9. Configuration (ENV / Config File)**

```env
LLM_PROVIDER=azure_openai
LLM_MODEL=gpt-4o
ENABLE_OLLAMA=false
DATABASE_URL=postgresql+asyncpg://rca:***@db:5432/rca
ENABLE_PGVECTOR=true
ENABLE_RATE_LIMITING=true
REDIS_URL=redis://redis:6379/0
STORAGE_TYPE=s3
S3_BUCKET=rca-artifacts
JWT_SECRET=supersecretkey
CORS_ALLOWED_ORIGINS=https://ui.company.com
ALLOWED_WATCH_ROOTS=/app/watch-folder/inbound,/data/inbound
LOG_LEVEL=INFO
```

---

### **10. Deliverables**

| Component            | Description                                                 |
| -------------------- | ----------------------------------------------------------- |
| **RCA API**          | FastAPI backend with clean endpoints, SSE, and OpenAPI spec |
| **Worker**           | Background RCA execution, retries, & budget limits          |
| **LLM Providers**    | Cloud + local adapters with fallback logic                  |
| **Retrieval Engine** | Embeddings via sentence-transformers + pgvector             |
| **Ticket Module**    | Modular adapters for Jira & ServiceNow                      |
| **File Watcher**     | Async watchdog with debounce, secure sandbox, and config UI |
| **Database**         | Postgres + Alembic migrations (pgvector enabled)            |
| **Frontend**         | Next.js + Tailwind (dark mode, config panels)               |
| **Compose Stack**    | API, worker, db, redis(optional), ui, (ollama optional)     |
| **Sample Logs**      | Blue Prism, Appian, PEGA logs for testing                   |
| **Swagger Spec**     | OpenAPI 3+ with typed schemas & examples                    |
| **CI/CD**            | Lint, type check, pip-audit, Bandit, Trivy, E2E smoke tests |

---

### **11. Success Criteria**

✅ RCA accuracy ≥90% vs SME benchmark
✅ Per-session ticket creation success ≥99%
✅ File watcher detection → job creation latency <2s
✅ 100% conversation persistence & traceability
✅ 429 backpressure at queue > threshold
✅ CI pipeline blocks on high/critical vulns

---

### **12. Security & Compliance**

* Non-root containers, read-only FS
* Secrets via ENV or secret store; never logged
* CSP without `'unsafe-inline'`
* JWT with audience/issuer claims
* MIME + magic number file validation
* Presigned S3 URLs for large downloads
* RBAC: watcher admin endpoints require `admin` scope

---

### **13. Observability**

* Metrics:

  * `jobs_started_total`, `jobs_failed_total`, `ticket_create_latency_seconds`
  * `watcher_files_detected_total`, `watcher_files_ingested_total`
* Tracing: OpenTelemetry optional (sample on errors or slow runs)
* Logging: JSON structured logs, correlation by `job_id`
* Dashboards: Grafana panels for job counts, latency, ticket success rates

---

### **14. Non-Goals**

* Multi-tenant RBAC (future)
* Full real-time WebSocket chat (SSE sufficient for v1)
* Cross-org analytics and RCA benchmarking

---

### **15. Deployment**

* **Docker-first**

  * API & worker from single image
  * Gunicorn (UvicornWorker) for API
  * Alembic auto-migrate on start
* **Profiles**: `local`, `dev`, `prod`
* **Zero-downtime reload** for file watcher config

---
