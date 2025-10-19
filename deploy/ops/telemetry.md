# Telemetry Runbook

**Audience:** On-call engineers and SREs responsible for ingestion pipeline health.

This runbook covers enabling the enhanced telemetry feature flag, validating metrics and dashboards, and rolling back if regressions occur.

---

## 1. Prerequisites
- Feature branch `001-act-as-the` deployed to the target environment.
- Database migrations applied (`alembic upgrade head`).
- `UploadTelemetryEventRecord` table present with indexes.
- Prometheus, Alertmanager, and Grafana reachable.

---

## 2. Enablement Procedure
1. **Confirm baseline:**
   - Run `curl -s $API_HOST/metrics | grep rca_pipeline_stage_total`.
   - Expect no series or only legacy counters if feature flag disabled.
2. **Toggle feature flag:**
   - Execute:
     ```bash
     http PUT $API_HOST/api/admin/tenants/{tenant_id}/feature-flags \
       "flags:= {\"telemetry_enhanced_metrics_enabled\": true}" \
       "Authorization: Bearer $ADMIN_TOKEN"
     ```
   - Apply per tenant or use `all-tenants` admin endpoint when available.
3. **Warmup validation:**
   - Upload a 5–10 MB UTF-8 text file through the UI or API.
   - Within 30 seconds verify Prometheus shows the new metrics (see Section 3).
4. **Document change:**
   - Update the environment change log with timestamp, tenant scope, and operator initials.

---

## 3. Post-Enablement Checks
- **Prometheus Metrics:**
  ```promql
  sum by (stage, status) (
    increase(rca_pipeline_stage_total{tenant="{tenant_id}"}[5m])
  )
  ```
  - Expect counts for `ingest` and `chunk` at minimum.
- **Latency Histograms:**
  ```promql
  histogram_quantile(0.95,
    sum by (le, stage) (
      rate(rca_pipeline_stage_duration_seconds_bucket{tenant="{tenant_id}"}[5m])
    )
  )
  ```
  - Ensure values < 60s; high values trigger investigation.
- **Telemetry Events:**
  ```sql
  SELECT stage, status, duration_ms
  FROM upload_telemetry_events
  WHERE tenant_id = '{tenant_uuid}'
  ORDER BY created_at DESC
  LIMIT 20;
  ```
  - Confirm recent rows exist for each stage.
- **Dashboards:**
  - Open Grafana dashboard `Telemetry / Pipeline Overview`.
  - Verify panels populate without errors and match Prometheus results.
- **Alerts:**
  - Ensure no active alerts for `TelemetryPipelineStall` or `TelemetryLoss` (see Alert Definitions).

---

## 4. Alert Definitions
| Alert | Expression | Action |
| --- | --- | --- |
| `TelemetryPipelineStall` | `increase(rca_pipeline_stage_total[15m]) == 0` for ingest stage | Investigate API/worker availability before route flapping. |
| `TelemetryLoss` | `absent_over_time(rca_pipeline_stage_total[10m])` | Check exporter logs, ensure feature flag still enabled. |
| `TelemetryLatencyHigh` | `histogram_quantile(0.95, rate(rca_pipeline_stage_duration_seconds_bucket[5m])) > 120` | Inspect worker logs, throttle uploads if necessary. |

Alert definitions live under `deploy/ops/alert-rules/telemetry.yml`. Update runbook if labels or thresholds change.

---

## 5. Troubleshooting
- **Metrics missing but telemetry table populated:**
  - Check application logs for Prometheus exporter exceptions.
  - Ensure `telemetry_enhanced_metrics_enabled` flag semantics match environment variable names.
- **Metrics present, but dashboards empty:**
  - Validate Grafana data source credentials.
  - Refresh dashboard JSON under `deploy/ops/dashboards/telemetry/`.
- **High stage latency:**
  - Inspect worker queue depth.
  - Review `PartialUploadTelemetry` metadata for skipped files or warnings indicating upstream issues.
- **Prometheus cardinality spike:**
  - Query `count_values("feature_flags", rca_pipeline_stage_total)` to identify noisy labels.
  - Work with developers to consolidate flag names or reduce scope.

---

## 6. Rollback Procedure
1. Disable feature flag:
   ```bash
   http PUT $API_HOST/api/admin/tenants/{tenant_id}/feature-flags \
     "flags:= {\"telemetry_enhanced_metrics_enabled\": false}" \
     "Authorization: Bearer $ADMIN_TOKEN"
   ```
2. Confirm metrics disappear from Prometheus within 5 minutes (`absent_over_time`).
3. Leave persisted telemetry records intact for postmortem analysis.
4. Log incident report referencing this runbook.

---

## 7. Verification After Rollback
- `curl -s $API_HOST/metrics | grep rca_pipeline_stage_total` returns no results.
- Grafana dashboard panels show `N/A` (expected).
- Alertmanager clears telemetry-related incidents.

---

## 8. Maintenance
- Review this runbook quarterly.
- Update alert thresholds to track SLA changes.
- Coordinate with feature team before modifying label sets or bucket boundaries.
- Ensure sampling CLI documentation stays in sync (`quickstart.md`, `docs/telemetry/overview.md`).

---

## Appendix
- **Related docs:**
  - `docs/telemetry/overview.md`
  - `specs/001-act-as-the/quickstart.md`
- **Contacts:**
  - Telemetry feature owner: `@telemetry-oncall`
  - SRE lead: `@sre-lead`

Keep this file under version control. Submit PRs for edits to guarantee review by the telemetry feature owner.
