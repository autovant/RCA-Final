"""
Security middleware for RCA Engine.
Provides CSP, CSRF protection, and other security headers.
"""

from typing import Callable, Dict, Tuple
from fastapi import Request, Response, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
from core.config import settings
import secrets
import logging
import asyncio
import time
from dataclasses import dataclass

try:
    import redis.asyncio as redis  # type: ignore[attr-defined]
except Exception:  # pragma: no cover - optional dependency
    redis = None

logger = logging.getLogger(__name__)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware to add security headers to all responses."""
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Add security headers to response.
        
        Args:
            request: Incoming request
            call_next: Next middleware/handler
            
        Returns:
            Response: Response with security headers
        """
        response = await call_next(request)
        
        # Content Security Policy
        if settings.security.CSP_ENABLED:
            csp_directives = [
                "default-src 'self'",
                "script-src 'self' 'unsafe-inline' 'unsafe-eval'",
                "style-src 'self' 'unsafe-inline'",
                "img-src 'self' data: https:",
                "font-src 'self' data:",
                "connect-src 'self'",
                "frame-ancestors 'none'",
                "base-uri 'self'",
                "form-action 'self'"
            ]
            csp_header = "; ".join(csp_directives)
            
            if settings.security.CSP_REPORT_ONLY:
                response.headers["Content-Security-Policy-Report-Only"] = csp_header
            else:
                response.headers["Content-Security-Policy"] = csp_header
        
        # Strict Transport Security (HSTS)
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        
        # X-Content-Type-Options
        response.headers["X-Content-Type-Options"] = "nosniff"
        
        # X-Frame-Options
        response.headers["X-Frame-Options"] = "DENY"
        
        # X-XSS-Protection
        response.headers["X-XSS-Protection"] = "1; mode=block"
        
        # Referrer-Policy
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        # Permissions-Policy
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        
        return response


class CSRFProtectionMiddleware(BaseHTTPMiddleware):
    """Middleware for CSRF protection."""
    
    SAFE_METHODS = {"GET", "HEAD", "OPTIONS", "TRACE"}
    CSRF_HEADER_NAME = "X-CSRF-Token"
    CSRF_COOKIE_NAME = "csrf_token"
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
    
    def _generate_csrf_token(self) -> str:
        """Generate a new CSRF token."""
        return secrets.token_urlsafe(settings.security.CSRF_TOKEN_LENGTH)
    
    def _get_csrf_token_from_request(self, request: Request) -> str:
        """Get CSRF token from request headers or cookies."""
        # Try to get from header first
        token = request.headers.get(self.CSRF_HEADER_NAME)
        if token:
            return token
        
        # Try to get from cookie
        token = request.cookies.get(self.CSRF_COOKIE_NAME)
        if token:
            return token
        
        return ""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Validate CSRF token for unsafe methods.
        
        Args:
            request: Incoming request
            call_next: Next middleware/handler
            
        Returns:
            Response: Response with CSRF protection
        """
        # Skip CSRF check for safe methods
        if request.method in self.SAFE_METHODS:
            response = await call_next(request)
            
            # Set CSRF token cookie for safe methods
            if self.CSRF_COOKIE_NAME not in request.cookies:
                csrf_token = self._generate_csrf_token()
                response.set_cookie(
                    key=self.CSRF_COOKIE_NAME,
                    value=csrf_token,
                    httponly=settings.security.CSRF_HTTP_ONLY,
                    secure=settings.security.CSRF_SECURE,
                    samesite=settings.security.CSRF_SAME_SITE,
                    max_age=settings.security.CSRF_TOKEN_EXPIRE_MINUTES * 60
                )
            
            return response
        
        # Skip CSRF check for authentication endpoints
        if request.url.path.startswith("/api/v1/auth/"):
            return await call_next(request)
        
        # Validate CSRF token for unsafe methods
        csrf_token_from_request = self._get_csrf_token_from_request(request)
        csrf_token_from_cookie = request.cookies.get(self.CSRF_COOKIE_NAME, "")
        
        if not csrf_token_from_request or not csrf_token_from_cookie:
            logger.warning(f"CSRF token missing for {request.method} {request.url.path}")
            return JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                content={"detail": "CSRF token missing"}
            )
        
        if csrf_token_from_request != csrf_token_from_cookie:
            logger.warning(f"CSRF token mismatch for {request.method} {request.url.path}")
            return JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                content={"detail": "CSRF token invalid"}
            )
        
        response = await call_next(request)
        return response


@dataclass
class LimitStatus:
    """Represents the state of a rate limit bucket."""

    limit: int
    remaining: int
    reset: float


class RateLimitExceeded(Exception):
    """Raised when a rate limit bucket is exhausted."""

    def __init__(self, status: LimitStatus) -> None:
        self.status = status


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Middleware for rate limiting backed by Redis with local fallback."""

    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self._limits: Dict[str, Tuple[int, int]] = {
            "default": self._parse_limit(settings.security.RATE_LIMIT_DEFAULT),
            "auth": self._parse_limit(settings.security.RATE_LIMIT_AUTH),
            "burst": self._parse_limit(settings.security.RATE_LIMIT_BURST),
        }

        self._redis_enabled = (
            settings.redis.REDIS_ENABLED
            and redis is not None
            and bool(settings.redis.REDIS_URL)
        )
        self._redis = None
        if self._redis_enabled:
            try:
                self._redis = redis.from_url(
                    settings.redis.REDIS_URL,
                    encoding="utf-8",
                    decode_responses=True,
                )
            except Exception as exc:  # pragma: no cover - connection issues
                logger.warning("Redis unavailable for rate limiting: %s", exc)
                self._redis_enabled = False

        if not self._redis_enabled:
            self._local_counters: Dict[str, Tuple[int, float]] = {}
            self._lock = asyncio.Lock()
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Apply rate limiting to requests.
        
        Args:
            request: Incoming request
            call_next: Next middleware/handler
            
        Returns:
            Response: Response with rate limiting
        """
        if not settings.security.RATE_LIMITING_ENABLED:
            return await call_next(request)

        scope = "auth" if request.url.path.startswith("/api/auth/") else "default"
        scope_limit = self._limits.get(scope, self._limits["default"])
        burst_limit = self._limits["burst"]

        try:
            main_status = await self._enforce(scope, scope_limit, request)
            burst_status = await self._enforce("burst", burst_limit, request)
        except RateLimitExceeded as exc:
            headers = self._build_headers(exc.status)
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={"detail": "Rate limit exceeded"},
                headers=headers,
            )

        response = await call_next(request)

        combined_status = self._combine_status(main_status, burst_status)
        headers = self._build_headers(combined_status)
        for header, value in headers.items():
            response.headers[header] = value

        return response

    def _parse_limit(self, value: str) -> Tuple[int, int]:
        try:
            quota, period = value.split("/", 1)
            limit = int(quota)
            window = self._interval_to_seconds(period.strip())
            return max(limit, 0), max(window, 1)
        except Exception as exc:  # pragma: no cover - configuration error
            logger.warning("Invalid rate limit definition '%s': %s", value, exc)
            return 0, 1

    @staticmethod
    def _interval_to_seconds(period: str) -> int:
        normalised = period.lower().rstrip("s")
        mapping = {
            "second": 1,
            "sec": 1,
            "s": 1,
            "minute": 60,
            "min": 60,
            "m": 60,
            "hour": 3600,
            "h": 3600,
            "day": 86400,
            "d": 86400,
        }
        return mapping.get(normalised, 60)

    async def _enforce(
        self,
        scope: str,
        limit_def: Tuple[int, int],
        request: Request,
    ) -> LimitStatus:
        limit, window = limit_def
        if limit <= 0:
            return LimitStatus(limit=limit, remaining=limit, reset=time.time() + window)

        key = self._bucket_key(scope, request)

        if self._redis_enabled and self._redis is not None:
            try:
                count = await self._redis.incr(key)
                if count == 1:
                    await self._redis.expire(key, window)
                ttl = await self._redis.ttl(key)
                ttl = ttl if ttl and ttl > 0 else window

                remaining = max(0, limit - count)
                status = LimitStatus(limit=limit, remaining=remaining, reset=time.time() + ttl)

                if count > limit:
                    raise RateLimitExceeded(status)
                return status
            except Exception as exc:  # pragma: no cover - network issues
                logger.warning("Redis rate limiting failed, switching to in-memory fallback: %s", exc)
                self._redis_enabled = False
                self._local_counters = {}
                self._lock = asyncio.Lock()

        async with self._lock:
            count, expires_at = self._local_counters.get(key, (0, 0.0))
            now = time.time()
            if now >= expires_at:
                count = 0
                expires_at = now + window
            count += 1
            remaining = max(0, limit - count)
            self._local_counters[key] = (count, expires_at)

        status = LimitStatus(limit=limit, remaining=remaining, reset=expires_at)
        if count > limit:
            raise RateLimitExceeded(status)
        return status

    @staticmethod
    def _build_headers(status: LimitStatus) -> Dict[str, str]:
        reset_epoch = int(max(status.reset, time.time()))
        remaining = max(0, status.remaining)
        return {
            "X-RateLimit-Limit": str(status.limit),
            "X-RateLimit-Remaining": str(remaining),
            "X-RateLimit-Reset": str(reset_epoch),
        }

    @staticmethod
    def _combine_status(primary: LimitStatus, burst: LimitStatus) -> LimitStatus:
        remaining = min(primary.remaining, burst.remaining)
        reset = min(primary.reset, burst.reset)
        return LimitStatus(limit=primary.limit, remaining=remaining, reset=reset)

    def _bucket_key(self, scope: str, request: Request) -> str:
        client = request.client.host if request.client else "unknown"
        return f"rl:{scope}:{client}"


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for logging requests and responses."""
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Log request and response details.
        
        Args:
            request: Incoming request
            call_next: Next middleware/handler
            
        Returns:
            Response: Response after logging
        """
        # Log request
        logger.info(
            f"Request: {request.method} {request.url.path}",
            extra={
                "method": request.method,
                "path": request.url.path,
                "client": request.client.host if request.client else "unknown",
                "user_agent": request.headers.get("user-agent", "unknown")
            }
        )
        
        try:
            response = await call_next(request)
            
            # Log response
            logger.info(
                f"Response: {response.status_code}",
                extra={
                    "status_code": response.status_code,
                    "method": request.method,
                    "path": request.url.path
                }
            )
            
            return response
            
        except Exception as e:
            logger.error(
                f"Request failed: {str(e)}",
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "error": str(e)
                },
                exc_info=True
            )
            raise


# Export middleware classes
__all__ = [
    "SecurityHeadersMiddleware",
    "CSRFProtectionMiddleware",
    "RateLimitMiddleware",
    "RequestLoggingMiddleware",
]
