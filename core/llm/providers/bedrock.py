"""
AWS Bedrock LLM provider implementation.
Provides integration with AWS Bedrock models (Claude, Titan, etc.).
"""

from typing import List, Optional, AsyncGenerator, Dict, Any
import json
import boto3
from botocore.config import Config
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


class BedrockProvider(BaseLLMProvider):
    """AWS Bedrock LLM provider implementation."""
    
    def __init__(
        self,
        model: str,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        region_name: Optional[str] = None,
        aws_access_key_id: Optional[str] = None,
        aws_secret_access_key: Optional[str] = None,
        **kwargs
    ):
        """
        Initialize Bedrock provider.
        
        Args:
            model: Model ID (e.g., 'anthropic.claude-v2', 'amazon.titan-text-express-v1')
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            region_name: AWS region
            aws_access_key_id: Optional AWS access key
            aws_secret_access_key: Optional AWS secret key
            **kwargs: Additional parameters
        """
        super().__init__(model, temperature, max_tokens, **kwargs)
        self.region_name = region_name or settings.llm.BEDROCK_REGION
        self.aws_access_key_id = aws_access_key_id
        self.aws_secret_access_key = aws_secret_access_key
        self._client = None
        self._runtime_client = None
    
    async def initialize(self) -> None:
        """Initialize the Bedrock provider."""
        if self._initialized:
            return
        
        try:
            # Configure boto3
            config = Config(
                region_name=self.region_name,
                retries={'max_attempts': 3, 'mode': 'adaptive'}
            )
            
            session_kwargs = {'region_name': self.region_name}
            if self.aws_access_key_id and self.aws_secret_access_key:
                session_kwargs['aws_access_key_id'] = self.aws_access_key_id
                session_kwargs['aws_secret_access_key'] = self.aws_secret_access_key
            
            # Create clients
            self._client = boto3.client('bedrock', config=config, **session_kwargs)
            self._runtime_client = boto3.client('bedrock-runtime', config=config, **session_kwargs)
            
            # Test connection
            await self.health_check()
            
            self._initialized = True
            logger.info(f"Bedrock provider initialized: model={self.model}, region={self.region_name}")
            
        except Exception as e:
            logger.error(f"Failed to initialize Bedrock provider: {e}")
            raise
    
    async def close(self) -> None:
        """Close the provider and cleanup resources."""
        self._client = None
        self._runtime_client = None
        self._initialized = False
        logger.info("Bedrock provider closed")
    
    def _format_messages_for_claude(self, messages: List[LLMMessage]) -> Dict[str, Any]:
        """
        Format messages for Claude models.
        
        Args:
            messages: List of messages
            
        Returns:
            Dict[str, Any]: Formatted request body
        """
        # Extract system message if present
        system_message = None
        conversation_messages = []
        
        for msg in messages:
            if msg.role == "system":
                system_message = msg.content
            else:
                conversation_messages.append({
                    "role": msg.role,
                    "content": msg.content
                })
        
        body = {
            "messages": conversation_messages,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens or 4096,
        }
        
        if system_message:
            body["system"] = system_message
        
        return body
    
    def _format_messages_for_titan(self, messages: List[LLMMessage]) -> Dict[str, Any]:
        """
        Format messages for Titan models.
        
        Args:
            messages: List of messages
            
        Returns:
            Dict[str, Any]: Formatted request body
        """
        # Combine all messages into a single prompt
        prompt_parts = []
        for msg in messages:
            if msg.role == "system":
                prompt_parts.append(f"System: {msg.content}")
            elif msg.role == "user":
                prompt_parts.append(f"User: {msg.content}")
            elif msg.role == "assistant":
                prompt_parts.append(f"Assistant: {msg.content}")
        
        prompt = "\n\n".join(prompt_parts) + "\n\nAssistant:"
        
        return {
            "inputText": prompt,
            "textGenerationConfig": {
                "temperature": self.temperature,
                "maxTokenCount": self.max_tokens or 4096,
            }
        }
    
    def _get_model_family(self) -> str:
        """
        Get the model family from model ID.
        
        Returns:
            str: Model family (claude, titan, etc.)
        """
        if "claude" in self.model.lower():
            return "claude"
        elif "titan" in self.model.lower():
            return "titan"
        else:
            return "unknown"
    
    async def generate(
        self,
        messages: List[LLMMessage],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> LLMResponse:
        """
        Generate a response from Bedrock.
        
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
            # Format request based on model family
            model_family = self._get_model_family()
            
            if model_family == "claude":
                body = self._format_messages_for_claude(messages)
            elif model_family == "titan":
                body = self._format_messages_for_titan(messages)
            else:
                raise ValueError(f"Unsupported model family: {model_family}")
            
            # Override temperature and max_tokens if provided
            if temperature is not None:
                if model_family == "claude":
                    body["temperature"] = self._get_temperature(temperature)
                elif model_family == "titan":
                    body["textGenerationConfig"]["temperature"] = self._get_temperature(temperature)
            
            if max_tokens is not None:
                if model_family == "claude":
                    body["max_tokens"] = self._get_max_tokens(max_tokens)
                elif model_family == "titan":
                    body["textGenerationConfig"]["maxTokenCount"] = self._get_max_tokens(max_tokens)
            
            # Make request
            with timer(llm_request_duration_seconds, provider="bedrock", model=self.model):
                response = self._runtime_client.invoke_model(
                    modelId=self.model,
                    body=json.dumps(body)
                )
            
            # Parse response
            response_body = json.loads(response['body'].read())
            
            # Extract content based on model family
            if model_family == "claude":
                content = response_body.get("content", [{}])[0].get("text", "")
                usage = {
                    "prompt_tokens": response_body.get("usage", {}).get("input_tokens", 0),
                    "completion_tokens": response_body.get("usage", {}).get("output_tokens", 0),
                    "total_tokens": (
                        response_body.get("usage", {}).get("input_tokens", 0) +
                        response_body.get("usage", {}).get("output_tokens", 0)
                    ),
                }
                finish_reason = response_body.get("stop_reason")
            elif model_family == "titan":
                content = response_body.get("results", [{}])[0].get("outputText", "")
                usage = {
                    "prompt_tokens": response_body.get("inputTextTokenCount", 0),
                    "completion_tokens": response_body.get("results", [{}])[0].get("tokenCount", 0),
                    "total_tokens": (
                        response_body.get("inputTextTokenCount", 0) +
                        response_body.get("results", [{}])[0].get("tokenCount", 0)
                    ),
                }
                finish_reason = response_body.get("results", [{}])[0].get("completionReason")
            else:
                content = ""
                usage = {}
                finish_reason = None
            
            duration = time.time() - start_time
            
            # Record metrics
            MetricsCollector.record_llm_request(
                provider="bedrock",
                model=self.model,
                status="success",
                duration=duration,
                input_tokens=usage.get("prompt_tokens"),
                output_tokens=usage.get("completion_tokens")
            )
            
            logger.info(
                f"Bedrock generation completed: model={self.model}, "
                f"tokens={usage.get('total_tokens', 0)}, duration={duration:.2f}s"
            )
            
            return LLMResponse(
                content=content,
                model=self.model,
                provider="bedrock",
                usage=usage,
                finish_reason=finish_reason,
                metadata={"raw_response": response_body}
            )
            
        except Exception as e:
            duration = time.time() - start_time
            MetricsCollector.record_llm_request(
                provider="bedrock",
                model=self.model,
                status="error",
                duration=duration
            )
            logger.error(f"Bedrock generation failed: {e}")
            raise
    
    async def stream_generate(
        self,
        messages: List[LLMMessage],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> AsyncGenerator[LLMStreamChunk, None]:
        """
        Generate a streaming response from Bedrock.
        
        Note: Streaming support varies by model. This is a placeholder implementation.
        
        Args:
            messages: List of conversation messages
            temperature: Optional temperature override
            max_tokens: Optional max tokens override
            **kwargs: Additional generation parameters
            
        Yields:
            LLMStreamChunk: Streaming response chunks
        """
        # For now, fall back to non-streaming and yield as single chunk
        response = await self.generate(messages, temperature, max_tokens, **kwargs)
        yield LLMStreamChunk(
            content=response.content,
            finish_reason=response.finish_reason,
            metadata=response.metadata
        )
    
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
        Check if Bedrock is accessible.
        
        Returns:
            bool: True if healthy, False otherwise
        """
        try:
            if not self._client:
                return False
            
            # Try to list foundation models
            self._client.list_foundation_models()
            return True
            
        except Exception as e:
            logger.error(f"Bedrock health check failed: {e}")
            return False
    
    @property
    def provider_name(self) -> str:
        """Get the provider name."""
        return "bedrock"


# Register provider with factory
LLMProviderFactory.register_provider("bedrock", BedrockProvider)


__all__ = ["BedrockProvider"]
