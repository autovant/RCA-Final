# Unified Ingestion Metrics

Prometheus metrics emitted by the ingestion pipeline have been expanded to cover platform detection outcomes and archive extraction guardrails. Metrics share the global registry exposed in `core.metrics.registry` and surface at `/metrics` for both API and worker components.

## Platform Detection

### `rca_platform_detection_total`
- **Type**: Counter
- **Description**: Number of platform detection attempts grouped by outcome.
- **Labels**:
  - `tenant_id` – UUID of the tenant running ingestion.
  - `platform` – detected platform or `unknown`.
  - `outcome` – high-level result (e.g., `success`, `low_confidence`, etc.).
  - `parser_executed` – `yes` or `no` string derived from parser execution flag.
  - `detection_method` – detection approach (heuristic, ml model, etc.).
  - `feature_flags` – pipe-delimited list of active rollout flags influencing detection.
- **Emitted By**: `core.metrics.collectors.observe_detection` when platform detection completes.

### `rca_platform_detection_confidence`
- **Type**: Histogram (buckets: `0.1`, `0.25`, `0.5`, `0.75`, `0.9`, `0.99`, `1.0`)
- **Description**: Confidence score distribution for detection attempts.
- **Labels**: `tenant_id`, `platform`, `detection_method`.
- **Notes**: Scores are clamped to `[0,1]` prior to recording.

### `rca_platform_detection_duration_seconds`
- **Type**: Histogram (buckets: `0.05`, `0.1`, `0.25`, `0.5`, `1`, `2`, `5`, `10`, `30`)
- **Description**: Execution time for detection routines and optional parsers.
- **Labels**: `tenant_id`, `platform`, `detection_method`.

## Archive Guardrails

### `rca_archive_guardrail_total`
- **Type**: Counter
- **Description**: Aggregates archive guardrail decisions by status.
- **Labels**:
  - `tenant_id`
  - `archive_type` – archive container (zip, tar_xz, etc.).
  - `status` – `passed`, `blocked_ratio`, `blocked_members`, `timeout`, or `error`.
  - `feature_flags` – active rollout flags relevant to archive handling.
  - `blocked_reason` – human-readable cause when status is blocked or errored.
- **Emitted By**: `core.metrics.collectors.observe_archive_guardrail`.

### `rca_archive_decompression_ratio`
- **Type**: Histogram (buckets: `1`, `5`, `10`, `25`, `50`, `100`, `250`, `500`, `1000`)
- **Description**: Distribution of decompression ratios observed during extraction.
- **Labels**: `tenant_id`, `archive_type`, `status`.

### `rca_archive_member_count`
- **Type**: Histogram (buckets: `1`, `5`, `10`, `25`, `50`, `100`, `250`, `500`, `1000`)
- **Description**: Archive member counts recorded when extraction completes or is blocked.
- **Labels**: `tenant_id`, `archive_type`, `status`.

## Integration Guidance

- Metrics emit via shared registry to ensure compatibility with existing Grafana dashboards; add panels by referencing the names above.
- Structured logging helpers (`log_platform_detection_event`, `log_archive_guardrail_event`) mirror the label set, allowing correlation between logs and metrics.
- For environments requiring different rollout thresholds, adjust the configuration variables documented in `docs/operations/feature-flags.md`; the metrics automatically reflect new limits.
- Unit tests covering metric emission live under `tests/test_metrics.py`; update snapshots or assertions when label sets change.
