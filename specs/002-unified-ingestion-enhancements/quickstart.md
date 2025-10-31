# Quickstart: Unified Ingestion Intelligence Enhancements

## Prerequisites
- Python 3.11 environment with project dependencies installed (`pip install -e .[dev]`).
- PostgreSQL instance with pgvector extension enabled and database migrations applied.
- Redis service running for job queueing/telemetry buffering.
- Node.js 18+ for the Next.js UI.
- Feature flags `related_incidents`, `platform_detection`, and `archive_expanded_formats` enabled in configuration.

## 1. Start Services
```pwsh
# From repository root
./start-dev.ps1
```
- Verifies API available at `http://localhost:8001` and UI at `http://localhost:3000`.

## 2. Seed Test Data
```pwsh
# Load sample incidents and embeddings
python scripts/pipeline/bootstrap_similarity.py --fixtures sample-data/incidents
```
- Populates historical fingerprints for search regression tests.

## 3. Run Ingestion Scenario
```pwsh
# Upload new archive via CLI helper
python scripts/pipeline/ingest_archive.py --path sample-data/archives/platform_mix.tar.gz --tenant demo-tenant
```
- Confirms expanded archive handling and platform detection results appear in job metadata.

## 4. Validate Related Incident Search
```pwsh
# Smoke test API endpoint
http POST :8001/api/v1/incidents/search query="bot failure" scope=authorized_workspaces min_relevance:=0.6
```
- Response should include ranked matches and `audit_token` for UI logging.

## 5. UI Verification
1. Sign in as an analyst with access to multiple workspaces.
2. Open a completed session detail page.
3. Confirm the Related Incidents panel lists cross-workspace matches, supports relevance filtering, and records audit entries.

## 6. Run Test Suite
```pwsh
pytest tests/test_job_processor.py tests/test_llm_providers.py tests/test_metrics.py
npm --prefix ui test
```
- Ensures new detection/telemetry logic passes regression coverage.

## 7. Observability Checks
- Visit `http://localhost:8001/metrics` and confirm new counters for detection outcomes and archive safeguards.
- Inspect structured logs for `ArchiveExtractionAudit` entries after running ingestion scenarios.

## 8. Cleanup
```pwsh
./stop-dev.ps1
```
- Shuts down local services to avoid lingering resources.
