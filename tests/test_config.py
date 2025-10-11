"""Tests for core configuration module."""

import pytest
from core.config import settings


def test_settings_loaded():
    """Test that settings are loaded correctly."""
    assert settings is not None
    assert settings.APP_NAME == "RCA Engine"
    assert settings.APP_VERSION == "1.0.0"


def test_security_settings():
    """Test security settings."""
    assert settings.security.JWT_SECRET_KEY is not None
    assert len(settings.security.JWT_SECRET_KEY) >= 32
    assert settings.security.JWT_ALGORITHM == "HS256"


def test_database_settings():
    """Test database settings."""
    assert settings.database.POSTGRES_HOST is not None
    assert settings.database.POSTGRES_PORT == 5432
    assert settings.database.DATABASE_URL is not None


def test_llm_settings():
    """Test LLM settings."""
    assert settings.llm.DEFAULT_PROVIDER in ["ollama", "openai", "bedrock"]
    assert settings.llm.OLLAMA_BASE_URL is not None
    assert settings.llm.EMBEDDING_PROVIDER in ["ollama", "openai"]
