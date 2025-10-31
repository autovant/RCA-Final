# Telemetry Validation Procedures

## Overview

This document describes validation procedures for the RCA Engine telemetry system, ensuring that metrics collectors are functioning correctly and providing accurate data.

## Telemetry Components

### 1. Embedding Cache Metrics

Tracks embedding cache performance and efficiency:

- **Hit/Miss Rates**: `rca_embedding_cache_hits_total`, `rca_embedding_cache_misses_total`
- **Cache Size**: `rca_embedding_cache_size_bytes`, `rca_embedding_cache_entries_total`
- **Performance**: `rca_embedding_cache_lookup_duration_seconds`, `rca_embedding_generation_duration_seconds`
- **Memory Usage**: `rca_embedding_cache_memory_bytes`
- **Evictions**: `rca_embedding_cache_evictions_total`

### 2. Compressed Ingestion Metrics

Monitors file compression and extraction:

- **File Counts**: `rca_compressed_ingestion_files_total`
- **Sizes**: `rca_compressed_ingestion_size_original_bytes`, `rca_compressed_ingestion_size_extracted_bytes`
- **Efficiency**: `rca_compressed_ingestion_compression_ratio`, `rca_compressed_ingestion_throughput_bytes_per_second`
- **Performance**: `rca_compressed_ingestion_duration_seconds`
- **Errors**: `rca_compressed_ingestion_errors_total`

### 3. Validation Metrics

Self-monitoring metrics for health checks:

- **Checks**: `rca_telemetry_validation_checks_total`
- **Duration**: `rca_telemetry_validation_duration_seconds`
- **Health**: `rca_telemetry_health_status`

## Validation Procedures

### Automated Validation

Use the built-in `TelemetryValidator` class:

```python
from core.metrics.enhanced_collectors import TelemetryValidator

# Validate specific component
embedding_results = TelemetryValidator.validate_embedding_cache()
print(f"Embedding cache status: {embedding_results['status']}")

# Validate all components
all_results = TelemetryValidator.validate_all()
print(f"Overall telemetry status: {all_results['status']}")
```

### Manual Testing

#### Embedding Cache Metrics

1. **Test Cache Hit**:
```python
from core.metrics.enhanced_collectors import EmbeddingCacheMetrics

metrics = EmbeddingCacheMetrics(model="text-embedding-ada-002", dimension=1536)

# Simulate cache hit
with metrics.lookup_timer(hit=True):
    # Perform cache lookup
    pass

metrics.record_hit()
metrics.update_size(size_bytes=1024000, entry_count=500)
```

2. **Test Cache Miss**:
```python
# Simulate cache miss
with metrics.lookup_timer(hit=False):
    # Perform cache lookup
    pass

metrics.record_miss()

# Simulate generation
with metrics.generation_timer(cached=False):
    # Generate embedding
    pass
```

3. **Verify Metrics**:
```bash
curl http://localhost:8000/metrics | grep embedding_cache
```

Expected output should show incremented counters and updated gauges.

#### Compressed Ingestion Metrics

1. **Test Successful Extraction**:
```python
from core.metrics.enhanced_collectors import CompressedIngestionMetrics

metrics = CompressedIngestionMetrics(format="zip")

with metrics.extraction_timer():
    # Simulate extraction
    import time
    time.sleep(0.1)

metrics.record_success(
    original_bytes=1024000,
    extracted_bytes=5120000,
    file_count=42,
    duration_seconds=0.1,
)
```

2. **Test Failed Extraction**:
```python
metrics.record_failure(error_type="corrupted_archive")
```

3. **Verify Metrics**:
```bash
curl http://localhost:8000/metrics | grep compressed_ingestion
```

### Health Check Endpoint

Add to FastAPI application:

```python
from fastapi import APIRouter
from core.metrics.enhanced_collectors import TelemetryValidator

router = APIRouter()

@router.get("/health/telemetry")
async def telemetry_health():
    """Health check for telemetry system."""
    results = TelemetryValidator.validate_all()
    
    status_code = 200 if results["status"] == "healthy" else 503
    return JSONResponse(content=results, status_code=status_code)
```

Test with:
```bash
curl http://localhost:8000/health/telemetry
```

## Monitoring & Alerting

### Prometheus Queries

#### Embedding Cache Hit Rate
```promql
# Cache hit rate over last 5 minutes
rate(rca_embedding_cache_hits_total[5m]) / 
(rate(rca_embedding_cache_hits_total[5m]) + rate(rca_embedding_cache_misses_total[5m]))
```

#### Average Compression Ratio
```promql
# Average compression ratio by format
avg(rca_compressed_ingestion_compression_ratio) by (format)
```

#### Extraction Throughput
```promql
# Average throughput in MB/s
avg(rca_compressed_ingestion_throughput_bytes_per_second) / 1048576
```

#### Telemetry Health
```promql
# Unhealthy components
rca_telemetry_health_status{} == 0
```

### Grafana Dashboards

Create dashboards for:

1. **Embedding Cache Performance**
   - Hit rate over time
   - Cache size growth
   - Lookup latency percentiles (p50, p95, p99)
   - Memory usage by component

2. **Compressed Ingestion**
   - Files processed per hour
   - Compression ratios by format
   - Extraction throughput
   - Error rates by type

3. **Telemetry Health**
   - Validation check status
   - Component health indicators
   - Recent issues

### Alert Rules

```yaml
groups:
  - name: telemetry_alerts
    rules:
      - alert: LowCacheHitRate
        expr: |
          rate(rca_embedding_cache_hits_total[5m]) /
          (rate(rca_embedding_cache_hits_total[5m]) + rate(rca_embedding_cache_misses_total[5m])) < 0.3
        for: 10m
        annotations:
          summary: "Embedding cache hit rate below 30%"
      
      - alert: HighExtractionFailureRate
        expr: |
          rate(rca_compressed_ingestion_errors_total[5m]) > 0.1
        for: 5m
        annotations:
          summary: "High rate of compression extraction failures"
      
      - alert: TelemetryUnhealthy
        expr: rca_telemetry_health_status == 0
        for: 2m
        annotations:
          summary: "Telemetry component unhealthy"
```

## Troubleshooting

### Common Issues

#### 1. Metrics Not Appearing

**Symptoms**: Metrics endpoint doesn't show expected metrics

**Checks**:
```python
# Verify metrics are registered
from prometheus_client import REGISTRY
print([c._name for c in REGISTRY._collector_to_names.keys()])
```

**Solutions**:
- Ensure `setup_metrics()` is called on startup
- Check that metrics module is imported
- Verify Prometheus client is installed

#### 2. Incorrect Metric Values

**Symptoms**: Metrics show unexpected values

**Checks**:
```python
# Enable debug logging
import logging
logging.getLogger("core.metrics").setLevel(logging.DEBUG)
```

**Solutions**:
- Verify label values are correct
- Check for timing issues (use context managers)
- Ensure counters are incremented, not set

#### 3. High Memory Usage

**Symptoms**: Metrics system consuming excessive memory

**Checks**:
```bash
# Check metric cardinality
curl http://localhost:8000/metrics | grep -c "^rca_"
```

**Solutions**:
- Reduce label cardinality (limit dynamic labels)
- Implement metric retention policies
- Use histograms with appropriate buckets

## Performance Considerations

### Metric Collection Overhead

- **Counters**: ~100ns per increment
- **Histograms**: ~500ns per observation
- **Gauges**: ~100ns per set

### Best Practices

1. **Use Appropriate Metric Types**:
   - Counters for cumulative values
   - Gauges for current values
   - Histograms for distributions

2. **Limit Label Cardinality**:
   - Avoid high-cardinality labels (user IDs, timestamps)
   - Use bucketing for numeric values

3. **Sample High-Frequency Events**:
   - Consider sampling for very frequent operations
   - Use structured logging as complement

4. **Batch Updates**:
   - Group related metric updates
   - Use context managers for timing

## Integration Testing

### Test Suite

```python
import pytest
from core.metrics.enhanced_collectors import (
    EmbeddingCacheMetrics,
    CompressedIngestionMetrics,
    TelemetryValidator,
)

@pytest.mark.asyncio
async def test_embedding_cache_metrics():
    """Test embedding cache metrics collection."""
    metrics = EmbeddingCacheMetrics(model="test-model")
    
    # Record operations
    metrics.record_hit()
    metrics.record_miss()
    metrics.update_size(size_bytes=1000, entry_count=10)
    
    # Validate
    results = TelemetryValidator.validate_embedding_cache()
    assert results["status"] == "healthy"

@pytest.mark.asyncio
async def test_compressed_ingestion_metrics():
    """Test compressed ingestion metrics."""
    metrics = CompressedIngestionMetrics(format="zip")
    
    # Record success
    metrics.record_success(
        original_bytes=1000,
        extracted_bytes=5000,
        file_count=10,
        duration_seconds=1.0,
    )
    
    # Validate
    results = TelemetryValidator.validate_compressed_ingestion()
    assert results["status"] == "healthy"

@pytest.mark.asyncio
async def test_telemetry_validation():
    """Test overall telemetry validation."""
    results = TelemetryValidator.validate_all()
    
    assert results["status"] in ["healthy", "unhealthy"]
    assert "components" in results
    assert "embedding_cache" in results["components"]
    assert "compressed_ingestion" in results["components"]
```

Run tests:
```bash
pytest tests/test_telemetry.py -v
```

## Maintenance

### Regular Tasks

1. **Daily**: Review Grafana dashboards for anomalies
2. **Weekly**: Check alert history and tune thresholds
3. **Monthly**: Analyze metric cardinality and optimize
4. **Quarterly**: Review and update validation procedures

### Metric Retention

Configure Prometheus retention:

```yaml
# prometheus.yml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

storage:
  tsdb:
    retention.time: 30d
    retention.size: 50GB
```

## References

- [Prometheus Best Practices](https://prometheus.io/docs/practices/)
- [Prometheus Client Python](https://github.com/prometheus/client_python)
- [Grafana Dashboards](https://grafana.com/docs/grafana/latest/dashboards/)
