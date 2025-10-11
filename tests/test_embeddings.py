"""Tests for embedding service."""

import pytest
import numpy as np

pytest.importorskip("openai")

from core.llm.embeddings import EmbeddingService


def test_cosine_similarity():
    """Test cosine similarity calculation."""
    vec1 = [1.0, 0.0, 0.0]
    vec2 = [1.0, 0.0, 0.0]
    
    similarity = EmbeddingService.cosine_similarity(vec1, vec2)
    assert abs(similarity - 1.0) < 0.001  # Should be 1.0 for identical vectors


def test_cosine_similarity_orthogonal():
    """Test cosine similarity for orthogonal vectors."""
    vec1 = [1.0, 0.0, 0.0]
    vec2 = [0.0, 1.0, 0.0]
    
    similarity = EmbeddingService.cosine_similarity(vec1, vec2)
    assert abs(similarity) < 0.001  # Should be 0.0 for orthogonal vectors


def test_cosine_similarity_opposite():
    """Test cosine similarity for opposite vectors."""
    vec1 = [1.0, 0.0, 0.0]
    vec2 = [-1.0, 0.0, 0.0]
    
    similarity = EmbeddingService.cosine_similarity(vec1, vec2)
    assert abs(similarity - (-1.0)) < 0.001  # Should be -1.0 for opposite vectors


def test_embedding_service_creation():
    """Test embedding service creation with provider name."""
    service = EmbeddingService(provider_name="ollama", model="nomic-embed-text")
    
    assert service is not None
    assert service.provider is not None
    assert service.provider.provider_name == "ollama"


def test_embedding_service_openai():
    """Test embedding service with OpenAI provider."""
    service = EmbeddingService(
        provider_name="openai",
        model="text-embedding-3-small",
        api_key="test_key"
    )
    
    assert service is not None
    assert service.provider.provider_name == "openai"
    assert service.provider.model == "text-embedding-3-small"


def test_embedding_dimension():
    """Test getting embedding dimension."""
    service = EmbeddingService(
        provider_name="openai",
        model="text-embedding-3-small"
    )
    
    dimension = service.get_dimension()
    assert dimension == 1536  # Default dimension for text-embedding-3-small
