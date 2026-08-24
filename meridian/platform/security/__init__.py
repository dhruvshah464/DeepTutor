"""
Security Module
================

Rate limiting, security headers, and audit logging for the DeepTutor SaaS API.

Middleware classes require the server extras (FastAPI/Starlette).
AuditService is always available.
"""

from .audit import AuditService, get_audit_service

__all__ = ["AuditService", "get_audit_service"]

# Middleware requires starlette (server extras)
try:
    from .headers import SecurityHeadersMiddleware
    from .rate_limiter import RateLimitMiddleware
    __all__ += ["RateLimitMiddleware", "SecurityHeadersMiddleware"]
except ImportError:
    pass
