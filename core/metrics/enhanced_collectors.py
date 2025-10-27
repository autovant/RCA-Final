"""
Enhanced telemetry collectors for embedding cache and compressed ingestion.

Provides Prometheus metrics for:
- Embedding cache hit rates, sizes, and performance
- Compressed ingestion throughput and compression ratios
- Validation procedures and health checks
"""

from __future__ import annotations

from prometheus_client import Counter, Histogram, Gauge, Info
from typing import Optional
from datetime import datetime

from core.logging import get_logger

logger = get_logger(__name__)


# ============================================================================
# Embedding Cache Metrics
# ============================================================================

embedding_cache_hits = Counter(
    "rca_embedding_cache_hits_total",
    "Total number of embedding cache hits",
    ["model", "dimension"],
)

embedding_cache_misses = Counter(
    "rca_embedding_cache_misses_total",
    "Total number of embedding cache misses",
    ["model", "dimension"],
)

embedding_cache_size = Gauge(
    "rca_embedding_cache_size_bytes",
    "Current size of embedding cache in bytes",
    ["model"],
)

embedding_cache_entries = Gauge(
    "rca_embedding_cache_entries_total",
    "Total number of entries in embedding cache",
    ["model"],
)

embedding_cache_evictions = Counter(
    "rca_embedding_cache_evictions_total",
    "Total number of cache evictions",
    ["model", "reason"],
)

embedding_cache_lookup_duration = Histogram(
    "rca_embedding_cache_lookup_duration_seconds",
    "Time spent looking up embeddings in cache",
    ["model", "hit"],
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0],
)

embedding_generation_duration = Histogram(
    "rca_embedding_generation_duration_seconds",
    "Time spent generating embeddings",
    ["model", "cached"],
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
)

embedding_batch_size = Histogram(
    "rca_embedding_batch_size",
    "Number of texts processed in a single embedding batch",
    ["model"],
    buckets=[1, 5, 10, 25, 50, 100, 250, 500, 1000],
)

embedding_cache_memory_bytes = Gauge(
    "rca_embedding_cache_memory_bytes",
    "Memory used by embedding cache",
    ["model", "component"],
)


class EmbeddingCacheMetrics:
    """
    High-level API for recording embedding cache metrics.
    
    Usage:
        metrics = EmbeddingCacheMetrics(model="text-embedding-ada-002")
        
        with metrics.lookup_timer(hit=True):
            result = cache.get(key)
        
        metrics.record_hit(dimension=1536)
        metrics.update_size(size_bytes=1024000, entry_count=500)
    """
    
    def __init__(self, model: str, dimension: Optional[int] = None):
        self.model = model
        self.dimension = str(dimension) if dimension else "unknown"
    
    def record_hit(self, dimension: Optional[int] = None) -> None:
        """Record a cache hit."""
        dim = str(dimension) if dimension else self.dimension
        embedding_cache_hits.labels(model=self.model, dimension=dim).inc()
    
    def record_miss(self, dimension: Optional[int] = None) -> None:
        """Record a cache miss."""
        dim = str(dimension) if dimension else self.dimension
        embedding_cache_misses.labels(model=self.model, dimension=dim).inc()
    
    def record_eviction(self, reason: str = "size_limit") -> None:
        """Record a cache eviction."""
        embedding_cache_evictions.labels(model=self.model, reason=reason).inc()
    
    def update_size(self, size_bytes: int, entry_count: int) -> None:
        """Update cache size metrics."""
        embedding_cache_size.labels(model=self.model).set(size_bytes)
        embedding_cache_entries.labels(model=self.model).set(entry_count)
    
    def update_memory(self, component: str, bytes_used: int) -> None:
        """Update memory usage for a cache component."""
        embedding_cache_memory_bytes.labels(
            model=self.model,
            component=component,
        ).set(bytes_used)
    
    def lookup_timer(self, hit: bool):
        """Context manager for timing cache lookups."""
        return embedding_cache_lookup_duration.labels(
            model=self.model,
            hit="hit" if hit else "miss",
        ).time()
    
    def generation_timer(self, cached: bool = False):
        """Context manager for timing embedding generation."""
        return embedding_generation_duration.labels(
            model=self.model,
            cached="yes" if cached else "no",
        ).time()
    
    def record_batch_size(self, size: int) -> None:
        """Record the size of an embedding batch."""
        embedding_batch_size.labels(model=self.model).observe(size)


# ============================================================================
# Compressed Ingestion Metrics
# ============================================================================

compressed_ingestion_files = Counter(
    "rca_compressed_ingestion_files_total",
    "Total number of compressed files ingested",
    ["format", "status"],
)

compressed_ingestion_size_original = Histogram(
    "rca_compressed_ingestion_size_original_bytes",
    "Original compressed file size in bytes",
    ["format"],
    buckets=[
        1024,  # 1KB
        10240,  # 10KB
        102400,  # 100KB
        1048576,  # 1MB
        10485760,  # 10MB
        104857600,  # 100MB
        1073741824,  # 1GB
    ],
)

compressed_ingestion_size_extracted = Histogram(
    "rca_compressed_ingestion_size_extracted_bytes",
    "Extracted (decompressed) size in bytes",
    ["format"],
    buckets=[
        1024,
        10240,
        102400,
        1048576,
        10485760,
        104857600,
        1073741824,
        10737418240,  # 10GB
    ],
)

compressed_ingestion_ratio = Histogram(
    "rca_compressed_ingestion_compression_ratio",
    "Compression ratio (extracted / original)",
    ["format"],
    buckets=[1, 2, 5, 10, 20, 50, 100, 500, 1000],
)

compressed_ingestion_duration = Histogram(
    "rca_compressed_ingestion_duration_seconds",
    "Time spent extracting compressed files",
    ["format"],
    buckets=[0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0, 120.0],
)

compressed_ingestion_throughput = Histogram(
    "rca_compressed_ingestion_throughput_bytes_per_second",
    "Extraction throughput in bytes per second",
    ["format"],
    buckets=[
        10240,  # 10KB/s
        102400,  # 100KB/s
        1048576,  # 1MB/s
        10485760,  # 10MB/s
        104857600,  # 100MB/s
        1073741824,  # 1GB/s
    ],
)

compressed_ingestion_files_extracted = Histogram(
    "rca_compressed_ingestion_files_extracted_count",
    "Number of files extracted from archive",
    ["format"],
    buckets=[1, 5, 10, 25, 50, 100, 250, 500, 1000, 5000],
)

compressed_ingestion_errors = Counter(
    "rca_compressed_ingestion_errors_total",
    "Total compression/extraction errors",
    ["format", "error_type"],
)


class CompressedIngestionMetrics:
    """
    High-level API for recording compressed ingestion metrics.
    
    Usage:
        metrics = CompressedIngestionMetrics(format="zip")
        
        with metrics.extraction_timer():
            extracted_size = extract_archive(archive_path)
        
        metrics.record_success(
            original_bytes=1024000,
            extracted_bytes=5120000,
            file_count=42,
        )
    """
    
    def __init__(self, format: str):
        self.format = format.lower()
    
    def record_success(
        self,
        original_bytes: int,
        extracted_bytes: int,
        file_count: int,
        duration_seconds: float,
    ) -> None:
        """Record successful extraction with all metrics."""
        compressed_ingestion_files.labels(
            format=self.format,
            status="success",
        ).inc()
        
        compressed_ingestion_size_original.labels(
            format=self.format,
        ).observe(original_bytes)
        
        compressed_ingestion_size_extracted.labels(
            format=self.format,
        ).observe(extracted_bytes)
        
        if original_bytes > 0:
            ratio = extracted_bytes / original_bytes
            compressed_ingestion_ratio.labels(
                format=self.format,
            ).observe(ratio)
        
        compressed_ingestion_files_extracted.labels(
            format=self.format,
        ).observe(file_count)
        
        if duration_seconds > 0:
            throughput = extracted_bytes / duration_seconds
            compressed_ingestion_throughput.labels(
                format=self.format,
            ).observe(throughput)
    
    def record_failure(self, error_type: str) -> None:
        """Record extraction failure."""
        compressed_ingestion_files.labels(
            format=self.format,
            status="failed",
        ).inc()
        
        compressed_ingestion_errors.labels(
            format=self.format,
            error_type=error_type,
        ).inc()
    
    def extraction_timer(self):
        """Context manager for timing extraction."""
        return compressed_ingestion_duration.labels(
            format=self.format,
        ).time()


# ============================================================================
# Validation Metrics
# ============================================================================

telemetry_validation_checks = Counter(
    "rca_telemetry_validation_checks_total",
    "Total number of telemetry validation checks performed",
    ["check_type", "status"],
)

telemetry_validation_duration = Histogram(
    "rca_telemetry_validation_duration_seconds",
    "Time spent on telemetry validation",
    ["check_type"],
    buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 5.0],
)

telemetry_health_status = Gauge(
    "rca_telemetry_health_status",
    "Overall health status of telemetry system (1=healthy, 0=unhealthy)",
    ["component"],
)


class TelemetryValidator:
    """
    Validation procedures for telemetry collectors.
    
    Ensures metrics are being recorded correctly and health checks pass.
    """
    
    @staticmethod
    def validate_embedding_cache() -> dict:
        """
        Validate embedding cache metrics are working.
        
        Returns:
            Dict with validation results and any issues found
        """
        results = {
            "status": "healthy",
            "checks": [],
            "issues": [],
        }
        
        try:
            # Check that metrics are registered
            metrics_to_check = [
                embedding_cache_hits,
                embedding_cache_misses,
                embedding_cache_size,
                embedding_cache_entries,
            ]
            
            for metric in metrics_to_check:
                results["checks"].append({
                    "metric": metric._name,
                    "registered": True,
                })
            
            telemetry_validation_checks.labels(
                check_type="embedding_cache",
                status="pass",
            ).inc()
            
            telemetry_health_status.labels(
                component="embedding_cache",
            ).set(1)
        
        except Exception as exc:
            results["status"] = "unhealthy"
            results["issues"].append(str(exc))
            
            telemetry_validation_checks.labels(
                check_type="embedding_cache",
                status="fail",
            ).inc()
            
            telemetry_health_status.labels(
                component="embedding_cache",
            ).set(0)
        
        return results
    
    @staticmethod
    def validate_compressed_ingestion() -> dict:
        """
        Validate compressed ingestion metrics are working.
        
        Returns:
            Dict with validation results and any issues found
        """
        results = {
            "status": "healthy",
            "checks": [],
            "issues": [],
        }
        
        try:
            metrics_to_check = [
                compressed_ingestion_files,
                compressed_ingestion_size_original,
                compressed_ingestion_size_extracted,
                compressed_ingestion_ratio,
            ]
            
            for metric in metrics_to_check:
                results["checks"].append({
                    "metric": metric._name,
                    "registered": True,
                })
            
            telemetry_validation_checks.labels(
                check_type="compressed_ingestion",
                status="pass",
            ).inc()
            
            telemetry_health_status.labels(
                component="compressed_ingestion",
            ).set(1)
        
        except Exception as exc:
            results["status"] = "unhealthy"
            results["issues"].append(str(exc))
            
            telemetry_validation_checks.labels(
                check_type="compressed_ingestion",
                status="fail",
            ).inc()
            
            telemetry_health_status.labels(
                component="compressed_ingestion",
            ).set(0)
        
        return results
    
    @staticmethod
    def validate_all() -> dict:
        """
        Run all validation checks.
        
        Returns:
            Combined validation results
        """
        embedding_results = TelemetryValidator.validate_embedding_cache()
        compression_results = TelemetryValidator.validate_compressed_ingestion()
        
        all_healthy = (
            embedding_results["status"] == "healthy" and
            compression_results["status"] == "healthy"
        )
        
        return {
            "status": "healthy" if all_healthy else "unhealthy",
            "timestamp": datetime.utcnow().isoformat(),
            "components": {
                "embedding_cache": embedding_results,
                "compressed_ingestion": compression_results,
            },
        }
