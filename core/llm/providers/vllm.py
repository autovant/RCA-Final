"""
vLLM Provider
Provides integration with vLLM for high-throughput LLM inference.
"""

import logging
import time
from typing import List, Optional, AsyncGenerator, Dict, Any

import aiohttp

from .base import BaseLLMProvider, LLMMessage, LLMResponse, LLMStreamChunk

logger = logging.getLogger(__name__)


class VLLMProvider(BaseLLMProvider):
    """
    vLLM provider for high-performance local LLM inference.
    
    vLLM provides OpenAI-compatible API endpoints.
    """
    
    def __init__(
        self,
        model: str,
        base_url: str = "http://localhost:8000",
        api_key: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ):
        """
        Initialize vLLM provider.
        
        Args:
            model: Model name/path
            base_url: Base URL for vLLM server
            api_key: Optional API key
            temperature: Sampling temperature (0.0 to 1.0)
            max_tokens: Maximum tokens to generate
            **kwargs: Additional parameters
        """
        super().__init__(model, temperature, max_tokens, **kwargs)
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.session: Optional[aiohttp.ClientSession] = None
        
    async def initialize(self) -> None:
        """Initialize the HTTP session."""
        if self._initialized:
            return
            
        try:
            timeout = aiohttp.ClientTimeout(total=300)  # 5 minute timeout
            self.session = aiohttp.ClientSession(timeout=timeout)
            self._initialized = True
            logger.info(f"vLLM provider initialized with model: {self.model}")
        except Exception as e:
            logger.error(f"Failed to initialize vLLM provider: {e}")
            raise
    
    async def close(self) -> None:
        """Close the HTTP session."""
        if self.session:
            await self.session.close()
            self.session = None
        self._initialized = False
        logger.info("vLLM provider closed")
    
    def _build_headers(self) -> Dict[str, str]:
        """Build request headers."""
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers
    
    def _convert_messages(self, messages: List[LLMMessage]) -> List[Dict[str, str]]:
        """Convert LLMMessage format to OpenAI-compatible format."""
        return [
            {
                "role": msg.role,
                "content": msg.content
            }
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
        Generate a response using vLLM.
        
        Args:
            messages: Conversation messages
            temperature: Optional temperature override
            max_tokens: Optional max tokens override
            **kwargs: Additional parameters (top_p, frequency_penalty, etc.)
            
        Returns:
            LLMResponse with generated content
        """
        if not self._initialized:
            await self.initialize()
        
        self._validate_messages(messages)
        temp = self._get_temperature(temperature)
        tokens = max_tokens or self.max_tokens
        
        converted_messages = self._convert_messages(messages)
        
        start_time = time.time()
        
        try:
            # Build request payload (OpenAI-compatible)
            payload = {
                "model": self.model,
                "messages": converted_messages,
                "temperature": temp,
                "stream": False
            }
            
            if tokens:
                payload["max_tokens"] = tokens
            
            # Add optional parameters
            if "top_p" in kwargs:
                payload["top_p"] = kwargs["top_p"]
            if "frequency_penalty" in kwargs:
                payload["frequency_penalty"] = kwargs["frequency_penalty"]
            if "presence_penalty" in kwargs:
                payload["presence_penalty"] = kwargs["presence_penalty"]
            if "stop" in kwargs:
                payload["stop"] = kwargs["stop"]
            
            url = f"{self.base_url}/v1/chat/completions"
            headers = self._build_headers()
            
            async with self.session.post(url, json=payload, headers=headers) as response:
                response.raise_for_status()
                data = await response.json()
            
            latency = time.time() - start_time
            
            # Parse response
            choice = data["choices"][0]
            content = choice["message"]["content"]
            finish_reason = choice.get("finish_reason")
            
            # Parse usage info
            usage = None
            if "usage" in data:
                usage = {
                    "prompt_tokens": data["usage"].get("prompt_tokens", 0),
                    "completion_tokens": data["usage"].get("completion_tokens", 0),
                    "total_tokens": data["usage"].get("total_tokens", 0)
                }
            
            return LLMResponse(
                content=content,
                model=self.model,
                provider=self.provider_name,
                usage=usage,
                finish_reason=finish_reason,
                metadata={
                    "latency_seconds": latency,
                    "model_version": data.get("model", self.model)
                }
            )
            
        except aiohttp.ClientError as e:
            logger.error(f"vLLM HTTP error: {e}")
            raise
        except Exception as e:
            logger.error(f"Error generating response from vLLM: {e}")
            raise
    
    async def stream_generate(
        self,
        messages: List[LLMMessage],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> AsyncGenerator[LLMStreamChunk, None]:
        """
        Generate a streaming response using vLLM.
        
        Args:
            messages: Conversation messages
            temperature: Optional temperature override
            max_tokens: Optional max tokens override
            **kwargs: Additional parameters
            
        Yields:
            LLMStreamChunk: Streaming response chunks
        """
        if not self._initialized:
            await self.initialize()
        
        self._validate_messages(messages)
        temp = self._get_temperature(temperature)
        tokens = max_tokens or self.max_tokens
        
        converted_messages = self._convert_messages(messages)
        
        try:
            # Build request payload
            payload = {
                "model": self.model,
                "messages": converted_messages,
                "temperature": temp,
                "stream": True
            }
            
            if tokens:
                payload["max_tokens"] = tokens
            
            # Add optional parameters
            if "top_p" in kwargs:
                payload["top_p"] = kwargs["top_p"]
            
            url = f"{self.base_url}/v1/chat/completions"
            headers = self._build_headers()
            
            async with self.session.post(url, json=payload, headers=headers) as response:
                response.raise_for_status()
                
                async for line in response.content:
                    line = line.decode('utf-8').strip()
                    
                    if not line or line == "data: [DONE]":
                        continue
                    
                    if line.startswith("data: "):
                        line = line[6:]  # Remove "data: " prefix
                        
                        try:
                            import json
                            data = json.loads(line)
                            
                            if "choices" in data and len(data["choices"]) > 0:
                                choice = data["choices"][0]
                                
                                if "delta" in choice:
                                    delta = choice["delta"]
                                    content = delta.get("content", "")
                                    
                                    if content:
                                        yield LLMStreamChunk(
                                            content=content,
                                            finish_reason=None
                                        )
                                
                                finish_reason = choice.get("finish_reason")
                                if finish_reason:
                                    yield LLMStreamChunk(
                                        content="",
                                        finish_reason=finish_reason
                                    )
                        except json.JSONDecodeError:
                            continue
                            
        except aiohttp.ClientError as e:
            logger.error(f"vLLM streaming HTTP error: {e}")
            raise
        except Exception as e:
            logger.error(f"Error streaming from vLLM: {e}")
            raise
    
    async def count_tokens(self, text: str) -> int:
        """
        Estimate token count for text.
        
        Uses rough approximation similar to GPT models.
        
        Args:
            text: Text to count tokens for
            
        Returns:
            Estimated token count
        """
        # Rough approximation: ~4 characters per token
        return len(text) // 4
    
    async def health_check(self) -> bool:
        """
        Check if vLLM server is accessible.
        
        Returns:
            True if healthy, False otherwise
        """
        try:
            if not self._initialized:
                await self.initialize()
            
            # Check health endpoint
            url = f"{self.base_url}/health"
            headers = self._build_headers()
            
            async with self.session.get(url, headers=headers) as response:
                return response.status == 200
        except Exception as e:
            logger.error(f"vLLM health check failed: {e}")
    @property
    def provider_name(self) -> str:
        """Get the provider name."""
        return "vllm"


# Register provider
from .base import LLMProviderFactory
LLMProviderFactory.register_provider("vllm", VLLMProvider)

__all__ = ["VLLMProvider"]
