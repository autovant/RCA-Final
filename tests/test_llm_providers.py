"""Tests for LLM providers."""

import pytest
from core.llm.providers.base import LLMMessage, LLMProviderFactory


def test_llm_message_creation():
    """Test LLM message creation."""
    message = LLMMessage(role="user", content="Hello")
    
    assert message.role == "user"
    assert message.content == "Hello"
    assert message.name is None


def test_llm_message_with_name():
    """Test LLM message with name."""
    message = LLMMessage(role="assistant", content="Hi there", name="bot")
    
    assert message.role == "assistant"
    assert message.content == "Hi there"
    assert message.name == "bot"


def test_provider_factory_registration():
    """Test that providers are registered."""
    # Check that providers are registered
    assert "ollama" in LLMProviderFactory._providers
    assert "openai" in LLMProviderFactory._providers
    assert "bedrock" in LLMProviderFactory._providers


def test_create_ollama_provider():
    """Test creating Ollama provider."""
    provider = LLMProviderFactory.create_provider(
        "ollama",
        model="llama2",
        temperature=0.7
    )
    
    assert provider is not None
    assert provider.model == "llama2"
    assert provider.temperature == 0.7
    assert provider.provider_name == "ollama"


def test_create_openai_provider():
    """Test creating OpenAI provider."""
    provider = LLMProviderFactory.create_provider(
        "openai",
        model="gpt-4",
        temperature=0.5,
        api_key="test_key"
    )
    
    assert provider is not None
    assert provider.model == "gpt-4"
    assert provider.temperature == 0.5
    assert provider.provider_name == "openai"


def test_create_bedrock_provider():
    """Test creating Bedrock provider."""
    provider = LLMProviderFactory.create_provider(
        "bedrock",
        model="anthropic.claude-v2",
        temperature=0.8
    )
    
    assert provider is not None
    assert provider.model == "anthropic.claude-v2"
    assert provider.temperature == 0.8
    assert provider.provider_name == "bedrock"


def test_invalid_provider():
    """Test creating invalid provider."""
    with pytest.raises(ValueError):
        LLMProviderFactory.create_provider("invalid_provider", model="test")
