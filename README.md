# RCA Insight Engine

Unified, Python-first root-cause analysis platform with multi-provider LLM support, streaming progress updates, and ITSM integrations.

## 🔒 Enterprise-Grade PII Protection

**Your data security is our top priority.** The RCA Engine implements comprehensive, **multi-layered PII redaction** to ensure no sensitive information reaches LLMs or analysis outputs:

- ✅ **30+ Pattern Types**: Automatically detects AWS/Azure keys, JWT tokens, passwords, emails, SSNs, credit cards, private keys, database credentials, and more
- ✅ **Multi-Pass Scanning**: Runs up to 3 redaction passes to catch nested or revealed patterns
- ✅ **Strict Validation**: Post-redaction validation detects potential leaks with security warnings
- ✅ **Highly Visible**: Prominent UI indicators show real-time redaction stats and security status
- ✅ **Audit Trail**: Complete logging of all redactions for compliance and security audits
- ✅ **Enabled by Default**: Zero configuration needed—protection is active out of the box

**See [PII Protection Guide](docs/PII_PROTECTION_GUIDE.md) for complete security documentation.**

---

## Quick Links

### 📚 Getting Started
- [Quickstart Checklist](docs/getting-started/quickstart.md) – Get running in 5 minutes
- [Developer Environment Setup](docs/getting-started/dev-setup.md) – Detailed setup guide
- [Startup Scripts Guide](scripts/README.md) – All PowerShell/Bash scripts documented

### � Security & Features
- [�🔒 **PII Protection & Security Guide**](docs/PII_PROTECTION_GUIDE.md) ⭐ – Multi-layer redaction
- [Platform Features](docs/reference/features.md) – Complete feature catalog

### 🏗️ Architecture & Diagrams
- [System Architecture](docs/diagrams/architecture.md) – C4 component diagram
- [Data Flow Sequences](docs/diagrams/data-flow.md) – Upload, analysis, SSE streaming
- [Deployment Topology](docs/diagrams/deployment.md) – WSL 2 + Docker infrastructure
- [PII Redaction Pipeline](docs/diagrams/pii-pipeline.md) – Multi-pass security flowchart
- [ITSM Integration Flows](docs/diagrams/itsm-integration.md) – ServiceNow & Jira workflows

### 🚀 Operations & Deployment
- [Deployment Guide](docs/deployment/deployment-guide.md) – Production deployment
- [Troubleshooting Playbook](docs/operations/troubleshooting.md) – Common issues & fixes

### 📖 Reference
- [Full Documentation Index](docs/index.md) – Complete docs catalog
- [Historical Archive](docs/archive/HISTORICAL_NOTES.md) – Legacy fixes & completion reports

---

## Highlights

- **🔒 PII Protection** – Multi-pass redaction with strict validation protects 30+ sensitive data types before any LLM or storage operations ([architecture diagram](docs/diagrams/pii-pipeline.md)).
- **Investigation pipeline** – FastAPI API + async worker coordinate redaction, embeddings (pgvector), retrieval, and LLM reasoning while emitting friendly `analysis-progress` events ([data flow diagrams](docs/diagrams/data-flow.md)).
- **Flexible LLM providers** – Toggle between GitHub Copilot, OpenAI, Bedrock, Anthropic, LM Studio, or vLLM with per-job overrides.
- **ITSM ready** – Ticket adapters for ServiceNow and Jira, structured outputs (Markdown/HTML/JSON), and optional dry-run previews ([integration workflows](docs/diagrams/itsm-integration.md)).
- **Observability** – Prometheus metrics, structured logs, and optional Grafana dashboards.
- **Next.js UI** – Upload artefacts, monitor live progress with real-time redaction stats, and review investigation transcripts.

See the [Architecture Overview](docs/diagrams/architecture.md) for a complete system diagram and the [Deployment Topology](docs/diagrams/deployment.md) for infrastructure setup.

---

## Local Development

> **⚠️ IMPORTANT - Docker via WSL Required**  
> This project uses **Docker Engine inside WSL 2**, NOT Docker Desktop on Windows.  
> Docker Desktop is typically blocked in enterprise environments. All startup scripts  
> (`quick-start-dev.ps1`, `start-dev.ps1`, etc.) invoke `wsl.exe` to run `docker compose`  
> inside your WSL distribution. Ensure Docker is installed and running in WSL before starting.

The fastest path is the consolidated quickstart:

```powershell
.\quick-start-dev.ps1
```

This launches the database containers (via WSL Docker), backend API (with reload), Next.js UI, optional worker, and Copilot proxy in dedicated terminals. Flags such as `-IncludeWorker`, `-NoWorker`, and `-NoBrowser` control behaviour.

Prefer more control? Follow the steps outlined in the [Developer Environment Setup](docs/getting-started/dev-setup.md) guide to run services manually via `start-dev.ps1`, Uvicorn, and `npm run dev`.

---

## Testing & Quality

```powershell
.\venv\Scripts\activate
python -m pytest

# Run Playwright UI smoke tests
cd tests\playwright
npm install   # first run only
npm test
```

Add linters or type-checkers (e.g. `ruff`, `mypy`) via your preferred workflow.

---

## Repository Map

```
apps/          FastAPI application and worker entry points
core/          Domain logic (config, jobs, LLM, privacy, tickets, prompts)
deploy/        Dockerfiles, compose stacks, monitoring profiles
docs/          📚 Consolidated documentation hub
  ├── diagrams/      Mermaid architecture & flow diagrams
  ├── getting-started/  Setup and quickstart guides
  ├── operations/    Troubleshooting and operational playbooks
  ├── deployment/    Production deployment guides
  ├── reference/     API docs, features, architecture
  └── archive/       Historical fixes and completion reports
scripts/       🔧 PowerShell/Bash automation and validation utilities
tools/         Manual testing utilities and sample payloads
ui/            Next.js 14 frontend (TypeScript, Tailwind, Zustand)
tests/         Pytest + Playwright test suites
  ├── integration/   Integration tests
  ├── unit/          Unit tests
  └── debug/         Temporary debugging scripts (not in CI)
```

**Key Files**:
- `quick-start-dev.ps1` – One-command full stack startup
- `scripts/README.md` – Complete script documentation
- `docs/index.md` – Full documentation catalog
- `docs/diagrams/README.md` – Visual documentation hub

---

## Contributing

1. Create a feature branch.
2. Run tests and update documentation when behaviour changes.
3. Open a pull request targeting `master`.

Please avoid checking in secrets—use `.env` locally and CI/CD vaults in production.
