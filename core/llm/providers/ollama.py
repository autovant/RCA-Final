"""
Ollama LLM provider implementation.
Provides integration with local Ollama models.
"""

from typing import List, Optional, AsyncGenerator, Dict, Any
import httpx
import json
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


class OllamaProvider(BaseLLMProvider):
    """Ollama LLM provider implementation."""
    
    def __init__(
        self,
        model: str,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        base_url: Optional[str] = None,
        timeout: float = 300.0,
        **kwargs
    ):
        """
        Initialize Ollama provider.
        
        Args:
            model: Model name (e.g., 'llama2', 'mistral')
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            base_url: Optional Ollama API base URL
            timeout: Request timeout in seconds
            **kwargs: Additional parameters
        """
        super().__init__(model, temperature, max_tokens, **kwargs)
        self.base_url = base_url or settings.llm.OLLAMA_BASE_URL
        self.timeout = timeout
        self._client: Optional[httpx.AsyncClient] = None
    
    async def initialize(self) -> None:
        """Initialize the Ollama provider."""
        if self._initialized:
            return
        
        try:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=httpx.Timeout(self.timeout)
            )
            
            # Test connection
            await self.health_check()
            
            self._initialized = True
            logger.info(f"Ollama provider initialized: model={self.model}, base_url={self.base_url}")
            
        except Exception as e:
            logger.error(f"Failed to initialize Ollama provider: {e}")
            raise
    
    async def close(self) -> None:
        """Close the provider and cleanup resources."""
        if self._client:
            await self._client.aclose()
            self._client = None
        self._initialized = False
        logger.info("Ollama provider closed")
    
    def _format_messages(self, messages: List[LLMMessage]) -> str:
        """
        Format messages for Ollama API.
        
        Args:
            messages: List of messages
            
        Returns:
            str: Formatted prompt
        """
        formatted_parts = []
        
        for msg in messages:
            if msg.role == "system":
                formatted_parts.append(f"System: {msg.content}")
            elif msg.role == "user":
                formatted_parts.append(f"User: {msg.content}")
            elif msg.role == "assistant":
                formatted_parts.append(f"Assistant: {msg.content}")
        
        formatted_parts.append("Assistant:")
        return "\n\n".join(formatted_parts)
    
    async def generate(
        self,
        messages: List[LLMMessage],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> LLMResponse:
        """
        Generate a response from Ollama.
        
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
            prompt = self._format_messages(messages)
            
            request_data = {
                "model": self.model,
                "prompt": prompt,
                "temperature": self._get_temperature(temperature),
                "stream": False,
            }
            
            if max_tokens := self._get_max_tokens(max_tokens):
                request_data["options"] = {"num_predict": max_tokens}
            
            # Add any additional kwargs
            request_data.update(kwargs)
            
            # Make request
            with timer(llm_request_duration_seconds, provider="ollama", model=self.model):
                response = await self._client.post("/api/generate", json=request_data)
                response.raise_for_status()
            
            result = response.json()
            
            # Extract response
            content = result.get("response", "")
            
            # Calculate token usage (approximate)
            usage = {
                "prompt_tokens": result.get("prompt_eval_count", 0),
                "completion_tokens": result.get("eval_count", 0),
                "total_tokens": result.get("prompt_eval_count", 0) + result.get("eval_count", 0),
            }
            
            duration = time.time() - start_time
            
            # Record metrics
            MetricsCollector.record_llm_request(
                provider="ollama",
                model=self.model,
                status="success",
                duration=duration,
                input_tokens=usage["prompt_tokens"],
                output_tokens=usage["completion_tokens"]
            )
            
            logger.info(
                f"Ollama generation completed: model={self.model}, "
                f"tokens={usage['total_tokens']}, duration={duration:.2f}s"
            )
            
            return LLMResponse(
                content=content,
                model=self.model,
                provider="ollama",
                usage=usage,
                finish_reason=result.get("done_reason"),
                metadata={"raw_response": result}
            )
            
        except Exception as e:
            duration = time.time() - start_time
            MetricsCollector.record_llm_request(
                provider="ollama",
                model=self.model,
                status="error",
                duration=duration
            )
            logger.error(f"Ollama generation failed: {e}")
            raise
    
    async def stream_generate(
        self,
        messages: List[LLMMessage],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> AsyncGenerator[LLMStreamChunk, None]:
        """
        Generate a streaming response from Ollama.
        
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
            prompt = self._format_messages(messages)
            
            request_data = {
                "model": self.model,
                "prompt": prompt,
                "temperature": self._get_temperature(temperature),
                "stream": True,
            }
            
            if max_tokens := self._get_max_tokens(max_tokens):
                request_data["options"] = {"num_predict": max_tokens}
            
            request_data.update(kwargs)
            
            # Make streaming request
            async with self._client.stream("POST", "/api/generate", json=request_data) as response:
                response.raise_for_status()
                
                async for line in response.aiter_lines():
                    if not line:
                        continue
                    
                    try:
                        chunk_data = json.loads(line)
                        content = chunk_data.get("response", "")
                        
                        if content:
                            yield LLMStreamChunk(
                                content=content,
                                finish_reason=chunk_data.get("done_reason") if chunk_data.get("done") else None,
                                metadata=chunk_data
                            )
                        
                        if chunk_data.get("done"):
                            break
                            
                    except json.JSONDecodeError:
                        logger.warning(f"Failed to decode streaming chunk: {line}")
                        continue
            
            duration = time.time() - start_time
            
            MetricsCollector.record_llm_request(
                provider="ollama",
                model=self.model,
                status="success",
                duration=duration
            )
            
            logger.info(f"Ollama streaming completed: model={self.model}, duration={duration:.2f}s")
            
        except Exception as e:
            duration = time.time() - start_time
            MetricsCollector.record_llm_request(
                provider="ollama",
                model=self.model,
                status="error",
                duration=duration
            )
            logger.error(f"Ollama streaming failed: {e}")
            raise
    
    async def count_tokens(self, text: str) -> int:
        """
        Count tokens in text (approximate).
        
        Args:
            text: Text to count tokens for
            
        Returns:
            int: Approximate token count
        """
        # Simple approximation: ~4 characters per token
        return len(text) // 4
    
    async def health_check(self) -> bool:
        """
        Check if Ollama is healthy and accessible.
        
        Returns:
            bool: True if healthy, False otherwise
        """
        try:
            if not self._client:
                return False
            
            response = await self._client.get("/api/tags")
            response.raise_for_status()
            
            # Check if our model is available
            models = response.json().get("models", [])
            model_names = [m.get("name") for m in models]
            
            if self.model not in model_names:
                logger.warning(f"Model {self.model} not found in Ollama. Available: {model_names}")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Ollama health check failed: {e}")
            return False
    
    @property
    def provider_name(self) -> str:
        """Get the provider name."""
        return "ollama"


# Register provider with factory
LLMProviderFactory.register_provider("ollama", OllamaProvider)


__all__ = ["OllamaProvider"]
