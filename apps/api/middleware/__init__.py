"""
API middleware adapters.

Historically the API imported ``SecurityMiddleware`` from this package. The new
implementation simply re-exports the richer security middlewares that live in
``core.security.middleware`` so that existing import paths keep working.
"""

from __future__ import annotations

from core.security.middleware import (
    SecurityHeadersMiddleware as _SecurityHeadersMiddleware,
    RateLimitMiddleware as _RateLimitMiddleware,
    RequestLoggingMiddleware,
)
from apps.api.middleware.deduplication import RequestDeduplicationMiddleware


class SecurityMiddleware(_SecurityHeadersMiddleware):
    """Backwards-compatible alias for the core security headers middleware."""


RateLimitMiddleware = _RateLimitMiddleware

__all__ = [
    "SecurityMiddleware",
    "RateLimitMiddleware",
    "RequestLoggingMiddleware",
    "RequestDeduplicationMiddleware",
]
