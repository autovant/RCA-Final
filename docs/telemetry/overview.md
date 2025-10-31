# Telemetry Overview

The telemetry stack tracks ingestion health end to end so regressions surface before they reach production. This document explains the metrics, event records, retention profile, and primary dashboards added in Phase 0.

## Objectives
- Monitor ingest, chunk, embed, cache, and storage stages with consistent Prometheus metrics.
- Persist structured upload telemetry events for forensics and offline sampling.
- Expose derived dashboards and alerts that operations can trust during rollout and incidents.

## Metric Families
All metrics live under the `rca_` namespace. Each collector is registered in `core/metrics/pipeline_metrics.py`. Enable them by flipping the `telemetry_enhanced_metrics_enabled` flag.

### Counters
- `rca_pipeline_stage_total`
  - Type: Counter
  - Description: Number of stage executions grouped by outcome.
  - Increments for every stage attempt (success, partial, failure).

- `rca_embedding_cache_hits_total`
  - Type: Counter
  - Description: Count of cache hits served during embedding requests.

- `rca_embedding_cache_requests_total`
  - Type: Counter
  - Description: Total embedding cache lookups, hit or miss.

- `rca_hybrid_retrieval_auto_disable_total`
  - Type: Counter
  - Description: Tracks automatic hybrid retrieval disable events (future phases).

### Histograms
- `rca_pipeline_stage_duration_seconds`
  - Type: Histogram (default buckets: 0.1s, 0.5s, 1s, 2s, 5s, 10s, 30s, 60s, 120s)
  - Description: Measures stage latency for ingest, chunk, embed, cache, storage.

- `rca_embedding_cache_lookup_seconds`
  - Type: Histogram (future phase)
  - Description: Cache lookup timing once Phase 1 lands.

### Shared Labels
| Label | Description |
| --- | --- |
| `tenant` | Tenant UUID; `all` when metric aggregates across tenants. |
| `stage` | One of `ingest`, `chunk`, `embed`, `cache`, `storage`. |
| `file_type` | Normalized file extension (e.g., `txt`, `pdf`, `unknown`). |
| `size_category` | Discrete bucket derived from file size (`small`, `medium`, `large`). |
| `status` | Outcome label (`success`, `partial`, `failure`). |
| `feature_flags` | Comma separated list of active feature flags for the upload. |

Keep labels low cardinality. When adding new dimensions, confirm they align with Prometheus cardinality budgets (< 1M series per metric in production).

## Telemetry Event Records
The `UploadTelemetryEventRecord` model (see `core/db/models.py`) mirrors the in-memory metrics. Each record stores:
- `tenant_id`, `job_id`, `upload_id`
- Stage (`ingest`, `chunk`, `embed`, `cache`, `storage`)
- `feature_flags`: JSON dictionary of flags enabled during the run
- `status`: `success`, `partial`, or `failure`
- `duration_ms`, `started_at`, `completed_at`
- `metadata`: Structured payload for warnings, skipped counts, encoding probe output, and partial upload details provided by `PartialUploadTelemetry`

Use the events for:
- Root-cause analysis during incidents (filter by stage/status/time windows).
- Generating smoke fixture plans via `scripts/pipeline/snapshot_upload_distribution.py`.
- Reconciling Prometheus counters with persisted records.

## Sampling CLI
`scripts/pipeline/snapshot_upload_distribution.py` queries telemetry events joined with file metadata to produce distribution snapshots. The CLI supports tenant and time filtering, JSON or CSV output, and aligns with Quickstart guidance. See `quickstart.md` section 6 for command examples.

## PromQL Examples
- Stage throughput for the past hour:
  ```promql
  sum by (stage, status) (
    increase(rca_pipeline_stage_total{tenant="tenant-123"}[1h])
  )
  ```
- Stage latency percentiles:
  ```promql
  histogram_quantile(0.95,
    sum by (le, stage) (
      rate(rca_pipeline_stage_duration_seconds_bucket{tenant="tenant-123"}[5m])
    )
  )
  ```
- Cache hit ratio (Phase 1+):
  ```promql
  sum(rate(rca_embedding_cache_hits_total[5m]))
    /
  sum(rate(rca_embedding_cache_requests_total[5m]))
  ```

## Dashboards
Grafana dashboard JSON lives under `deploy/ops/dashboards/telemetry/`. Import it into a workspace configured with the Prometheus data source.

Key panels:
- Stage throughput (per stage, per tenant)
- Stage latency P50/P95/P99
- Partial upload warnings grouped by file type
- Telemetry event volume vs. pipeline job volume

Future phases will add embedding cache, chunk quality, and hybrid retrieval panels to the same board.

## Retention Strategy
- Prometheus server retains 30 days of raw samples locally.
- Remote write pushes to the managed Thanos bucket with 12-month downsampled retention (5m, 1h resolution).
- Alertmanager deduplicates alerts when Thanos replication fails; see `deploy/ops/telemetry.md` (T019) for on-call runbooks.

## Operational Checklist
1. Ensure `telemetry_enhanced_metrics_enabled` is ON before enabling new feature flags.
2. Validate ingestion metrics with a test upload: confirm counters increment and histograms report latency.
3. Verify smoke tests pass (`pytest tests/smoke/test_file_encoding.py`).
4. Generate a weekly snapshot via the sampling CLI to keep fixture library current.
5. Review dashboards and confirm alerts are silenced during maintenance windows.

## Future Enhancements
Phase 1+ work will extend this document with embedding cache metrics, compressed ingestion counters, and end-to-end telemetry validation procedures. Keep this file updated whenever new metric families or labels ship.
