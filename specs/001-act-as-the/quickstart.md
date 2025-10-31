# Quickstart – File Upload & RAG Pipeline Enhancements

## Prerequisites
- Python 3.11 environment with project dependencies installed (`pip install -r requirements.txt`).
- Running Postgres instance with pgvector extension enabled.
- Redis instance available for background job coordination.
- Feature branch `001-act-as-the` checked out locally.

## 1. Apply Database Changes
```bash
alembic upgrade head
python deploy/ops/embedding_cache_migration.py --apply
```
- Confirms `embedding_cache`, `chunk_quality_record`, and telemetry tables exist.
- Rollback command: `python deploy/ops/embedding_cache_migration.py --rollback`.

## 2. Enable Feature Flags for Staging Tenant
```bash
http PUT :8000/api/admin/tenants/{tenant_id}/feature-flags \
  "flags:= {\"telemetry\": true, \"compressed_ingest\": true, \"embedding_cache\": true, \"quality_retrieval\": false}" \
  "Authorization: Bearer <token>"
```
- Telemetry should be toggled first; hybrid retrieval can remain off until chunk quality metrics stabilize.

## 3. Configure Chunk Budgets
```bash
http PUT :8000/api/admin/tenants/{tenant_id}/chunking \
  default_token_budget:=900 \
  per_model:='{"gpt-4o": 850, "claude-3-sonnet": 950}' \
  "Authorization: Bearer <token>"
```
- Settings apply immediately without restart.

## 4. Execute Smoke & Unit Tests
```bash
pytest tests/smoke/test_file_ingest.py
pytest tests/worker/test_embedding_cache.py
pytest tests/retrieval/test_hybrid_retrieval.py
```
- Smoke run should cover UTF-8, UTF-16, malformed cases.
- Worker tests validate cache hit thresholds and eviction scheduling.

## 5. Validate Metrics
```bash
curl -s http://localhost:8001/metrics | grep rca_pipeline_stage
```
- Ensure counters and histograms for ingest, embed, cache, storage are exposed.
- Confirm `hybrid_retrieval_auto_disable_total` increments when latency guard triggers.

## 6. Snapshot Upload Distribution
```bash
python scripts/pipeline/snapshot_upload_distribution.py --limit 10 --output data/upload-snapshot.json
```
- Default JSON payload includes `captured_at`, scoped tenant list, and aggregated percentiles for the top 10 file extensions.
- Filter by tenant or date window when curating fixtures for a specific customer slice:
  ```bash
  python scripts/pipeline/snapshot_upload_distribution.py \
    --tenant-id 7d3d9a00-9e73-4e41-9d6f-0cbf5d5eb201 \
    --start "2025-09-01T00:00:00" \
    --end "2025-10-01T00:00:00" \
    --limit 5 \
    --output data/tenant-a-upload-snapshot.json
  ```
- Generate CSV directly to the console for quick review when selecting replacement files:
  ```bash
  python scripts/pipeline/snapshot_upload_distribution.py --format csv --limit 8
  ```
- After reviewing the extension mix and target percentiles, refresh smoke fixtures in `tests/smoke/files/` by sampling representative files that match the observed distribution (e.g., add a larger UTF-16 document if the snapshot shows 95th percentile >4 MB for `.txt`).

## 7. Turn On Hybrid Retrieval (Pilot)
```bash
http PUT :8000/api/admin/tenants/{tenant_id}/feature-flags \
  "flags:= {\"telemetry\": true, \"compressed_ingest\": true, \"embedding_cache\": true, \"quality_retrieval\": true}" \
  "Authorization: Bearer <token>"
```
- Monitor `HybridRetrievalStatus` endpoint until citation coverage ≥0.9 and P95 latency ≤1.5× baseline.
