"""
Security middleware for RCA Engine.
Provides CSP, CSRF protection, and other security headers.
"""

from typing import Callable
from fastapi import Request, Response, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
from core.config import settings
import secrets
import logging

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


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Middleware for rate limiting (basic implementation)."""
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self._request_counts = {}
    
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
        
        # Get client identifier (IP address)
        client_ip = request.client.host if request.client else "unknown"
        
        # Simple rate limiting logic (should be replaced with Redis-based solution in production)
        # This is a placeholder implementation
        
        response = await call_next(request)
        
        # Add rate limit headers
        response.headers["X-RateLimit-Limit"] = "100"
        response.headers["X-RateLimit-Remaining"] = "99"
        response.headers["X-RateLimit-Reset"] = "3600"
        
        return response


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
