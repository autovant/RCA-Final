# Quick Start Guide - New Features

## Installation

1. **Install dependencies:**
```powershell
pip install -r requirements.txt
```

2. **Verify installation:**
```powershell
python -c "import croniter, aioboto3, azure.storage.blob; print('All dependencies installed!')"
```

## File Watcher System

### Using Timeline Tracking
```python
from core.watchers.timeline import get_watcher_timeline

# Get timeline instance
timeline = get_watcher_timeline()
await timeline.start()

# Get recent events
events = await timeline.get_events(limit=50)

# Get statistics
stats = await timeline.get_stats(hours=24)
print(f"Total events: {stats.total_events}")
print(f"Average processing time: {stats.avg_processing_time_ms}ms")

# Subscribe to real-time events
queue = await timeline.subscribe()
while True:
    event = await queue.get()
    print(f"New event: {event.event_type} - {event.path}")
```

### Using Pattern Testing
```python
from core.watchers.patterns import PatternTester, PatternType

# Test a pattern
result = PatternTester.test_pattern(
    "*.log",
    "/var/log/app.log",
    PatternType.GLOB
)
print(f"Matches: {result.matches}")

# Test multiple paths
paths = ["/data/file1.csv", "/data/file2.txt"]
results = PatternTester.test_multiple_paths("*.csv", paths, PatternType.GLOB)
```

### Using Presets
```python
from core.watchers.patterns import get_preset_registry

registry = get_preset_registry()

# Get logs preset
logs_preset = registry.get_preset("logs")
print(f"Patterns: {logs_preset.patterns}")

# Convert to watcher config
config = logs_preset.to_config()
# Use config with watcher manager
```

### Scheduling Watchers
```python
from core.watchers.advanced import WatcherSchedule

# Run every hour
schedule = WatcherSchedule(
    cron_expr="0 * * * *",
    timezone="America/New_York"
)

# Check if should run
if await schedule.should_run():
    print("Time to run!")
    
# Get next run time
next_run = schedule.get_next_run()
print(f"Next run at: {next_run}")
```

## Telemetry & Metrics

### Embedding Cache Metrics
```python
from core.metrics.enhanced_collectors import EmbeddingCacheMetrics

metrics = EmbeddingCacheMetrics(model="text-embedding-ada-002", dimension=1536)

# Record cache hit
with metrics.lookup_timer(hit=True):
    # Perform lookup
    pass
metrics.record_hit()

# Record cache miss + generation
with metrics.lookup_timer(hit=False):
    pass
metrics.record_miss()

with metrics.generation_timer(cached=False):
    # Generate embedding
    pass

# Update cache size
metrics.update_size(size_bytes=50000000, entry_count=10000)
```

### Compression Metrics
```python
from core.metrics.enhanced_collectors import CompressedIngestionMetrics

metrics = CompressedIngestionMetrics(format="zip")

with metrics.extraction_timer():
    # Extract archive
    pass

metrics.record_success(
    original_bytes=10_000_000,
    extracted_bytes=50_000_000,
    file_count=150,
    duration_seconds=3.5
)
```

### Validation
```python
from core.metrics.enhanced_collectors import TelemetryValidator

# Validate all systems
results = TelemetryValidator.validate_all()
print(f"Status: {results['status']}")
for component, status in results['components'].items():
    print(f"{component}: {status['status']}")
```

## RPA Platform Support

### Auto-Detect Platform
```python
from core.files.rpa_adapters import RPAPlatformRegistry

registry = RPAPlatformRegistry()

# Read log file
with open("automation_log.txt") as f:
    log_content = f.read()

# Detect platform
adapter = registry.detect_platform(log_content)
if adapter:
    print(f"Detected: {adapter.platform}")
    
    # Parse logs
    entries = adapter.parse_logs(log_content)
    for entry in entries:
        print(f"{entry['timestamp']}: {entry['message']}")
```

### Platform-Specific Parsing
```python
from core.files.rpa_adapters import AutomationAnywhereAdapter

adapter = AutomationAnywhereAdapter()

# Check if this is AA logs
confidence = adapter.detect(log_content)
if confidence > 0.5:
    entries = adapter.parse_logs(log_content)
    # Process entries
```

## Archive Formats

### Extract Archives
```python
from core.files.enhanced_archives import EnhancedArchiveExtractor
from pathlib import Path

# Auto-detect and extract
result = await EnhancedArchiveExtractor.extract(
    Path("/data/archive.7z"),
    Path("/data/output")
)

if result.success:
    print(f"Extracted {result.file_count} files")
    print(f"Compression ratio: {result.compression_ratio:.2f}x")
else:
    print(f"Error: {result.error}")
```

### Format-Specific
```python
from core.files.enhanced_archives import SevenZipExtractor

extractor = SevenZipExtractor()

if await extractor.can_handle(Path("data.7z")):
    info = await extractor.extract(
        Path("data.7z"),
        Path("output")
    )
    print(f"Extracted in {info.duration_seconds:.2f}s")
```

## Multi-Tenant Management

### Check Quota
```python
from core.jobs.distributed import TenantGuardrails

guardrails = TenantGuardrails()

# Check if tenant can submit job
allowed = await guardrails.check_quota(
    tenant_id="tenant123",
    job_type="analysis",
    estimated_cost=5.0
)

if not allowed:
    usage = await guardrails.get_usage("tenant123")
    print(f"Quota exceeded. Used {usage['jobs_today']} jobs today")
```

### Upgrade Plan
```python
# Upgrade to professional
success = await guardrails.upgrade_plan("tenant123", "professional")

# New limits apply immediately
quota = guardrails._quotas["tenant123"]
print(f"New daily limit: {quota.max_jobs_per_day}")
```

## ML Pipeline Optimization

### Track Performance
```python
from core.jobs.ml_tuning import MLPipelineOptimizer

optimizer = MLPipelineOptimizer()

# Record stage completion
optimizer.record_stage_completion(
    stage="embedding",
    duration_ms=150.0,
    success=True
)

# Detect bottlenecks
bottlenecks = optimizer.detect_bottlenecks()
for rec in bottlenecks:
    print(f"Bottleneck in {rec.stage}: {rec.diagnosis}")
    print(f"Suggestion: {rec.suggestion}")
```

### Optimize Batch Size
```python
# Test different batch sizes
test_data = [
    (10, 100.0),   # batch_size, throughput
    (50, 400.0),
    (100, 500.0),
    (200, 450.0),
]

rec = optimizer.optimize_batch_size("processing", test_data)
print(f"Optimal batch size: {rec.suggested_value}")
```

## API Usage

### Submit Feedback
```bash
curl -X POST http://localhost:8000/api/feedback/demo \
  -H "Content-Type: application/json" \
  -d '{
    "demo_id": "incident_analysis_demo",
    "rating": 5,
    "comments": "Great feature!",
    "feature_requests": ["Export to PDF", "Dark mode"]
  }'
```

### Create Share Link
```bash
curl -X POST http://localhost:8000/api/share/demo \
  -H "Content-Type: application/json" \
  -d '{
    "title": "My Demo Configuration",
    "demo_config": {"filters": {"severity": "high"}},
    "expires_hours": 24
  }'
```

### Check Health
```bash
# Overall health
curl http://localhost:8000/health

# Telemetry health
curl http://localhost:8000/health/telemetry

# Cluster health
curl http://localhost:8000/health/cluster
```

### Tenant Management
```bash
# Get usage
curl http://localhost:8000/api/tenant/tenant123/usage

# Upgrade plan
curl -X PUT http://localhost:8000/api/tenant/tenant123/quota \
  -H "Content-Type: application/json" \
  -d '{"plan": "professional"}'

# Check quota
curl -X POST http://localhost:8000/api/tenant/tenant123/jobs/check-quota \
  -H "Content-Type: application/json" \
  -d '{
    "job_type": "analysis",
    "payload": {},
    "estimated_cost": 5.0
  }'
```

## Running Tests

```powershell
# All watcher tests
pytest tests/test_watcher_timeline.py -v

# All telemetry tests
pytest tests/test_telemetry_collectors.py -v

# RPA adapter tests
pytest tests/test_rpa_and_archives.py::TestAutomationAnywhereAdapter -v

# Specific test
pytest tests/test_watcher_timeline.py::TestPatternTester::test_glob_pattern_match -v

# With coverage
pytest tests/ --cov=core --cov-report=html
```

## Prometheus Queries

```promql
# Embedding cache hit rate
rate(embedding_cache_hits_total[5m]) / 
(rate(embedding_cache_hits_total[5m]) + rate(embedding_cache_misses_total[5m]))

# Average extraction time by format
rate(compressed_ingestion_duration_seconds_sum[5m]) / 
rate(compressed_ingestion_duration_seconds_count[5m])

# Compression effectiveness
avg(compressed_ingestion_compression_ratio) by (format)

# Watcher event rate
rate(watcher_events_total[5m])

# ML pipeline bottlenecks
sum(ml_pipeline_bottleneck_detected) by (stage)
```

## Troubleshooting

### Missing Dependencies
```powershell
# Check what's installed
pip list | grep -E "(croniter|aioboto3|azure-storage)"

# Reinstall
pip install --force-reinstall croniter aioboto3 azure-storage-blob
```

### Import Errors
```python
# Test imports
python -c "from core.watchers.timeline import get_watcher_timeline; print('OK')"
python -c "from core.metrics.enhanced_collectors import EmbeddingCacheMetrics; print('OK')"
python -c "from core.files.rpa_adapters import RPAPlatformRegistry; print('OK')"
```

### Test Failures
```powershell
# Run with verbose output
pytest tests/test_watcher_timeline.py -vvs

# Run single test
pytest tests/test_watcher_timeline.py::TestWatcherTimeline::test_record_event -vvs

# Show print statements
pytest tests/test_telemetry_collectors.py -s
```

### API Errors
```bash
# Check logs
tail -f deploy/logs/api.log

# Test endpoint
curl -v http://localhost:8000/health

# Check database connection
curl http://localhost:8000/health/database
```

## Next Steps

1. ✅ Dependencies installed
2. ✅ Core features implemented  
3. ✅ Tests created (40+ passing)
4. ⏳ Database migrations (create tables for demo feedback, analytics, shares)
5. ⏳ Frontend integration (wire up InteractiveDemo components)
6. ⏳ Monitoring setup (Prometheus + Grafana dashboards)
7. ⏳ Production deployment

See `docs/IMPLEMENTATION_COMPLETE_SUMMARY.md` for full details.
