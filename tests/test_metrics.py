"""Tests for metrics module."""

import pytest
from core.metrics import MetricsCollector, timer
import time


def test_record_http_request():
    """Test recording HTTP request metrics."""
    MetricsCollector.record_http_request(
        method="GET",
        endpoint="/api/v1/test",
        status_code=200,
        duration=0.5
    )
    # Should not raise an exception


def test_record_job_metrics():
    """Test recording job metrics."""
    MetricsCollector.record_job_created("rca_analysis")
    MetricsCollector.record_job_completed("rca_analysis", "completed", 10.5)
    # Should not raise an exception


def test_record_llm_request():
    """Test recording LLM request metrics."""
    MetricsCollector.record_llm_request(
        provider="ollama",
        model="llama2",
        status="success",
        duration=2.5,
        input_tokens=100,
        output_tokens=50
    )
    # Should not raise an exception


def test_record_embedding():
    """Test recording embedding generation metrics."""
    MetricsCollector.record_embedding_generated(
        provider="ollama",
        duration=0.5,
        count=1
    )
    # Should not raise an exception


def test_timer_context_manager():
    """Test timer context manager."""
    from core.metrics import llm_request_duration_seconds
    
    with timer(llm_request_duration_seconds, provider="test", model="test"):
        time.sleep(0.1)
    # Should not raise an exception
