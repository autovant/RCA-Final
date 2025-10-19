"""
GitHub Copilot LLM provider implementation.
Provides integration with GitHub Copilot API.
"""

from typing import List, Optional, AsyncGenerator, Dict, Any
import asyncio
import httpx
import json
from datetime import datetime, timedelta
import importlib
import importlib.util
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


class GitHubCopilotProvider(BaseLLMProvider):
    """GitHub Copilot LLM provider implementation."""

    # Refresh token five minutes before remote expiry to avoid race conditions
    TOKEN_REFRESH_BUFFER_SECONDS = 300
    RETRYABLE_STATUS_CODES = {401}
    
    def __init__(
        self,
        model: str = "gpt-4",
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        github_token: Optional[str] = None,
        **kwargs
    ):
        """
        Initialize GitHub Copilot provider.
        
        Args:
            model: Model name (e.g., 'gpt-4', 'gpt-3.5-turbo', 'gpt-4o')
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            github_token: GitHub access token
            **kwargs: Additional parameters
        """
        super().__init__(model, temperature, max_tokens, **kwargs)
        self.github_token = github_token or settings.llm.GITHUB_TOKEN
        self.copilot_token: Optional[str] = None
        self.token_expiry: Optional[datetime] = None
        self._client: Optional[httpx.AsyncClient] = None
        self._token_lock: asyncio.Lock = asyncio.Lock()
    
    async def initialize(self) -> None:
        """Initialize the GitHub Copilot provider."""
        if self._initialized:
            return
        
        try:
            self._client = httpx.AsyncClient(timeout=60.0)
            
            # Get Copilot token
            await self._refresh_copilot_token()
            
            self._initialized = True
            logger.info(f"GitHub Copilot provider initialized: model={self.model}")
            
        except Exception as e:
            logger.error(f"Failed to initialize GitHub Copilot provider: {e}")
            raise
    
    async def close(self) -> None:
        """Close the provider and cleanup resources."""
        if self._client:
            await self._client.aclose()
            self._client = None
        self._initialized = False
        logger.info("GitHub Copilot provider closed")
    
    async def _refresh_copilot_token(self) -> None:
        """Refresh the Copilot token using the GitHub access token."""
        logger.info("Refreshing GitHub Copilot token...")
        
        headers = {
            "authorization": f"token {self.github_token}",
            "user-agent": "GithubCopilot/1.155.0"
        }
        
        try:
            if not self._client:
                raise RuntimeError("HTTP client not initialized")
            response = await self._client.get(
                "https://api.github.com/copilot_internal/v2/token",
                headers=headers
            )
            response.raise_for_status()
            
            data = response.json()
            self.copilot_token = data["token"]

            expires_at = data.get("expires_at")
            refresh_margin = timedelta(seconds=self.TOKEN_REFRESH_BUFFER_SECONDS)

            if isinstance(expires_at, (int, float)):
                expiry = datetime.fromtimestamp(expires_at)
            elif isinstance(expires_at, str):
                try:
                    expiry = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
                except ValueError:
                    logger.warning("Unexpected expires_at format from Copilot token response: %s", expires_at)
                    expiry = datetime.utcnow() + timedelta(minutes=25)
            else:
                logger.warning("Missing expires_at in Copilot token response; defaulting to 25 minutes")
                expiry = datetime.utcnow() + timedelta(minutes=25)

            self.token_expiry = expiry - refresh_margin
            
            logger.info("GitHub Copilot token refreshed successfully")
            
        except Exception as e:
            logger.error(f"Failed to refresh Copilot token: {e}")
            raise
    
    def _should_refresh_token(self) -> bool:
        """Determine if the current token needs refreshing."""
        if not self.copilot_token:
            return True
        if not self.token_expiry:
            return True
        return datetime.utcnow() >= self.token_expiry

    async def _ensure_valid_token(self) -> None:
        """Ensure we have a valid Copilot token."""
        if self._should_refresh_token():
            async with self._token_lock:
                # Another coroutine may have refreshed while we awaited the lock
                if self._should_refresh_token():
                    await self._refresh_copilot_token()
    
    def _format_messages(self, messages: List[LLMMessage]) -> List[Dict[str, str]]:
        """
        Format messages for GitHub Copilot API.
        
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
        Generate a response from GitHub Copilot.
        
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
        
        await self._ensure_valid_token()
        self._validate_messages(messages)
        
        start_time = time.time()
        
        try:
            # Prepare request
            formatted_messages = self._format_messages(messages)
            
            headers = {
                "authorization": f"Bearer {self.copilot_token}",
                "Copilot-Integration-Id": "vscode-chat",
                "content-type": "application/json",
                "user-agent": "GithubCopilot/1.155.0"
            }
            
            payload = {
                "messages": formatted_messages,
                "model": self.model,
                "temperature": self._get_temperature(temperature),
                "stream": False
            }
            
            if max_tokens := self._get_max_tokens(max_tokens):
                payload["max_tokens"] = max_tokens
            
            # Add any additional kwargs
            payload.update(kwargs)
            
            # Make request
            if not self._client:
                raise RuntimeError("HTTP client not initialized")

            async def _post_once() -> httpx.Response:
                return await self._client.post(
                    "https://api.githubcopilot.com/chat/completions",
                    headers=headers,
                    json=payload,
                )

            with timer(llm_request_duration_seconds, provider="github-copilot", model=self.model):
                response = await _post_once()
                if response.status_code in self.RETRYABLE_STATUS_CODES:
                    logger.info(
                        "Copilot request returned %s; refreshing token and retrying",
                        response.status_code,
                    )
                    await self._refresh_copilot_token()
                    headers["authorization"] = f"Bearer {self.copilot_token}"
                    response = await _post_once()

                response.raise_for_status()
                data = response.json()
            
            # Extract response
            choice = data["choices"][0]
            content = choice["message"]["content"]
            
            # Extract usage
            usage = None
            if "usage" in data:
                usage = {
                    "prompt_tokens": data["usage"].get("prompt_tokens", 0),
                    "completion_tokens": data["usage"].get("completion_tokens", 0),
                    "total_tokens": data["usage"].get("total_tokens", 0),
                }
            
            duration = time.time() - start_time
            latency_ms = duration * 1000
            
            # Record metrics
            MetricsCollector.record_llm_request(
                provider=self.provider_name,
                model=self.model,
                status="success",
                duration=duration,
                input_tokens=usage["prompt_tokens"] if usage else None,
                output_tokens=usage["completion_tokens"] if usage else None,
            )
            
            return LLMResponse(
                content=content,
                model=self.model,
                provider=self.provider_name,
                usage=usage,
                finish_reason=choice.get("finish_reason"),
                metadata={"latency_ms": latency_ms}
            )
            
        except Exception as e:
            duration = time.time() - start_time
            MetricsCollector.record_llm_request(
                provider=self.provider_name,
                model=self.model,
                status="error",
                duration=duration,
            )
            logger.error(f"GitHub Copilot generate failed: {e}")
            raise
    
    async def stream_generate(
        self,
        messages: List[LLMMessage],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> AsyncGenerator[LLMStreamChunk, None]:
        """
        Generate a streaming response from GitHub Copilot.
        
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
        
        await self._ensure_valid_token()
        self._validate_messages(messages)
        
        start_time = time.time()
        try:
            # Prepare request
            formatted_messages = self._format_messages(messages)
            
            headers = {
                "authorization": f"Bearer {self.copilot_token}",
                "Copilot-Integration-Id": "vscode-chat",
                "content-type": "application/json",
                "user-agent": "GithubCopilot/1.155.0"
            }
            
            payload = {
                "messages": formatted_messages,
                "model": self.model,
                "temperature": self._get_temperature(temperature),
                "stream": True
            }
            
            if max_tokens := self._get_max_tokens(max_tokens):
                payload["max_tokens"] = max_tokens
            
            # Add any additional kwargs
            payload.update(kwargs)
            
            # Make streaming request
            if not self._client:
                raise RuntimeError("HTTP client not initialized")
            for attempt in range(2):
                if not self._client:
                    raise RuntimeError("HTTP client not initialized")

                async with self._client.stream(
                    "POST",
                    "https://api.githubcopilot.com/chat/completions",
                    headers=headers,
                    json=payload,
                ) as response:
                    if response.status_code in self.RETRYABLE_STATUS_CODES and attempt == 0:
                        logger.info(
                            "Copilot stream request returned %s; refreshing token and retrying",
                            response.status_code,
                        )
                        await self._refresh_copilot_token()
                        headers["authorization"] = f"Bearer {self.copilot_token}"
                        continue

                    response.raise_for_status()

                    async for line in response.aiter_lines():
                        if not line or line == "data: [DONE]":
                            continue

                        if line.startswith("data: "):
                            try:
                                chunk_data = json.loads(line[6:])

                                if "choices" in chunk_data and chunk_data["choices"]:
                                    choice = chunk_data["choices"][0]

                                    if "delta" in choice and "content" in choice["delta"]:
                                        content = choice["delta"]["content"]
                                        yield LLMStreamChunk(
                                            content=content,
                                            finish_reason=choice.get("finish_reason"),
                                            metadata={}
                                        )
                            except json.JSONDecodeError:
                                continue
                    break
            duration = time.time() - start_time
            MetricsCollector.record_llm_request(
                provider=self.provider_name,
                model=self.model,
                status="success",
                duration=duration,
            )
            
        except Exception as e:
            duration = time.time() - start_time
            MetricsCollector.record_llm_request(
                provider=self.provider_name,
                model=self.model,
                status="error",
                duration=duration,
            )
            logger.error(f"GitHub Copilot stream failed: {e}")
            raise
    
    async def generate_stream(
        self,
        messages: List[LLMMessage],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> AsyncGenerator[LLMStreamChunk, None]:
        """Backward compatible wrapper around stream_generate."""
        async for chunk in self.stream_generate(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs,
        ):
            yield chunk

    async def count_tokens(self, text: str) -> int:
        """Estimate token usage for provided text."""
        try:
            tiktoken_spec = importlib.util.find_spec("tiktoken")
            if not tiktoken_spec:
                raise ImportError("tiktoken not installed")
            tiktoken = importlib.import_module("tiktoken")

            if "gpt-4o" in self.model:
                encoding = tiktoken.encoding_for_model("gpt-4o-mini")
            elif "gpt-4" in self.model:
                encoding = tiktoken.encoding_for_model("gpt-4")
            elif "gpt-3.5" in self.model:
                encoding = tiktoken.encoding_for_model("gpt-3.5-turbo")
            else:
                encoding = tiktoken.get_encoding("cl100k_base")
            return len(encoding.encode(text))
        except Exception as exc:  # pragma: no cover - best effort fallback
            logger.debug(
                "Falling back to approximate token counting for GitHub Copilot provider: %s",
                exc,
            )
            return max(1, len(text) // 4)
    
    async def health_check(self) -> bool:
        """
        Check if the provider is healthy and accessible.
        
        Returns:
            bool: True if provider is healthy
        """
        try:
            if not self._initialized:
                await self.initialize()
            
            await self._ensure_valid_token()
            if not self._client:
                raise RuntimeError("HTTP client not initialized")
            
            # Try to get available models
            headers = {
                "authorization": f"Bearer {self.copilot_token}",
                "Copilot-Integration-Id": "vscode-chat"
            }
            
            response = await self._client.get(
                "https://api.githubcopilot.com/models",
                headers=headers
            )
            response.raise_for_status()
            
            return True
            
        except Exception as e:
            logger.error(f"GitHub Copilot health check failed: {e}")
            return False
    
    def _get_temperature(self, override: Optional[float] = None) -> float:
        """Get temperature value."""
        return override if override is not None else self.temperature
    
    def _get_max_tokens(self, override: Optional[int] = None) -> Optional[int]:
        """Get max tokens value."""
        return override if override is not None else self.max_tokens
    
    def _validate_messages(self, messages: List[LLMMessage]) -> None:
        """Validate messages list."""
        if not messages:
            raise ValueError("Messages list cannot be empty")
        
        for msg in messages:
            if not msg.content or not msg.role:
                raise ValueError("Message must have role and content")

    @property
    def provider_name(self) -> str:
        """Return canonical provider identifier."""
        return "github-copilot"


# Register the provider
LLMProviderFactory.register_provider("github-copilot", GitHubCopilotProvider)
LLMProviderFactory.register_provider("copilot", GitHubCopilotProvider)  # Alias
