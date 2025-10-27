# Quick Reference: New Features API

## File Watcher Phase 2/3

### Timeline & Events
```python
from core.watchers import get_watcher_timeline, WatcherEvent

timeline = get_watcher_timeline()
await timeline.start()

# Record event
event = WatcherEvent(
    event_type="created",
    path="/data/file.log",
    timestamp=datetime.utcnow(),
    pattern_matched="*.log",
    processor="log_ingestion"
)
await timeline.record_event(event)

# Query events
events = await timeline.get_events(
    limit=50,
    event_type="created",
    since=datetime.utcnow() - timedelta(hours=1)
)

# Get statistics
stats = await timeline.get_stats()
print(f"Total: {stats.total_events}, Peak: {stats.peak_events_per_minute}/min")
```

### Pattern Testing
```python
from core.watchers import PatternTester, PatternType

# Test single pattern
result = PatternTester.test_pattern("*.log", "/data/app.log", PatternType.GLOB)
print(f"Matches: {result.matches}")

# Validate pattern
validation = PatternTester.validate_pattern("*.{log,txt}", PatternType.GLOB)
print(f"Valid: {validation['valid']}, Warnings: {validation['warnings']}")
```

### Presets
```python
from core.watchers import get_preset_registry

registry = get_preset_registry()

# Get built-in preset
logs_preset = registry.get_preset("logs")
config = logs_preset.to_config()

# List all presets
presets = registry.list_presets(category="data")
```

### Scheduling
```python
from core.watchers import WatcherSchedule
from datetime import time

schedule = WatcherSchedule(
    enabled=True,
    cron_expression="0 */6 * * *",  # Every 6 hours
    start_time=time(9, 0),
    end_time=time(17, 0),
    days_of_week={0, 1, 2, 3, 4}  # Mon-Fri
)

if schedule.is_active():
    # Process files
    pass
```

### Cloud Storage
```python
from core.watchers import S3StorageBackend, AzureBlobStorageBackend

# S3
s3 = S3StorageBackend(
    bucket="my-bucket",
    prefix="logs/",
    region="us-east-1"
)
content = await s3.read("app.log")

# Azure
azure = AzureBlobStorageBackend(
    container="logs",
    connection_string="..."
)
files = await azure.list(prefix="2025/")
```

## Telemetry

### Embedding Cache
```python
from core.metrics.enhanced_collectors import EmbeddingCacheMetrics

metrics = EmbeddingCacheMetrics(model="text-embedding-ada-002")

# Record hit
with metrics.lookup_timer(hit=True):
    result = cache.get(key)
metrics.record_hit(dimension=1536)

# Record miss + generation
with metrics.lookup_timer(hit=False):
    result = cache.get(key)
metrics.record_miss()

with metrics.generation_timer():
    embedding = model.embed(text)
```

### Compressed Ingestion
```python
from core.metrics.enhanced_collectors import CompressedIngestionMetrics

metrics = CompressedIngestionMetrics(format="zip")

with metrics.extraction_timer():
    extract_archive(path)

metrics.record_success(
    original_bytes=1024000,
    extracted_bytes=5120000,
    file_count=42,
    duration_seconds=2.5
)
```

### Validation
```python
from core.metrics.enhanced_collectors import TelemetryValidator

# Validate specific component
results = TelemetryValidator.validate_embedding_cache()
print(results["status"])  # "healthy" or "unhealthy"

# Validate all
all_results = TelemetryValidator.validate_all()
```

## RPA Platform Adapters

```python
from core.files.rpa_adapters import get_rpa_registry

registry = get_rpa_registry()

# Detect platform
platform, confidence, adapter = registry.detect_platform(
    content=log_content,
    filename="robot.log"
)
print(f"Platform: {platform.value}, Confidence: {confidence:.2%}")

# Parse logs
entries = registry.parse_logs(content, adapter=adapter)
for entry in entries:
    print(f"{entry.timestamp} [{entry.level}] {entry.message}")
    if entry.error_code:
        print(f"  Error: {entry.error_code}")
```

## Enhanced Archives

```python
from core.files.enhanced_archives import get_enhanced_extractor

extractor = get_enhanced_extractor()

# Check format support
formats = extractor.supported_formats()
print(f"Supported: {formats}")

# Extract archive
info = await extractor.extract(
    archive_path=Path("data.7z"),
    extract_to=Path("/tmp/extracted")
)
print(f"Extracted {info.file_count} files")
print(f"Compression ratio: {info.metadata['extracted_size'] / info.compressed_size:.1f}x")

# List without extracting
files = await extractor.list_contents(Path("data.rar"))
```

## ML Pipeline Tuning

```python
from core.jobs.ml_tuning import get_ml_optimizer, OptimizationStrategy

optimizer = get_ml_optimizer()

# Record execution
optimizer.record_stage_execution(
    stage="parse_logs",
    duration_ms=150.5,
    success=True,
    items_processed=10,
    queue_depth=5
)

# Get recommendations
recs = optimizer.generate_recommendations()
for rec in recs:
    print(f"{rec.stage}.{rec.parameter}: {rec.current_value} → {rec.recommended_value}")
    print(f"  Expected improvement: {rec.expected_improvement:.1%}")
    print(f"  Reason: {rec.reason}")

# Detect bottleneck
bottleneck = optimizer.detect_bottleneck()
if bottleneck:
    print(f"Bottleneck detected: {bottleneck}")

# Get stage summary
summary = optimizer.get_stage_summary("parse_logs")
print(f"Success rate: {summary['success_rate']:.2%}")
print(f"P95 latency: {summary['p95_duration_ms']:.1f}ms")
```

## Multi-Tenant Guardrails

```python
from core.jobs.distributed import get_tenant_guardrails, TenantPlan

guardrails = get_tenant_guardrails()

# Register tenant
await guardrails.register_tenant(
    tenant_id="acme-corp",
    plan=TenantPlan.PROFESSIONAL
)

# Check quota
allowed, reason = await guardrails.check_job_quota("acme-corp")
if not allowed:
    raise QuotaExceeded(reason)

# Track usage
await guardrails.track_job_start("acme-corp")
try:
    # Process job
    pass
finally:
    await guardrails.track_job_complete("acme-corp")

# Check feature access
if await guardrails.check_feature_access("acme-corp", "ml_insights"):
    # Enable ML features
    pass

# Get usage summary
usage = await guardrails.get_usage_summary("acme-corp")
print(f"Jobs: {usage['current_usage']['jobs_this_hour']}/{usage['quota']['max_jobs_per_hour']}")
print(f"Concurrent: {usage['limits_percentage']['concurrent']:.1f}%")
```

## Distributed Job Scheduler

```python
from core.jobs.distributed import get_distributed_scheduler

scheduler = get_distributed_scheduler()

# Register workers
await scheduler.register_worker(
    node_id="worker-01",
    hostname="10.0.1.5",
    capacity=10,
    capabilities={"gpu", "ml"},
    region="us-east-1"
)

# Assign job
node_id = await scheduler.assign_job(
    job_id="job-123",
    required_capabilities={"gpu"},
    preferred_region="us-east-1",
    priority=8
)
print(f"Assigned to: {node_id}")

# Release when done
await scheduler.release_job("job-123")

# Monitor cluster
status = await scheduler.get_cluster_status()
print(f"Workers: {status['healthy_workers']}/{status['total_workers']}")
print(f"Utilization: {status['utilization_percent']:.1f}%")
```

## AI-Guided Troubleshooting

```python
from core.jobs.distributed import get_ai_troubleshooter

troubleshooter = get_ai_troubleshooter()

# Analyze error
hints = troubleshooter.analyze_error(
    error_message="Connection refused to database on port 5432",
    context={"service": "postgres", "host": "db.example.com"}
)

for hint in hints:
    print(f"\n[{hint.severity.upper()}] {hint.issue}")
    print(f"Action: {hint.suggested_action}")
    print(f"Why: {hint.explanation}")
    print(f"Confidence: {hint.confidence:.0%}")
```

## Feature Showcase (React/TypeScript)

```tsx
import {
  FeedbackPanel,
  DemoAnalyticsTracker,
  ComparisonView,
  ExportButton,
  ShareButton
} from "@/components/demo/InteractiveDemo";

// Feedback
<FeedbackPanel
  demoId="rpa-demo-001"
  onSubmit={(feedback) => console.log(feedback)}
  categories={["Accuracy", "Speed", "Ease of Use"]}
/>

// Analytics
const tracker = new DemoAnalyticsTracker("demo-001", 5);
tracker.trackInteraction("button_click", { button: "start" });
tracker.trackStepComplete();
const analytics = tracker.complete();

// Comparison
<ComparisonView
  title="PII Redaction Results"
  results={[
    {
      label: "Email Addresses",
      before: "user@example.com",
      after: "[EMAIL_REDACTED]",
      improvement: "100% sensitive data removed"
    }
  ]}
/>

// Export
<ExportButton
  data={results}
  filename="demo-results"
  format="json"
  label="Download Results"
/>

// Share
<ShareButton
  demoId="rpa-demo-001"
  results={demoResults}
  label="Share Demo"
/>
```

## Prometheus Queries

```promql
# Cache hit rate
rate(rca_embedding_cache_hits_total[5m]) /
(rate(rca_embedding_cache_hits_total[5m]) + rate(rca_embedding_cache_misses_total[5m]))

# Average compression ratio
avg(rca_compressed_ingestion_compression_ratio) by (format)

# Pipeline throughput
rate(rca_pipeline_stage_duration_seconds_count[5m])

# Pipeline P95 latency
histogram_quantile(0.95, rate(rca_pipeline_stage_duration_seconds_bucket[5m]))

# Unhealthy telemetry
rca_telemetry_health_status == 0
```

## Configuration Examples

### Watcher Multi-Config
```yaml
watchers:
  - config_id: "logs-watcher"
    name: "Production Logs"
    watch_path: "/var/log/app"
    patterns: ["*.log"]
    processor: "log_ingestion"
    schedule:
      cron_expression: "*/5 * * * *"
    webhook:
      url: "https://api.example.com/webhooks/logs"
      method: "POST"
    priority: 10

  - config_id: "rpa-watcher"
    name: "RPA Reports"
    watch_path: "/data/rpa"
    patterns: ["*.xlsx"]
    processor: "rpa_ingestion"
    schedule:
      start_time: "09:00"
      end_time: "17:00"
    priority: 5
```

### Tenant Configuration
```yaml
tenants:
  - tenant_id: "acme-corp"
    plan: "professional"
    custom_quota:
      max_jobs_per_hour: 500
      max_concurrent_jobs: 20
      features:
        - "ml_insights"
        - "custom_processors"
        - "webhook_notifications"

  - tenant_id: "startup-inc"
    plan: "starter"
```

### Distributed Cluster
```yaml
workers:
  - node_id: "worker-01"
    hostname: "10.0.1.5"
    capacity: 10
    capabilities: ["gpu", "ml"]
    region: "us-east-1"

  - node_id: "worker-02"
    hostname: "10.0.1.6"
    capacity: 20
    capabilities: ["cpu"]
    region: "us-west-2"
```
