"""
LLM providers module.

Optional providers are imported lazily to avoid hard dependencies on third-party
SDKs during environments (like CI) where those libraries are not installed.
"""

from typing import List

from core.llm.providers.base import (
    BaseLLMProvider,
    LLMProvider,
    LLMMessage,
    LLMResponse,
    LLMStreamChunk,
    LLMProviderFactory,
)

try:  # Optional provider; requires Ollama HTTP API
    from core.llm.providers.ollama import OllamaProvider
except Exception:  # pragma: no cover - dependency optional
    OllamaProvider = None  # type: ignore[assignment]

try:  # Optional provider; requires openai package
    from core.llm.providers.openai import OpenAIProvider
except Exception:  # pragma: no cover - dependency optional
    OpenAIProvider = None  # type: ignore[assignment]

try:  # Optional provider; requires boto3
    from core.llm.providers.bedrock import BedrockProvider
except Exception:  # pragma: no cover - dependency optional
    BedrockProvider = None  # type: ignore[assignment]

try:  # Optional provider; requires anthropic SDK
    from core.llm.providers.anthropic import AnthropicProvider
except Exception:  # pragma: no cover - dependency optional
    AnthropicProvider = None  # type: ignore[assignment]

try:  # Optional provider; requires vLLM client
    from core.llm.providers.vllm import VLLMProvider
except Exception:  # pragma: no cover - dependency optional
    VLLMProvider = None  # type: ignore[assignment]

try:  # Optional provider; requires LM Studio client
    from core.llm.providers.lmstudio import LMStudioProvider
except Exception:  # pragma: no cover - dependency optional
    LMStudioProvider = None  # type: ignore[assignment]

__all__: List[str] = [
    "BaseLLMProvider",
    "LLMProvider",
    "LLMMessage",
    "LLMResponse",
    "LLMStreamChunk",
    "LLMProviderFactory",
]

if OllamaProvider is not None:
    __all__.append("OllamaProvider")
if OpenAIProvider is not None:
    __all__.append("OpenAIProvider")
if BedrockProvider is not None:
    __all__.append("BedrockProvider")
if AnthropicProvider is not None:
    __all__.append("AnthropicProvider")
if VLLMProvider is not None:
    __all__.append("VLLMProvider")
if LMStudioProvider is not None:
    __all__.append("LMStudioProvider")
