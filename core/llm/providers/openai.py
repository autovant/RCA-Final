"""
OpenAI LLM provider implementation.
Provides integration with OpenAI's GPT models.
"""

from typing import List, Optional, AsyncGenerator, Dict, Any
import openai
from openai import AsyncOpenAI
from core.llm.providers.base import (
    BaseLLMProvider,
    LLMMessage,
    LLMResponse,
    LLMStreamChunk,
    LLMProviderFactory,
)
from core.config import settings
from core.metrics import MetricsCollector, timer, llm_request_duration_seconds
import logging
import time

logger = logging.getLogger(__name__)


class OpenAIProvider(BaseLLMProvider):
    """OpenAI LLM provider implementation."""
    
    def __init__(
        self,
        model: str,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        api_key: Optional[str] = None,
        organization: Optional[str] = None,
        **kwargs
    ):
        """
        Initialize OpenAI provider.
        
        Args:
            model: Model name (e.g., 'gpt-4', 'gpt-3.5-turbo')
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            api_key: Optional API key override
            organization: Optional organization ID
            **kwargs: Additional parameters
        """
        super().__init__(model, temperature, max_tokens, **kwargs)
        self.api_key = api_key or settings.llm.OPENAI_API_KEY
        self.organization = organization or settings.llm.OPENAI_ORG_ID
        self._client: Optional[AsyncOpenAI] = None
    
    async def initialize(self) -> None:
        """Initialize the OpenAI provider."""
        if self._initialized:
            return
        
        try:
            self._client = AsyncOpenAI(
                api_key=self.api_key,
                organization=self.organization
            )
            
            # Test connection
            await self.health_check()
            
            self._initialized = True
            logger.info(f"OpenAI provider initialized: model={self.model}")
            
        except Exception as e:
            logger.error(f"Failed to initialize OpenAI provider: {e}")
            raise
    
    async def close(self) -> None:
        """Close the provider and cleanup resources."""
        if self._client:
            await self._client.close()
            self._client = None
        self._initialized = False
        logger.info("OpenAI provider closed")
    
    def _format_messages(self, messages: List[LLMMessage]) -> List[Dict[str, str]]:
        """
        Format messages for OpenAI API.
        
        Args:
            messages: List of messages
            
        Returns:
            List[Dict[str, str]]: Formatted messages
        """
        return [
            {"role": msg.role, "content": msg.content}
            for msg in messages
        ]
    
    async def generate(
        self,
        messages: List[LLMMessage],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> LLMResponse:
        """
        Generate a response from OpenAI.
        
        Args:
            messages: List of conversation messages
            temperature: Optional temperature override
            max_tokens: Optional max tokens override
            **kwargs: Additional generation parameters
            
        Returns:
            LLMResponse: Generated response
        """
        if not self._initialized:
            await self.initialize()
        
        self._validate_messages(messages)
        
        start_time = time.time()
        
        try:
            # Prepare request
            formatted_messages = self._format_messages(messages)
            
            request_params = {
                "model": self.model,
                "messages": formatted_messages,
                "temperature": self._get_temperature(temperature),
            }
            
            if max_tokens := self._get_max_tokens(max_tokens):
                request_params["max_tokens"] = max_tokens
            
            # Add any additional kwargs
            request_params.update(kwargs)
            
            # Make request
            with timer(llm_request_duration_seconds, provider="openai", model=self.model):
                response = await self._client.chat.completions.create(**request_params)
            
            # Extract response
            choice = response.choices[0]
            content = choice.message.content
            
            # Extract usage
            usage = {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens,
            }
            
            duration = time.time() - start_time
            
            # Record metrics
            MetricsCollector.record_llm_request(
                provider="openai",
                model=self.model,
                status="success",
                duration=duration,
                input_tokens=usage["prompt_tokens"],
                output_tokens=usage["completion_tokens"]
            )
            
            logger.info(
                f"OpenAI generation completed: model={self.model}, "
                f"tokens={usage['total_tokens']}, duration={duration:.2f}s"
            )
            
            return LLMResponse(
                content=content,
                model=self.model,
                provider="openai",
                usage=usage,
                finish_reason=choice.finish_reason,
                metadata={"response_id": response.id}
            )
            
        except Exception as e:
            duration = time.time() - start_time
            MetricsCollector.record_llm_request(
                provider="openai",
                model=self.model,
                status="error",
                duration=duration
            )
            logger.error(f"OpenAI generation failed: {e}")
            raise
    
    async def stream_generate(
        self,
        messages: List[LLMMessage],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> AsyncGenerator[LLMStreamChunk, None]:
        """
        Generate a streaming response from OpenAI.
        
        Args:
            messages: List of conversation messages
            temperature: Optional temperature override
            max_tokens: Optional max tokens override
            **kwargs: Additional generation parameters
            
        Yields:
            LLMStreamChunk: Streaming response chunks
        """
        if not self._initialized:
            await self.initialize()
        
        self._validate_messages(messages)
        
        start_time = time.time()
        
        try:
            # Prepare request
            formatted_messages = self._format_messages(messages)
            
            request_params = {
                "model": self.model,
                "messages": formatted_messages,
                "temperature": self._get_temperature(temperature),
                "stream": True,
            }
            
            if max_tokens := self._get_max_tokens(max_tokens):
                request_params["max_tokens"] = max_tokens
            
            request_params.update(kwargs)
            
            # Make streaming request
            stream = await self._client.chat.completions.create(**request_params)
            
            async for chunk in stream:
                if chunk.choices:
                    choice = chunk.choices[0]
                    
                    if choice.delta.content:
                        yield LLMStreamChunk(
                            content=choice.delta.content,
                            finish_reason=choice.finish_reason,
                            metadata={"chunk_id": chunk.id}
                        )
            
            duration = time.time() - start_time
            
            MetricsCollector.record_llm_request(
                provider="openai",
                model=self.model,
                status="success",
                duration=duration
            )
            
            logger.info(f"OpenAI streaming completed: model={self.model}, duration={duration:.2f}s")
            
        except Exception as e:
            duration = time.time() - start_time
            MetricsCollector.record_llm_request(
                provider="openai",
                model=self.model,
                status="error",
                duration=duration
            )
            logger.error(f"OpenAI streaming failed: {e}")
            raise
    
    async def count_tokens(self, text: str) -> int:
        """
        Count tokens in text using tiktoken.
        
        Args:
            text: Text to count tokens for
            
        Returns:
            int: Token count
        """
        try:
            import tiktoken
            
            # Get encoding for model
            if "gpt-4" in self.model:
                encoding = tiktoken.encoding_for_model("gpt-4")
            elif "gpt-3.5" in self.model:
                encoding = tiktoken.encoding_for_model("gpt-3.5-turbo")
            else:
                encoding = tiktoken.get_encoding("cl100k_base")
            
            return len(encoding.encode(text))
            
        except Exception as e:
            logger.warning(f"Failed to count tokens with tiktoken: {e}. Using approximation.")
            # Fallback to approximation
            return len(text) // 4
    
    async def health_check(self) -> bool:
        """
        Check if OpenAI API is accessible.
        
        Returns:
            bool: True if healthy, False otherwise
        """
        try:
            if not self._client:
                return False
            
            # Try to list models
            await self._client.models.list()
            return True
            
        except Exception as e:
            logger.error(f"OpenAI health check failed: {e}")
            return False
    
    @property
    def provider_name(self) -> str:
        """Get the provider name."""
        return "openai"


# Register provider with factory
LLMProviderFactory.register_provider("openai", OpenAIProvider)


__all__ = ["OpenAIProvider"]
