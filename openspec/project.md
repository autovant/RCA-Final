# Project Context

## Purpose
The **RCA Insight Engine** is a unified, Python-first root-cause analysis platform designed for enterprise environments. It provides:

- **Multi-layered PII protection** with 30+ pattern types, multi-pass scanning, and strict validation
- **Multi-provider LLM support** (GitHub Copilot, OpenAI, Bedrock, Anthropic, LM Studio, vLLM)
- **Streaming progress updates** via SSE for real-time analysis feedback
- **ITSM integrations** with ServiceNow and Jira for automated ticket creation
- **Intelligent investigation pipeline** combining embeddings (pgvector), retrieval, and LLM reasoning
- **File watcher integration** for automated artefact ingestion
- **Structured outputs** in Markdown, HTML, and JSON formats

Core goal: Enable engineering teams to perform fast, secure, and automated root-cause analysis on system artefacts while protecting sensitive data.

## Tech Stack

### Backend
- **Python 3.11+** – Primary language
- **FastAPI** – REST API and SSE streaming endpoints
- **SQLAlchemy 2.0** – ORM with async support
- **PostgreSQL + pgvector** – Database with vector embeddings
- **Alembic** – Database migrations
- **Redis** – Optional caching layer
- **Uvicorn** – ASGI server with hot reload
- **Pydantic 2.9** – Data validation and settings management

### Frontend
- **Next.js 14** – React framework with App Router
- **TypeScript 5.3** – Type-safe development
- **Tailwind CSS** – Utility-first styling
- **React Hook Form + Zod** – Form handling and validation
- **Zustand** – State management
- **Axios** – HTTP client
- **EventSource** – SSE client for real-time updates
- **Recharts** – Data visualization

### LLM & AI
- **OpenAI SDK** – GPT models
- **Anthropic SDK** – Claude models
- **Boto3** – AWS Bedrock integration
- **Ollama** – Local LLM support
- **NumPy** – Vector operations

### Infrastructure & DevOps
- **Docker Engine (WSL 2)** – Container runtime (NOT Docker Desktop)
- **Docker Compose** – Multi-container orchestration
- **Prometheus** – Metrics collection
- **Grafana** – Observability dashboards (optional)
- **Watchdog** – File system monitoring

### Testing & Quality
- **Pytest** – Unit and integration testing
- **Playwright** – End-to-end UI testing
- **Ruff/MyPy** – Linting and type checking (recommended)

## Project Conventions

### Code Style

**Python:**
- **Async-first**: Use `async def` for all I/O-bound operations (database, HTTP, LLM calls)
- **Type hints**: All functions must include type annotations (Pydantic models preferred)
- **Naming**:
  - Classes: `PascalCase` (e.g., `JobProcessor`, `TicketService`)
  - Functions/variables: `snake_case` (e.g., `process_job`, `job_id`)
  - Constants: `UPPER_SNAKE_CASE` (e.g., `MAX_RETRIES`, `DEFAULT_TIMEOUT`)
  - Private members: prefix with `_` (e.g., `_internal_method`)
- **Imports**: Group into stdlib, third-party, local (separated by blank lines)
- **Docstrings**: Use triple quotes for module, class, and public function documentation
- **Line length**: Aim for 100 characters (not strict)

**TypeScript/React:**
- **Components**: PascalCase for React components (e.g., `JobDashboard.tsx`)
- **Hooks**: Prefix with `use` (e.g., `useJobStatus`)
- **Types/Interfaces**: PascalCase with descriptive names (e.g., `JobStatusResponse`)
- **Constants**: UPPER_SNAKE_CASE for config values
- **File naming**: `kebab-case.tsx` for components, `camelCase.ts` for utilities

### Architecture Patterns

**Layered Architecture:**
```
apps/          # Application entry points (FastAPI, Worker)
  ├── api/     # REST endpoints, routers, middleware
  └── worker/  # Background job processing
core/          # Domain logic (shared across apps)
  ├── db/      # SQLAlchemy models, database utilities
  ├── jobs/    # Job processing orchestration
  ├── llm/     # LLM provider abstraction
  ├── privacy/ # PII redaction engine
  ├── prompts/ # Prompt management
  ├── security/# Auth, encryption, access control
  └── tickets/ # ITSM integrations (ServiceNow, Jira)
```

**Key Patterns:**
- **Router-based endpoints**: Each domain (jobs, files, tickets) has its own FastAPI `APIRouter`
- **Dependency Injection**: Use FastAPI's `Depends()` for database sessions, auth, and services
- **Service Layer**: Business logic lives in `core/` modules, not in route handlers
- **Event-driven**: Use `job_event_bus` and `watcher_event_bus` for SSE streaming
- **Repository Pattern**: Database operations abstracted via SQLAlchemy models and helper functions
- **Strategy Pattern**: LLM provider selection via `core/llm/factory.py`
- **Multi-pass processing**: PII redaction runs 2-3 passes to catch nested patterns

**Database:**
- Async SQLAlchemy sessions (`AsyncSession`)
- Alembic for migrations (never modify schema manually)
- pgvector for embeddings storage

### Testing Strategy

**Framework:** Pytest with async support (`asyncio_mode = auto`)

**Test Organization:**
```
tests/
  ├── unit/         # Fast, isolated tests
  ├── integration/  # Tests with database/external services
  ├── playwright/   # End-to-end UI tests
  └── conftest.py   # Shared fixtures
```

**Markers:**
- `@pytest.mark.unit` – Unit tests (fast, no external deps)
- `@pytest.mark.integration` – Integration tests (database, Redis)
- `@pytest.mark.slow` – Long-running tests

**Requirements:**
- All new features must include tests
- Run `python -m pytest` before committing
- Playwright tests for critical UI flows: `cd tests/playwright && npm test`
- Mock external LLM calls in unit tests

**Coverage Goals:**
- Core business logic: >80%
- API endpoints: >70%
- UI components: Best-effort (focus on critical paths)

### Git Workflow

**Branching Strategy:**
- `master` – Production-ready code (default branch)
- Feature branches: `<ticket-number>-<description>` (e.g., `002-unified-ingestion-enhancements`)
- Hotfix branches: `hotfix-<description>`

**Commit Conventions:**
- Use descriptive commit messages (not enforced, but preferred)
- Group related changes in single commits
- Include ticket/issue numbers when applicable

**Workflow:**
1. Create feature branch from `master`
2. Make incremental changes with tests
3. Update documentation for behavior changes
4. Run tests locally before pushing
5. Create PR for review (if team workflow requires)

**Important:** Set `core.autocrlf=true` on Windows for consistent line endings.

## Domain Context

**Root Cause Analysis (RCA):**
- Ingesting system artefacts (logs, traces, config files, error dumps)
- Chunking and embedding documents for semantic search
- Retrieving relevant context based on query similarity
- Orchestrating LLM calls to reason about failures
- Generating structured investigation reports

**PII Protection:**
- Enterprise environments require strict data privacy
- Multi-pass redaction engine detects 30+ pattern types:
  - Credentials: AWS/Azure keys, JWT tokens, passwords, API keys, database connection strings
  - Personal data: SSNs, credit cards, emails, phone numbers
  - Security: Private keys, certificates, IP addresses
- Post-redaction validation ensures no leaks
- All redactions logged for audit trails

**ITSM Integration:**
- ServiceNow and Jira ticket creation with structured payloads
- Custom field mapping via `config/itsm_config.json`
- Dry-run mode for testing without creating real tickets

**File Watching:**
- Automated artefact ingestion from monitored directories
- Event-driven processing via `core/watchers/event_bus.py`
- Support for glob patterns and filtering rules

## Important Constraints

**Docker via WSL (CRITICAL):**
- **MUST use Docker Engine inside WSL 2, NOT Docker Desktop**
- Docker Desktop is blocked in enterprise environments
- All scripts invoke `wsl.exe -e docker ...` commands
- Verify with: `wsl.exe -e docker ps`

**Security & Privacy:**
- PII redaction is **enabled by default**
- All LLM inputs must pass through `core/privacy/redactor.py`
- Never log or store unredacted sensitive data
- HTTPS required for production deployments

**Enterprise Environment:**
- Assume firewalls, proxies, and restricted internet access
- Support for local/self-hosted LLM providers (Ollama, vLLM)
- Designed for air-gapped deployments with manual dependency management

**Database:**
- PostgreSQL with pgvector extension is required (not optional)
- Alembic migrations must be version-controlled
- No direct schema modifications outside Alembic

**Async Everywhere:**
- All I/O operations must be async (database, HTTP, file operations)
- Blocking calls in async functions will cause performance degradation

## External Dependencies

**LLM Providers (configurable per job):**
- **GitHub Copilot** – Requires `copilot-to-api-main/` proxy server
- **OpenAI** – API key in environment (`OPENAI_API_KEY`)
- **Anthropic** – API key (`ANTHROPIC_API_KEY`)
- **AWS Bedrock** – Boto3 credentials configured
- **LM Studio / vLLM** – Local HTTP endpoints
- **Ollama** – Local installation required

**ITSM Platforms:**
- **ServiceNow** – REST API credentials and instance URL
- **Jira** – API token and project configuration

**Databases:**
- **PostgreSQL 14+** with `pgvector` extension
- **Redis** (optional) for caching and rate limiting

**Monitoring (optional):**
- **Prometheus** – Metrics scraping endpoint at `/metrics`
- **Grafana** – Dashboards for observability

**Infrastructure:**
- **WSL 2** – Required on Windows for Docker Engine
- **Docker Engine** – NOT Docker Desktop

**File System:**
- **Watchdog** – Python library for file system event monitoring
- Monitored directories: `deploy/watch-folder/`, `uploads/`
