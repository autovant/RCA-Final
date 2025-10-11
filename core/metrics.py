"""
Prometheus metrics module for RCA Engine.
Provides performance monitoring and metrics collection.
"""

from prometheus_client import (
    Counter,
    Histogram,
    Gauge,
    Info,
    generate_latest,
    CONTENT_TYPE_LATEST,
    CollectorRegistry,
)
from fastapi import Response
from typing import Optional
from core.config import settings
import time
import logging

logger = logging.getLogger(__name__)
_metrics_configured = False


def setup_metrics() -> None:
    """
    Idempotent initialiser used by the API and worker entrypoints.

    The heavy lifting (registry / metric creation) happens at import time; this
    hook simply records the fact that metrics were requested and emits a single
    log entry so operators know the component was initialised.
    """
    global _metrics_configured

    if _metrics_configured:
        logger.debug("Metrics already configured; skipping re-initialisation")
        return

    if not settings.METRICS_ENABLED:
        logger.info("Prometheus metrics disabled via configuration")
        _metrics_configured = True
        return

    logger.info(
        "Prometheus metrics enabled for %s v%s",
        settings.APP_NAME,
        settings.APP_VERSION,
    )
    _metrics_configured = True

# Create custom registry
registry = CollectorRegistry()

# Application info
app_info = Info(
    'rca_engine_app',
    'RCA Engine application information',
    registry=registry
)
app_info.info({
    'version': settings.APP_VERSION,
    'environment': settings.ENVIRONMENT,
})

# HTTP metrics
http_requests_total = Counter(
    'rca_engine_http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status'],
    registry=registry
)

http_request_duration_seconds = Histogram(
    'rca_engine_http_request_duration_seconds',
    'HTTP request duration in seconds',
    ['method', 'endpoint'],
    registry=registry
)

http_requests_in_progress = Gauge(
    'rca_engine_http_requests_in_progress',
    'HTTP requests currently in progress',
    ['method', 'endpoint'],
    registry=registry
)

# Job metrics
jobs_total = Counter(
    'rca_engine_jobs_total',
    'Total jobs created',
    ['job_type', 'status'],
    registry=registry
)

jobs_duration_seconds = Histogram(
    'rca_engine_jobs_duration_seconds',
    'Job processing duration in seconds',
    ['job_type', 'status'],
    registry=registry
)

jobs_in_progress = Gauge(
    'rca_engine_jobs_in_progress',
    'Jobs currently in progress',
    ['job_type'],
    registry=registry
)

jobs_queue_size = Gauge(
    'rca_engine_jobs_queue_size',
    'Number of jobs in queue',
    registry=registry
)

# Database metrics
db_connections_total = Gauge(
    'rca_engine_db_connections_total',
    'Total database connections',
    registry=registry
)

db_connections_active = Gauge(
    'rca_engine_db_connections_active',
    'Active database connections',
    registry=registry
)

db_query_duration_seconds = Histogram(
    'rca_engine_db_query_duration_seconds',
    'Database query duration in seconds',
    ['operation'],
    registry=registry
)

# LLM metrics
llm_requests_total = Counter(
    'rca_engine_llm_requests_total',
    'Total LLM requests',
    ['provider', 'model', 'status'],
    registry=registry
)

llm_request_duration_seconds = Histogram(
    'rca_engine_llm_request_duration_seconds',
    'LLM request duration in seconds',
    ['provider', 'model'],
    registry=registry
)

llm_tokens_total = Counter(
    'rca_engine_llm_tokens_total',
    'Total LLM tokens used',
    ['provider', 'model', 'type'],
    registry=registry
)

# File processing metrics
files_processed_total = Counter(
    'rca_engine_files_processed_total',
    'Total files processed',
    ['file_type', 'status'],
    registry=registry
)

files_size_bytes = Histogram(
    'rca_engine_files_size_bytes',
    'File size in bytes',
    ['file_type'],
    registry=registry
)

files_processing_duration_seconds = Histogram(
    'rca_engine_files_processing_duration_seconds',
    'File processing duration in seconds',
    ['file_type'],
    registry=registry
)

# Embedding metrics
embeddings_generated_total = Counter(
    'rca_engine_embeddings_generated_total',
    'Total embeddings generated',
    ['provider'],
    registry=registry
)

embeddings_generation_duration_seconds = Histogram(
    'rca_engine_embeddings_generation_duration_seconds',
    'Embedding generation duration in seconds',
    ['provider'],
    registry=registry
)

# Error metrics
errors_total = Counter(
    'rca_engine_errors_total',
    'Total errors',
    ['error_type', 'component'],
    registry=registry
)

# System metrics
system_cpu_usage = Gauge(
    'rca_engine_system_cpu_usage',
    'System CPU usage percentage',
    registry=registry
)

system_memory_usage_bytes = Gauge(
    'rca_engine_system_memory_usage_bytes',
    'System memory usage in bytes',
    registry=registry
)


class MetricsCollector:
    """Collector for application metrics."""
    
    @staticmethod
    def record_http_request(
        method: str,
        endpoint: str,
        status_code: int,
        duration: float
    ) -> None:
        """
        Record HTTP request metrics.
        
        Args:
            method: HTTP method
            endpoint: Request endpoint
            status_code: Response status code
            duration: Request duration in seconds
        """
        http_requests_total.labels(
            method=method,
            endpoint=endpoint,
            status=str(status_code)
        ).inc()
        
        http_request_duration_seconds.labels(
            method=method,
            endpoint=endpoint
        ).observe(duration)
    
    @staticmethod
    def record_job_created(job_type: str) -> None:
        """
        Record job creation.
        
        Args:
            job_type: Type of job
        """
        jobs_total.labels(
            job_type=job_type,
            status='created'
        ).inc()
    
    @staticmethod
    def record_job_completed(
        job_type: str,
        status: str,
        duration: float
    ) -> None:
        """
        Record job completion.
        
        Args:
            job_type: Type of job
            status: Job status (completed/failed)
            duration: Job duration in seconds
        """
        jobs_total.labels(
            job_type=job_type,
            status=status
        ).inc()
        
        jobs_duration_seconds.labels(
            job_type=job_type,
            status=status
        ).observe(duration)
    
    @staticmethod
    def record_llm_request(
        provider: str,
        model: str,
        status: str,
        duration: float,
        input_tokens: Optional[int] = None,
        output_tokens: Optional[int] = None
    ) -> None:
        """
        Record LLM request metrics.
        
        Args:
            provider: LLM provider
            model: Model name
            status: Request status
            duration: Request duration in seconds
            input_tokens: Optional input token count
            output_tokens: Optional output token count
        """
        llm_requests_total.labels(
            provider=provider,
            model=model,
            status=status
        ).inc()
        
        llm_request_duration_seconds.labels(
            provider=provider,
            model=model
        ).observe(duration)
        
        if input_tokens is not None:
            llm_tokens_total.labels(
                provider=provider,
                model=model,
                type='input'
            ).inc(input_tokens)
        
        if output_tokens is not None:
            llm_tokens_total.labels(
                provider=provider,
                model=model,
                type='output'
            ).inc(output_tokens)
    
    @staticmethod
    def record_file_processed(
        file_type: str,
        status: str,
        size_bytes: int,
        duration: float
    ) -> None:
        """
        Record file processing metrics.
        
        Args:
            file_type: Type of file
            status: Processing status
            size_bytes: File size in bytes
            duration: Processing duration in seconds
        """
        files_processed_total.labels(
            file_type=file_type,
            status=status
        ).inc()
        
        files_size_bytes.labels(
            file_type=file_type
        ).observe(size_bytes)
        
        files_processing_duration_seconds.labels(
            file_type=file_type
        ).observe(duration)
    
    @staticmethod
    def record_embedding_generated(
        provider: str,
        duration: float,
        count: int = 1
    ) -> None:
        """
        Record embedding generation metrics.
        
        Args:
            provider: Embedding provider
            duration: Generation duration in seconds
            count: Number of embeddings generated
        """
        embeddings_generated_total.labels(
            provider=provider
        ).inc(count)
        
        embeddings_generation_duration_seconds.labels(
            provider=provider
        ).observe(duration)
    
    @staticmethod
    def record_error(error_type: str, component: str) -> None:
        """
        Record error metrics.
        
        Args:
            error_type: Type of error
            component: Component where error occurred
        """
        errors_total.labels(
            error_type=error_type,
            component=component
        ).inc()
    
    @staticmethod
    def update_job_queue_size(size: int) -> None:
        """
        Update job queue size.
        
        Args:
            size: Current queue size
        """
        jobs_queue_size.set(size)
    
    @staticmethod
    def update_jobs_in_progress(job_type: str, count: int) -> None:
        """
        Update jobs in progress count.
        
        Args:
            job_type: Type of job
            count: Number of jobs in progress
        """
        jobs_in_progress.labels(job_type=job_type).set(count)
    
    @staticmethod
    def update_db_connections(total: int, active: int) -> None:
        """
        Update database connection metrics.
        
        Args:
            total: Total connections
            active: Active connections
        """
        db_connections_total.set(total)
        db_connections_active.set(active)


def get_metrics() -> Response:
    """
    Get Prometheus metrics.
    
    Returns:
        Response: Prometheus metrics response
    """
    metrics_data = generate_latest(registry)
    return Response(
        content=metrics_data,
        media_type=CONTENT_TYPE_LATEST
    )


# Context managers for timing operations
class timer:
    """Context manager for timing operations."""
    
    def __init__(self, metric: Histogram, **labels):
        """
        Initialize timer.
        
        Args:
            metric: Histogram metric to record to
            **labels: Metric labels
        """
        self.metric = metric
        self.labels = labels
        self.start_time = None
    
    def __enter__(self):
        """Start timer."""
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Stop timer and record duration."""
        duration = time.time() - self.start_time
        self.metric.labels(**self.labels).observe(duration)


# Export commonly used items
__all__ = [
    'setup_metrics',
    'MetricsCollector',
    'get_metrics',
    'timer',
    'registry',
    # Metrics
    'http_requests_total',
    'http_request_duration_seconds',
    'jobs_total',
    'jobs_duration_seconds',
    'llm_requests_total',
    'llm_request_duration_seconds',
    'files_processed_total',
    'embeddings_generated_total',
    'errors_total',
]
