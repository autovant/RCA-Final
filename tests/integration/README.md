# Integration Test Suite

The integration tests require a running environment with the API, Prometheus, and (optionally) Thanos exposed over HTTP. Each test is disabled by default and only executes when the required environment variables are set.

## Required Environment Variables

| Variable | Description |
| --- | --- |
| `TELEMETRY_UPLOAD_COMMAND` | Shell command that triggers a representative 20 MB upload end-to-end (e.g., `httpie` call or bespoke script). Optional; set when the test should initiate the upload itself. |
| `PROMETHEUS_URL` | Base URL for Prometheus HTTP API, e.g., `http://prometheus:9090`. |
| `THANOS_QUERY_URL` | Base URL for Thanos query API (optional). When provided the test verifies remote rollups. |
| `TELEMETRY_TENANT_ID` | Tenant UUID to filter telemetry metrics. |
| `TELEMETRY_EXPECTED_STAGES` | Comma-separated list of pipeline stages to assert (defaults to `ingest,chunk,embed,cache,storage`). |
| `TELEMETRY_METRIC_TIMEOUT` | Time in seconds to wait for metrics to appear (default: `60`). |
| `SMOKE_COMMAND` | Command that executes the smoke suite against a deployment (e.g., `pytest tests/smoke/test_file_encoding.py`). |
| `SMOKE_EXPECT_EXIT` | Expected exit code for the smoke command (default: `1`). |

## Running

```bash
# Example: run telemetry metric verification once environment variables are set
pytest tests/integration/test_telemetry_prometheus.py

# Example: assert smoke suite fails the deployment gate
pytest tests/integration/test_smoke_gate.py
```
