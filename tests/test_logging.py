"""Tests for logging module."""

import pytest
import logging
from core.logging import setup_logging, get_logger


def test_setup_logging():
    """Test logging setup."""
    setup_logging(log_level="INFO", log_format="json")
    logger = logging.getLogger("test")
    assert logger is not None


def test_get_logger():
    """Test getting a logger with context."""
    logger = get_logger("test_module", context={"request_id": "123"})
    assert logger is not None
    assert logger.name == "test_module"


def test_logger_with_context():
    """Test logger with context."""
    context = {"user_id": "user123", "request_id": "req456"}
    logger = get_logger("test_context", context=context)
    
    # This should not raise an exception
    logger.info("Test message with context")
