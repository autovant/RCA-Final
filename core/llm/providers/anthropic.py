"""
Anthropic Claude API Provider
Provides direct integration with Anthropic's Claude API.
"""

import logging
import time
from typing import List, Optional, AsyncGenerator, Dict, Any

import anthropic
from anthropic import AsyncAnthropic
from anthropic.types import Message, MessageStreamEvent

from .base import BaseLLMProvider, LLMMessage, LLMResponse, LLMStreamChunk

logger = logging.getLogger(__name__)


class AnthropicProvider(BaseLLMProvider):
    """
    Anthropic Claude provider for direct API access.
    
    Supports Claude models: claude-3-opus, claude-3-sonnet, claude-3-haiku, etc.
    """
    
    def __init__(
        self,
        model: str = "claude-3-sonnet-20240229",
        api_key: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        **kwargs
    ):
        """
        Initialize Anthropic provider.
        
        Args:
            model: Model name (e.g., 'claude-3-opus-20240229')
            api_key: Anthropic API key
            temperature: Sampling temperature (0.0 to 1.0)
            max_tokens: Maximum tokens to generate
            **kwargs: Additional parameters
        """
        super().__init__(model, temperature, max_tokens, **kwargs)
        self.api_key = api_key
        self.client: Optional[AsyncAnthropic] = None
        self.default_max_tokens = max_tokens or 4096
        
    async def initialize(self) -> None:
        """Initialize the Anthropic client."""
        if self._initialized:
            return
            
        try:
            self.client = AsyncAnthropic(api_key=self.api_key)
            self._initialized = True
            logger.info(f"Anthropic provider initialized with model: {self.model}")
        except Exception as e:
            logger.error(f"Failed to initialize Anthropic provider: {e}")
            raise
    
    async def close(self) -> None:
        """Close the client and cleanup."""
        if self.client:
            await self.client.close()
            self.client = None
        self._initialized = False
        logger.info("Anthropic provider closed")
    
    def _convert_messages(self, messages: List[LLMMessage]) -> tuple[Optional[str], List[Dict[str, str]]]:
        """
        Convert LLMMessage format to Anthropic format.
        
        Anthropic requires system messages to be separate from conversation messages.
        
        Returns:
            Tuple of (system_message, conversation_messages)
        """
        system_message = None
        conversation_messages = []
        
        for msg in messages:
            if msg.role == "system":
                # Anthropic handles system message separately
                system_message = msg.content
            else:
                conversation_messages.append({
                    "role": msg.role,
                    "content": msg.content
                })
        
        return system_message, conversation_messages
    
    async def generate(
        self,
        messages: List[LLMMessage],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> LLMResponse:
        """
        Generate a response using Anthropic Claude API.
        
        Args:
            messages: Conversation messages
            temperature: Optional temperature override
            max_tokens: Optional max tokens override
            **kwargs: Additional parameters (top_p, top_k, etc.)
            
        Returns:
            LLMResponse with generated content
        """
        if not self._initialized:
            await self.initialize()
        
        self._validate_messages(messages)
        temp = self._get_temperature(temperature)
        tokens = max_tokens or self.default_max_tokens
        
        system_msg, conversation_msgs = self._convert_messages(messages)
        
        start_time = time.time()
        
        try:
            # Build request parameters
            request_params = {
                "model": self.model,
                "messages": conversation_messages,
                "max_tokens": tokens,
            # Build request parameters
            request_params = {
                "model": self.model,
                "messages": conversation_msgs,
                "max_tokens": tokens,
                "temperature": temp,
            }

            if "stop_sequences" in kwargs:
                request_params["stop_sequences"] = kwargs["stop_sequences"]
            
            response: Message = await self.client.messages.create(**request_params)
            
            latency = time.time() - start_time
            
            # Extract content
            content = ""
            if response.content:
                for block in response.content:
                    if hasattr(block, 'text'):
                        content += block.text
            
            # Build usage info
            usage = None
            if response.usage:
                usage = {
                    "prompt_tokens": response.usage.input_tokens,
                    "completion_tokens": response.usage.output_tokens,
                    "total_tokens": response.usage.input_tokens + response.usage.output_tokens
                }
            
            return LLMResponse(
                content=content,
                model=self.model,
                provider=self.provider_name,
                usage=usage,
                finish_reason=response.stop_reason,
                metadata={
                    "latency_seconds": latency,
                    "model_version": response.model,
                    "stop_reason": response.stop_reason
                }
            )
            
        except anthropic.APIError as e:
            logger.error(f"Anthropic API error: {e}")
            raise
        except Exception as e:
            logger.error(f"Error generating response from Anthropic: {e}")
            raise
    
    async def stream_generate(
        self,
        messages: List[LLMMessage],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> AsyncGenerator[LLMStreamChunk, None]:
        """
        Generate a streaming response using Anthropic Claude API.
        
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
        tokens = max_tokens or self.default_max_tokens
        
        system_msg, conversation_msgs = self._convert_messages(messages)
        
        try:
            # Build request parameters
            request_params = {
                "model": self.model,
                "messages": conversation_msgs,
                "max_tokens": tokens,
                "temperature": temp,
                "stream": True
            }
            
            if system_msg:
                request_params["system"] = system_msg
            
            # Add optional parameters
            if "top_p" in kwargs:
                request_params["top_p"] = kwargs["top_p"]
            if "top_k" in kwargs:
                request_params["top_k"] = kwargs["top_k"]
            
            async with self.client.messages.stream(**request_params) as stream:
                async for event in stream:
                    if hasattr(event, 'type'):
                        if event.type == "content_block_delta":
                            if hasattr(event, 'delta') and hasattr(event.delta, 'text'):
                                yield LLMStreamChunk(
                                    content=event.delta.text,
                                    finish_reason=None
                                )
                        elif event.type == "message_stop":
                            yield LLMStreamChunk(
                                content="",
                                finish_reason="end_turn"
                            )
                            
        except anthropic.APIError as e:
            logger.error(f"Anthropic streaming API error: {e}")
            raise
        except Exception as e:
            logger.error(f"Error streaming from Anthropic: {e}")
            raise
    
    async def count_tokens(self, text: str) -> int:
        """
        Estimate token count for text.
        
        Note: Anthropic doesn't provide a direct token counting API.
        This uses a rough approximation (4 chars per token).
        
        Args:
            text: Text to count tokens for
            
        Returns:
            Estimated token count
        """
        # Rough approximation: ~4 characters per token
        return len(text) // 4
    
    async def health_check(self) -> bool:
        """
        Check if Anthropic API is accessible.
        
        Returns:
            True if healthy, False otherwise
        """
        try:
            if not self._initialized:
                await self.initialize()
            
            # Simple test message
            test_messages = [LLMMessage(role="user", content="Hi")]
            
            response = await self.generate(
                messages=test_messages,
                max_tokens=10,
                temperature=0.1
            )
            
            return bool(response.content)
        except Exception as e:
            logger.error(f"Anthropic health check failed: {e}")
    @property
    def provider_name(self) -> str:
        """Get the provider name."""
        return "anthropic"


# Register provider
from .base import LLMProviderFactory
LLMProviderFactory.register_provider("anthropic", AnthropicProvider)

__all__ = ["AnthropicProvider"]
