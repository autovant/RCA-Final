"""
Security module for RCA Engine.
Provides convenient exports and a lightweight setup hook.
"""

from __future__ import annotations

import logging

from core.security.auth import (
    AuthService,
    get_current_user,
    get_current_active_user,
    get_current_superuser,
    pwd_context,
    security,
)
from core.security.middleware import (
    SecurityHeadersMiddleware,
    CSRFProtectionMiddleware,
    RateLimitMiddleware,
    RequestLoggingMiddleware,
)
from core.security.audit import AnalystAuditRecorder, record_related_incident_views

logger = logging.getLogger(__name__)
_security_initialised = False


def setup_security() -> None:
    """
    Idempotent initialisation hook used by the API entrypoint.

    The heavy lifting lives inside the individual auth/middleware modules;
    this helper simply ensures we emit a single log message so operators know
    the security stack has been touched.
    """
    global _security_initialised

    if _security_initialised:
        logger.debug("Security subsystem already initialised")
        return

    logger.info("Security subsystem initialised (JWT + middleware ready)")
    _security_initialised = True


__all__ = [
    "setup_security",
    "AuthService",
    "get_current_user",
    "get_current_active_user",
    "get_current_superuser",
    "pwd_context",
    "security",
    "SecurityHeadersMiddleware",
    "CSRFProtectionMiddleware",
    "RateLimitMiddleware",
    "RequestLoggingMiddleware",
    "AnalystAuditRecorder",
    "record_related_incident_views",
]
