"""
Base provider interface for LLM integrations.
Defines the contract that all LLM providers must implement.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, AsyncGenerator
from dataclasses import dataclass
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class LLMProvider(str, Enum):
    """Supported LLM providers."""
    OLLAMA = "ollama"
    OPENAI = "openai"
    BEDROCK = "bedrock"
    ANTHROPIC = "anthropic"
    VLLM = "vllm"
    LMSTUDIO = "lmstudio"


@dataclass
class LLMMessage:
    """Represents a message in LLM conversation."""
    role: str  # system, user, assistant
    content: str
    name: Optional[str] = None


@dataclass
class LLMResponse:
    """Represents a response from LLM."""
    content: str
    model: str
    provider: str
    usage: Optional[Dict[str, int]] = None  # token usage
    finish_reason: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class LLMStreamChunk:
    """Represents a streaming chunk from LLM."""
    content: str
    finish_reason: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class BaseLLMProvider(ABC):
    """Base class for LLM providers."""
    
    def __init__(
        self,
        model: str,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ):
        """
        Initialize LLM provider.
        
        Args:
            model: Model name/identifier
            temperature: Sampling temperature (0.0 to 1.0)
            max_tokens: Maximum tokens to generate
            **kwargs: Additional provider-specific parameters
        """
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.kwargs = kwargs
        self._initialized = False
    
    @abstractmethod
    async def initialize(self) -> None:
        """
        Initialize the provider.
        Should be called before using the provider.
        """
        pass
    
    @abstractmethod
    async def close(self) -> None:
        """
        Close the provider and cleanup resources.
        """
        pass
    
    @abstractmethod
    async def generate(
        self,
        messages: List[LLMMessage],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> LLMResponse:
        """
        Generate a response from the LLM.
        
        Args:
            messages: List of conversation messages
            temperature: Optional temperature override
            max_tokens: Optional max tokens override
            **kwargs: Additional generation parameters
            
        Returns:
            LLMResponse: Generated response
        """
        pass
    
    @abstractmethod
    async def stream_generate(
        self,
        messages: List[LLMMessage],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> AsyncGenerator[LLMStreamChunk, None]:
        """
        Generate a streaming response from the LLM.
        
        Args:
            messages: List of conversation messages
            temperature: Optional temperature override
            max_tokens: Optional max tokens override
            **kwargs: Additional generation parameters
            
        Yields:
            LLMStreamChunk: Streaming response chunks
        """
        pass
    
    @abstractmethod
    async def count_tokens(self, text: str) -> int:
        """
        Count tokens in text.
        
        Args:
            text: Text to count tokens for
            
        Returns:
            int: Token count
        """
        pass
    
    @abstractmethod
    async def health_check(self) -> bool:
        """
        Check if the provider is healthy and accessible.
        
        Returns:
            bool: True if healthy, False otherwise
        """
        pass
    
    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Get the provider name."""
        pass
    
    @property
    def is_initialized(self) -> bool:
        """Check if provider is initialized."""
        return self._initialized
    
    def _validate_messages(self, messages: List[LLMMessage]) -> None:
        """
        Validate message format.
        
        Args:
            messages: Messages to validate
            
        Raises:
            ValueError: If messages are invalid
        """
        if not messages:
            raise ValueError("Messages list cannot be empty")
        
        valid_roles = {"system", "user", "assistant"}
        for msg in messages:
            if msg.role not in valid_roles:
                raise ValueError(f"Invalid message role: {msg.role}")
            if not msg.content:
                raise ValueError("Message content cannot be empty")
    
    def _get_temperature(self, override: Optional[float] = None) -> float:
        """
        Get temperature value with optional override.
        
        Args:
            override: Optional temperature override
            
        Returns:
            float: Temperature value
        """
        temp = override if override is not None else self.temperature
        if not 0.0 <= temp <= 1.0:
            raise ValueError(f"Temperature must be between 0.0 and 1.0, got {temp}")
        return temp
    
    def _get_max_tokens(self, override: Optional[int] = None) -> Optional[int]:
        """
        Get max tokens value with optional override.
        
        Args:
            override: Optional max tokens override
            
        Returns:
            Optional[int]: Max tokens value
        """
        max_tok = override if override is not None else self.max_tokens
        if max_tok is not None and max_tok <= 0:
            raise ValueError(f"Max tokens must be positive, got {max_tok}")
        return max_tok


class LLMProviderFactory:
    """Factory for creating LLM provider instances."""
    
    _providers: Dict[str, type] = {}
    
    @classmethod
    def register_provider(cls, provider_name: str, provider_class: type) -> None:
        """
        Register a provider class.
        
        Args:
            provider_name: Name of the provider
            provider_class: Provider class
        """
        cls._providers[provider_name.lower()] = provider_class
        logger.info(f"Registered LLM provider: {provider_name}")
    
    @classmethod
    def create_provider(
        cls,
        provider_name: str,
        model: str,
        **kwargs
    ) -> BaseLLMProvider:
        """
        Create a provider instance.
        
        Args:
            provider_name: Name of the provider
            model: Model name
            **kwargs: Additional provider parameters
            
        Returns:
            BaseLLMProvider: Provider instance
            
        Raises:
            ValueError: If provider is not registered
        """
        provider_class = cls._providers.get(provider_name.lower())
        if not provider_class:
            raise ValueError(
                f"Unknown provider: {provider_name}. "
                f"Available providers: {list(cls._providers.keys())}"
            )
        
        return provider_class(model=model, **kwargs)
    
    @classmethod
    def list_providers(cls) -> List[str]:
        """
        List registered providers.
        
        Returns:
            List[str]: List of provider names
        """
        return list(cls._providers.keys())


# Export commonly used items
__all__ = [
    "BaseLLMProvider",
    "LLMProvider",
    "LLMMessage",
    "LLMResponse",
    "LLMStreamChunk",
    "LLMProviderFactory",
]
