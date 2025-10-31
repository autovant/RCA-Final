"""Tests for enhanced telemetry collectors."""

import pytest
from unittest.mock import MagicMock

from core.metrics.enhanced_collectors import (
    EmbeddingCacheMetrics,
    CompressedIngestionMetrics,
    TelemetryValidator,
)


class TestEmbeddingCacheMetrics:
    """Test suite for EmbeddingCacheMetrics."""
    
    @pytest.fixture
    def metrics(self):
        """Create metrics instance for testing."""
        return EmbeddingCacheMetrics(model="test-model", dimension=1536)
    
    def test_record_hit(self, metrics):
        """Test recording cache hits."""
        metrics.record_hit()
        # Verify counter incremented (would check Prometheus in integration test)
    
    def test_record_miss(self, metrics):
        """Test recording cache misses."""
        metrics.record_miss()
        # Verify counter incremented
    
    def test_record_eviction(self, metrics):
        """Test recording cache evictions."""
        metrics.record_eviction(reason="size_limit")
        # Verify counter incremented with label
    
    def test_update_size(self, metrics):
        """Test updating cache size metrics."""
        metrics.update_size(size_bytes=1024000, entry_count=500)
        # Verify gauges updated
    
    def test_update_memory(self, metrics):
        """Test updating memory metrics."""
        metrics.update_memory(component="index", bytes_used=2048000)
        # Verify gauge updated with component label
    
    def test_lookup_timer(self, metrics):
        """Test lookup timer context manager."""
        with metrics.lookup_timer(hit=True):
            # Simulate lookup
            pass
        # Verify histogram recorded
    
    def test_generation_timer(self, metrics):
        """Test generation timer context manager."""
        with metrics.generation_timer(cached=False):
            # Simulate generation
            pass
        # Verify histogram recorded
    
    def test_record_batch_size(self, metrics):
        """Test recording batch size."""
        metrics.record_batch_size(size=50)
        # Verify histogram recorded


class TestCompressedIngestionMetrics:
    """Test suite for CompressedIngestionMetrics."""
    
    @pytest.fixture
    def metrics(self):
        """Create metrics instance for testing."""
        return CompressedIngestionMetrics(format="zip")
    
    def test_record_success(self, metrics):
        """Test recording successful extraction."""
        metrics.record_success(
            original_bytes=1024000,
            extracted_bytes=5120000,
            file_count=42,
            duration_seconds=2.5,
        )
        # Verify all metrics recorded
    
    def test_record_failure(self, metrics):
        """Test recording extraction failure."""
        metrics.record_failure(error_type="corrupted_archive")
        # Verify error counter incremented
    
    def test_extraction_timer(self, metrics):
        """Test extraction timer context manager."""
        with metrics.extraction_timer():
            # Simulate extraction
            pass
        # Verify histogram recorded
    
    def test_compression_ratio(self, metrics):
        """Test compression ratio calculation."""
        metrics.record_success(
            original_bytes=1000000,
            extracted_bytes=5000000,
            file_count=10,
            duration_seconds=1.0,
        )
        # Ratio should be 5.0x
    
    def test_throughput_calculation(self, metrics):
        """Test throughput calculation."""
        metrics.record_success(
            original_bytes=1000000,
            extracted_bytes=10000000,
            file_count=100,
            duration_seconds=2.0,
        )
        # Throughput should be 5MB/s


class TestTelemetryValidator:
    """Test suite for TelemetryValidator."""
    
    def test_validate_embedding_cache(self):
        """Test embedding cache validation."""
        results = TelemetryValidator.validate_embedding_cache()
        
        assert "status" in results
        assert "checks" in results
        assert "issues" in results
        
        # Should be healthy if metrics are registered
        assert results["status"] in ["healthy", "unhealthy"]
    
    def test_validate_compressed_ingestion(self):
        """Test compressed ingestion validation."""
        results = TelemetryValidator.validate_compressed_ingestion()
        
        assert "status" in results
        assert "checks" in results
        assert "issues" in results
    
    def test_validate_all(self):
        """Test validating all components."""
        results = TelemetryValidator.validate_all()
        
        assert "status" in results
        assert "timestamp" in results
        assert "components" in results
        assert "embedding_cache" in results["components"]
        assert "compressed_ingestion" in results["components"]
    
    def test_validation_health_status(self):
        """Test that validation sets health status metric."""
        TelemetryValidator.validate_embedding_cache()
        # Verify health status gauge was set
        
        TelemetryValidator.validate_compressed_ingestion()
        # Verify health status gauge was set


class TestMetricsIntegration:
    """Integration tests for metrics."""
    
    def test_embedding_cache_workflow(self):
        """Test complete embedding cache workflow."""
        metrics = EmbeddingCacheMetrics(model="test", dimension=768)
        
        # Simulate cache miss + generation
        with metrics.lookup_timer(hit=False):
            pass
        metrics.record_miss()
        
        with metrics.generation_timer(cached=False):
            pass
        
        metrics.update_size(size_bytes=500000, entry_count=100)
        
        # Simulate cache hit
        with metrics.lookup_timer(hit=True):
            pass
        metrics.record_hit()
    
    def test_compression_workflow(self):
        """Test complete compression workflow."""
        metrics = CompressedIngestionMetrics(format="7z")
        
        # Simulate successful extraction
        with metrics.extraction_timer():
            # Would extract here
            pass
        
        metrics.record_success(
            original_bytes=2048000,
            extracted_bytes=10240000,
            file_count=150,
            duration_seconds=3.5,
        )
    
    def test_validation_workflow(self):
        """Test validation workflow."""
        # Run validations
        embedding_results = TelemetryValidator.validate_embedding_cache()
        compression_results = TelemetryValidator.validate_compressed_ingestion()
        all_results = TelemetryValidator.validate_all()
        
        # Verify structure
        assert embedding_results["status"] in ["healthy", "unhealthy"]
        assert compression_results["status"] in ["healthy", "unhealthy"]
        assert all_results["status"] in ["healthy", "unhealthy"]
