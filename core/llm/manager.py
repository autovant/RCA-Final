"""
LLM Provider Manager with Fallback Support
Handles provider selection, fallback, and retry logic.
"""

import logging
from typing import List, Optional, Dict, Any, AsyncGenerator

from core.config import settings
from core.llm.providers import (
    BaseLLMProvider,
    LLMProviderFactory,
    LLMMessage,
    LLMResponse,
    LLMStreamChunk,
)

logger = logging.getLogger(__name__)


class ProviderConfig:
    """Configuration for a specific LLM provider."""
    
    def __init__(
        self,
        provider: str,
        model: str,
        **kwargs
    ):
        self.provider = provider
        self.model = model
        self.kwargs = kwargs


class LLMProviderManager:
    """
    Manages LLM provider selection and fallback logic.
    
    Supports configuring primary and fallback providers with automatic
    failover when a provider is unavailable or fails.
    """
    
    def __init__(
        self,
        primary_provider: Optional[str] = None,
        primary_model: Optional[str] = None,
        fallback_providers: Optional[List[ProviderConfig]] = None,
        max_retries: int = 2
    ):
        """
        Initialize provider manager.
        
        Args:
            primary_provider: Primary provider name
            primary_model: Primary model name
            fallback_providers: List of fallback provider configurations
            max_retries: Maximum retries per provider
        """
        self.primary_provider = primary_provider or settings.llm.DEFAULT_PROVIDER
        self.primary_model = primary_model or self._get_default_model(self.primary_provider)
        self.fallback_providers = fallback_providers or self._get_default_fallbacks()
        self.max_retries = max_retries
        self._active_provider: Optional[BaseLLMProvider] = None
        self._provider_health: Dict[str, bool] = {}
    
    def _get_default_model(self, provider: str) -> str:
        """Get default model for a provider."""
        provider_lower = provider.lower()
        
        model_map = {
            "ollama": settings.llm.OLLAMA_MODEL,
            "openai": settings.llm.OPENAI_MODEL,
            "bedrock": settings.llm.BEDROCK_MODEL,
            "anthropic": settings.llm.ANTHROPIC_MODEL,
            "vllm": settings.llm.VLLM_MODEL,
            "lmstudio": settings.llm.LMSTUDIO_MODEL,
        }
        
        return model_map.get(provider_lower, "default-model")
    
    def _get_default_fallbacks(self) -> List[ProviderConfig]:
        """
        Get default fallback providers.
        
        Returns a list of fallback providers in order of preference:
        1. OpenAI (if API key available)
        2. Anthropic (if API key available)
        3. Ollama (local)
        """
        fallbacks = []
        
        # Add OpenAI if API key is configured
        if settings.llm.OPENAI_API_KEY:
            fallbacks.append(ProviderConfig(
                provider="openai",
                model=settings.llm.OPENAI_MODEL,
                api_key=settings.llm.OPENAI_API_KEY,
                max_tokens=settings.llm.OPENAI_MAX_TOKENS
            ))
        
        # Add Anthropic if API key is configured
        if settings.llm.ANTHROPIC_API_KEY:
            fallbacks.append(ProviderConfig(
                provider="anthropic",
                model=settings.llm.ANTHROPIC_MODEL,
                api_key=settings.llm.ANTHROPIC_API_KEY,
                max_tokens=settings.llm.ANTHROPIC_MAX_TOKENS
            ))
        
        # Always add Ollama as final fallback (local)
        fallbacks.append(ProviderConfig(
            provider="ollama",
            model=settings.llm.OLLAMA_MODEL,
            base_url=settings.llm.OLLAMA_BASE_URL,
            max_tokens=settings.llm.OLLAMA_MAX_TOKENS,
            timeout=settings.llm.OLLAMA_TIMEOUT
        ))
        
        return fallbacks
    
    async def _create_provider(self, config: ProviderConfig) -> BaseLLMProvider:
        """Create a provider instance from configuration."""
        provider = LLMProviderFactory.create_provider(
            provider_name=config.provider,
            model=config.model,
            **config.kwargs
        )
        
        await provider.initialize()
        return provider
    
    async def _check_provider_health(self, provider: BaseLLMProvider) -> bool:
        """Check if a provider is healthy."""
        try:
            is_healthy = await provider.health_check()
            self._provider_health[provider.provider_name] = is_healthy
            return is_healthy
        except Exception as e:
            logger.warning(f"Health check failed for {provider.provider_name}: {e}")
            self._provider_health[provider.provider_name] = False
            return False
    
    async def get_provider(self, force_refresh: bool = False) -> BaseLLMProvider:
        """
        Get an active provider, creating one if needed.
        
        Args:
            force_refresh: Force refresh of the provider
            
        Returns:
            Active provider instance
            
        Raises:
            RuntimeError: If no provider is available
        """
        if self._active_provider and not force_refresh:
            # Check if current provider is still healthy
            if await self._check_provider_health(self._active_provider):
                return self._active_provider
            else:
                await self._active_provider.close()
                self._active_provider = None
        
        # Try primary provider
        try:
            primary_config = ProviderConfig(
                provider=self.primary_provider,
                model=self.primary_model
            )
            
            provider = await self._create_provider(primary_config)
            
            if await self._check_provider_health(provider):
                logger.info(f"Using primary provider: {self.primary_provider}")
                self._active_provider = provider
                return provider
            else:
                await provider.close()
                logger.warning(f"Primary provider {self.primary_provider} is unhealthy")
        except Exception as e:
            logger.error(f"Failed to create primary provider {self.primary_provider}: {e}")
        
        # Try fallback providers
        for fallback in self.fallback_providers:
            # Skip if this is the same as primary
            if fallback.provider == self.primary_provider:
                continue
            
            try:
                provider = await self._create_provider(fallback)
                
                if await self._check_provider_health(provider):
                    logger.info(f"Using fallback provider: {fallback.provider}")
                    self._active_provider = provider
                    return provider
                else:
                    await provider.close()
                    logger.warning(f"Fallback provider {fallback.provider} is unhealthy")
            except Exception as e:
                logger.error(f"Failed to create fallback provider {fallback.provider}: {e}")
        
        raise RuntimeError("No healthy LLM provider available")
    
    async def generate(
        self,
        messages: List[LLMMessage],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> LLMResponse:
        """
        Generate a response with automatic fallback.
        
        Args:
            messages: Conversation messages
            temperature: Optional temperature override
            max_tokens: Optional max tokens override
            **kwargs: Additional generation parameters
            
        Returns:
            LLMResponse with generated content
            
        Raises:
            RuntimeError: If all providers fail
        """
        last_error = None
        
        for attempt in range(self.max_retries):
            try:
                provider = await self.get_provider(force_refresh=(attempt > 0))
                
                response = await provider.generate(
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    **kwargs
                )
                
                return response
                
            except Exception as e:
                logger.warning(
                    f"Generation failed (attempt {attempt + 1}/{self.max_retries}): {e}"
                )
                last_error = e
                
                # Mark current provider as unhealthy
                if self._active_provider:
                    self._provider_health[self._active_provider.provider_name] = False
                    await self._active_provider.close()
                    self._active_provider = None
        
        raise RuntimeError(f"All providers failed after {self.max_retries} retries: {last_error}")
    
    async def stream_generate(
        self,
        messages: List[LLMMessage],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> AsyncGenerator[LLMStreamChunk, None]:
        """
        Generate a streaming response with fallback.
        
        Note: Fallback is only attempted if provider selection fails.
        Once streaming starts, errors will propagate.
        
        Args:
            messages: Conversation messages
            temperature: Optional temperature override
            max_tokens: Optional max tokens override
            **kwargs: Additional generation parameters
            
        Yields:
            LLMStreamChunk: Streaming response chunks
        """
        provider = await self.get_provider()
        
        async for chunk in provider.stream_generate(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs
        ):
            yield chunk
    
    async def close(self) -> None:
        """Close the active provider."""
        if self._active_provider:
            await self._active_provider.close()
            self._active_provider = None
        
        logger.info("LLM provider manager closed")
    
    def get_provider_health_status(self) -> Dict[str, bool]:
        """Get health status of all known providers."""
        return self._provider_health.copy()


__all__ = [
    "LLMProviderManager",
    "ProviderConfig",
]
