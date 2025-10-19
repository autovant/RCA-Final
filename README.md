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

- [Quickstart Checklist](docs/getting-started/quickstart.md)
- [Developer Environment Setup](docs/getting-started/dev-setup.md)
- [🔒 **PII Protection & Security Guide**](docs/PII_PROTECTION_GUIDE.md) ⭐
- [Deployment Guide](docs/deployment/deployment-guide.md)
- [Startup & Helper Scripts](docs/operations/startup-scripts.md)
- [Platform Features](docs/reference/features.md)

The full documentation index lives at [`docs/index.md`](docs/index.md). Historical fix logs and legacy guides have been moved into [`docs/archive/`](docs/archive/README.md).

---

## Highlights

- **🔒 PII Protection** – Multi-pass redaction with strict validation protects 30+ sensitive data types before any LLM or storage operations.
- **Investigation pipeline** – FastAPI API + async worker coordinate redaction, embeddings (pgvector), retrieval, and LLM reasoning while emitting friendly `analysis-progress` events.
- **Flexible LLM providers** – Toggle between GitHub Copilot, OpenAI, Bedrock, Anthropic, LM Studio, or vLLM with per-job overrides.
- **ITSM ready** – Ticket adapters for ServiceNow and Jira, structured outputs (Markdown/HTML/JSON), and optional dry-run previews.
- **Observability** – Prometheus metrics, structured logs, and optional Grafana dashboards.
- **Next.js UI** – Upload artefacts, monitor live progress with real-time redaction stats, and review investigation transcripts.

See the [Architecture Overview](docs/reference/architecture.md) for a component diagram and data flow summary.

---

## Local Development

The fastest path is the consolidated quickstart:

```powershell
.\quick-start-dev.ps1
```

This launches the database containers, backend API (with reload), Next.js UI, optional worker, and Copilot proxy in dedicated terminals. Flags such as `-IncludeWorker`, `-NoWorker`, and `-NoBrowser` control behaviour.

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
apps/       FastAPI application and worker entry points
core/       Domain logic (config, jobs, LLM, privacy, tickets)
deploy/     Dockerfiles, compose stacks, monitoring profiles
docs/       Consolidated documentation hub (+ archive)
scripts/    Automation helpers and CI utilities
tools/      Manual testing utilities and sample payloads
ui/         Next.js frontend
tests/      Pytest + Playwright suites
```

---

## Contributing

1. Create a feature branch.
2. Run tests and update documentation when behaviour changes.
3. Open a pull request targeting `master`.

Please avoid checking in secrets—use `.env` locally and CI/CD vaults in production.
