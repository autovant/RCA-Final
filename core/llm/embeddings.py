"""
Embedding service for RCA Engine.
Provides text embedding generation and management.
"""

from typing import List, Optional, Dict, Any
from abc import ABC, abstractmethod
import hashlib
import logging
import re
import time

import numpy as np
import httpx

from core.config import settings
from core.metrics import (
    MetricsCollector,
    embeddings_generation_duration_seconds,
    timer,
)

try:  # Optional dependency; only required when using OpenAI embeddings
    from openai import AsyncOpenAI  # type: ignore
except Exception:  # pragma: no cover - dependency optional
    AsyncOpenAI = None  # type: ignore[assignment]

logger = logging.getLogger(__name__)


class BaseEmbeddingProvider(ABC):
    """Base class for embedding providers."""
    
    @abstractmethod
    async def initialize(self) -> None:
        """Initialize the provider."""
        pass
    
    @abstractmethod
    async def close(self) -> None:
        """Close the provider and cleanup resources."""
        pass
    
    @abstractmethod
    async def embed_text(self, text: str) -> List[float]:
        """
        Generate embedding for a single text.
        
        Args:
            text: Text to embed
            
        Returns:
            List[float]: Embedding vector
        """
        pass
    
    @abstractmethod
    async def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for multiple texts.
        
        Args:
            texts: List of texts to embed
            
        Returns:
            List[List[float]]: List of embedding vectors
        """
        pass
    
    @abstractmethod
    def get_dimension(self) -> int:
        """
        Get the dimension of embeddings.
        
        Returns:
            int: Embedding dimension
        """
        pass
    
    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Get the provider name."""
        pass


class OllamaEmbeddingProvider(BaseEmbeddingProvider):
    """Ollama embedding provider."""
    
    def __init__(
        self,
        model: str = "nomic-embed-text",
        base_url: Optional[str] = None,
        timeout: float = 60.0
    ):
        """
        Initialize Ollama embedding provider.
        
        Args:
            model: Embedding model name
            base_url: Optional Ollama API base URL
            timeout: Request timeout in seconds
        """
        self.model = model
        self.base_url = base_url or settings.llm.OLLAMA_BASE_URL
        self.timeout = timeout
        self._client: Optional[httpx.AsyncClient] = None
        self._dimension: Optional[int] = None
    
    async def initialize(self) -> None:
        """Initialize the provider."""
        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=httpx.Timeout(self.timeout)
        )
        logger.info(f"Ollama embedding provider initialized: model={self.model}")
    
    async def close(self) -> None:
        """Close the provider."""
        if self._client:
            await self._client.aclose()
            self._client = None
        logger.info("Ollama embedding provider closed")
    
    async def embed_text(self, text: str) -> List[float]:
        """Generate embedding for a single text."""
        if not self._client:
            await self.initialize()
        
        start_time = time.time()
        
        try:
            with timer(embeddings_generation_duration_seconds, provider="ollama"):
                response = await self._client.post(
                    "/api/embeddings",
                    json={"model": self.model, "prompt": text}
                )
                response.raise_for_status()
            
            result = response.json()
            embedding = result.get("embedding", [])
            
            if not self._dimension:
                self._dimension = len(embedding)
            
            duration = time.time() - start_time
            MetricsCollector.record_embedding_generated("ollama", duration)
            
            return embedding
            
        except Exception as e:
            logger.error(f"Ollama embedding generation failed: {e}")
            raise
    
    async def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts."""
        embeddings = []
        for text in texts:
            embedding = await self.embed_text(text)
            embeddings.append(embedding)
        return embeddings
    
    def get_dimension(self) -> int:
        """Get the dimension of embeddings."""
        return self._dimension or 768  # Default dimension
    
    @property
    def provider_name(self) -> str:
        """Get the provider name."""
        return "ollama"


class OpenAIEmbeddingProvider(BaseEmbeddingProvider):
    """OpenAI embedding provider."""
    
    def __init__(
        self,
        model: str = "text-embedding-3-small",
        api_key: Optional[str] = None,
        organization: Optional[str] = None
    ):
        """
        Initialize OpenAI embedding provider.
        
        Args:
            model: Embedding model name
            api_key: Optional API key override
            organization: Optional organization ID
        """
        if AsyncOpenAI is None:
            raise RuntimeError(
                "OpenAIEmbeddingProvider requires the 'openai' package. "
                "Install it with 'pip install openai' to enable OpenAI embeddings."
            )
        self.model = model
        self.api_key = api_key or settings.llm.OPENAI_API_KEY
        self.organization = organization or settings.llm.OPENAI_ORG_ID
        self._client: Optional[AsyncOpenAI] = None
        self._dimension_map = {
            "text-embedding-3-small": 1536,
            "text-embedding-3-large": 3072,
            "text-embedding-ada-002": 1536,
        }
    
    async def initialize(self) -> None:
        """Initialize the provider."""
        self._client = AsyncOpenAI(
            api_key=self.api_key,
            organization=self.organization
        )
        logger.info(f"OpenAI embedding provider initialized: model={self.model}")
    
    async def close(self) -> None:
        """Close the provider."""
        if self._client:
            await self._client.close()
            self._client = None
        logger.info("OpenAI embedding provider closed")
    
    async def embed_text(self, text: str) -> List[float]:
        """Generate embedding for a single text."""
        if not self._client:
            await self.initialize()
        
        start_time = time.time()
        
        try:
            with timer(embeddings_generation_duration_seconds, provider="openai"):
                response = await self._client.embeddings.create(
                    model=self.model,
                    input=text
                )
            
            embedding = response.data[0].embedding
            
            duration = time.time() - start_time
            MetricsCollector.record_embedding_generated("openai", duration)
            
            return embedding
            
        except Exception as e:
            logger.error(f"OpenAI embedding generation failed: {e}")
            raise
    
    async def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts."""
        if not self._client:
            await self.initialize()
        
        start_time = time.time()
        
        try:
            with timer(embeddings_generation_duration_seconds, provider="openai"):
                response = await self._client.embeddings.create(
                    model=self.model,
                    input=texts
                )
            
            embeddings = [data.embedding for data in response.data]
            
            duration = time.time() - start_time
            MetricsCollector.record_embedding_generated("openai", duration, len(texts))
            
            return embeddings
            
        except Exception as e:
            logger.error(f"OpenAI batch embedding generation failed: {e}")
            raise
    
    def get_dimension(self) -> int:
        """Get the dimension of embeddings."""
        return self._dimension_map.get(self.model, 1536)
    
    @property
    def provider_name(self) -> str:
        """Get the provider name."""
        return "openai"


class HashingEmbeddingProvider(BaseEmbeddingProvider):
    """Deterministic local embedding provider based on token hashing."""

    def __init__(self, dimension: Optional[int] = None):
        self.dimension = int(dimension or settings.VECTOR_DIMENSION)
        self._initialised = False

    async def initialize(self) -> None:
        self._initialised = True
        logger.info(
            "Hashing embedding provider initialized: dimension=%s", self.dimension
        )

    async def close(self) -> None:
        self._initialised = False
        logger.info("Hashing embedding provider closed")

    def _vectorise(self, text: str) -> List[float]:
        vector = np.zeros(self.dimension, dtype=np.float32)
        tokens = re.findall(r"\w+", text.lower())
        if not tokens:
            return vector.tolist()

        for token in tokens:
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            index = int.from_bytes(digest[:8], "big") % self.dimension
            sign = 1.0 if digest[8] & 1 else -1.0
            vector[index] += sign

        norm = np.linalg.norm(vector)
        if norm > 0:
            vector /= norm

        return vector.tolist()

    async def embed_text(self, text: str) -> List[float]:
        if not self._initialised:
            await self.initialize()

        start_time = time.time()
        embedding = self._vectorise(text)
        duration = time.time() - start_time
        MetricsCollector.record_embedding_generated("hashing", duration)
        return embedding

    async def embed_texts(self, texts: List[str]) -> List[List[float]]:
        if not self._initialised:
            await self.initialize()

        start_time = time.time()
        embeddings = [self._vectorise(text) for text in texts]
        duration = time.time() - start_time
        MetricsCollector.record_embedding_generated(
            "hashing", duration, len(texts)
        )
        return embeddings

    def get_dimension(self) -> int:
        return self.dimension

    @property
    def provider_name(self) -> str:
        return "hashing"


class EmbeddingService:
    """Service for managing embeddings."""
    
    def __init__(
        self,
        provider: Optional[BaseEmbeddingProvider] = None,
        provider_name: Optional[str] = None,
        **kwargs
    ):
        """
        Initialize embedding service.
        
        Args:
            provider: Optional provider instance
            provider_name: Optional provider name to create
            **kwargs: Provider-specific parameters
        """
        if provider:
            self.provider = provider
        elif provider_name:
            self.provider = self._create_provider(provider_name, **kwargs)
        else:
            # Default to configured provider
            default_provider = settings.llm.EMBEDDING_PROVIDER or "openai"
            self.provider = self._create_provider(default_provider, **kwargs)
    
    def _create_provider(
        self,
        provider_name: str,
        **kwargs
    ) -> BaseEmbeddingProvider:
        """
        Create a provider instance.
        
        Args:
            provider_name: Provider name
            **kwargs: Provider parameters
            
        Returns:
            BaseEmbeddingProvider: Provider instance
        """
        normalised = provider_name.lower()
        if normalised == "ollama":
            return OllamaEmbeddingProvider(**kwargs)
        if normalised == "openai":
            api_key = kwargs.get("api_key") or settings.llm.OPENAI_API_KEY
            if not api_key or str(api_key).startswith("your-"):
                logger.warning(
                    "OpenAI API key not configured; falling back to hashing embeddings"
                )
                return HashingEmbeddingProvider()
            return OpenAIEmbeddingProvider(**kwargs)
        if normalised in {"hashing", "hash", "local"}:
            return HashingEmbeddingProvider(**kwargs)

        raise ValueError(f"Unknown embedding provider: {provider_name}")
    
    async def initialize(self) -> None:
        """Initialize the service."""
        await self.provider.initialize()
        logger.info(f"Embedding service initialized with {self.provider.provider_name}")
    
    async def close(self) -> None:
        """Close the service."""
        await self.provider.close()
        logger.info("Embedding service closed")
    
    async def embed_text(self, text: str) -> List[float]:
        """
        Generate embedding for a single text.
        
        Args:
            text: Text to embed
            
        Returns:
            List[float]: Embedding vector
        """
        return await self.provider.embed_text(text)
    
    async def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for multiple texts.
        
        Args:
            texts: List of texts to embed
            
        Returns:
            List[List[float]]: List of embedding vectors
        """
        return await self.provider.embed_texts(texts)
    
    async def embed_documents(
        self,
        documents: List[str],
        batch_size: int = 100
    ) -> List[List[float]]:
        """
        Generate embeddings for documents in batches.
        
        Args:
            documents: List of documents to embed
            batch_size: Batch size for processing
            
        Returns:
            List[List[float]]: List of embedding vectors
        """
        all_embeddings = []
        
        for i in range(0, len(documents), batch_size):
            batch = documents[i:i + batch_size]
            embeddings = await self.embed_texts(batch)
            all_embeddings.extend(embeddings)
            
            logger.info(f"Embedded batch {i // batch_size + 1}/{(len(documents) + batch_size - 1) // batch_size}")
        
        return all_embeddings
    
    def get_dimension(self) -> int:
        """
        Get the dimension of embeddings.
        
        Returns:
            int: Embedding dimension
        """
        return self.provider.get_dimension()
    
    @staticmethod
    def cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
        """
        Calculate cosine similarity between two vectors.
        
        Args:
            vec1: First vector
            vec2: Second vector
            
        Returns:
            float: Cosine similarity (-1 to 1)
        """
        v1 = np.array(vec1)
        v2 = np.array(vec2)
        
        dot_product = np.dot(v1, v2)
        norm1 = np.linalg.norm(v1)
        norm2 = np.linalg.norm(v2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return float(dot_product / (norm1 * norm2))


# Export commonly used items
__all__ = [
    "BaseEmbeddingProvider",
    "OllamaEmbeddingProvider",
    "OpenAIEmbeddingProvider",
    "EmbeddingService",
]
