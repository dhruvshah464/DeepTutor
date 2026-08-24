"""
Audit Service
==============

Centralized audit logging for all significant platform actions.
Writes to the audit_logs table via async database writes.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class AuditService:
    """
    Service for creating audit log entries.

    Usage::

        audit = AuditService()
        await audit.log(
            user_id="abc",
            action="user.login",
            description="User logged in from Chrome",
            ip_address="1.2.3.4",
        )
    """

    async def log(
        self,
        action: str,
        user_id: Optional[str] = None,
        org_id: Optional[str] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        description: Optional[str] = None,
        changes: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        request_id: Optional[str] = None,
    ) -> None:
        """Create an audit log entry."""
        try:
            from meridian.persistence.engine import get_async_session
            from meridian.persistence.models.audit import AuditLog

            async with get_async_session() as session:
                entry = AuditLog(
                    user_id=user_id,
                    org_id=org_id,
                    action=action,
                    resource_type=resource_type,
                    resource_id=resource_id,
                    description=description,
                    changes=changes,
                    metadata_=metadata,
                    ip_address=ip_address,
                    user_agent=user_agent,
                    request_id=request_id,
                )
                session.add(entry)
                # Commit happens via context manager

            logger.debug("Audit: %s (user=%s, resource=%s/%s)", action, user_id, resource_type, resource_id)
        except Exception as e:
            # Audit logging should never crash the app
            logger.warning("Failed to write audit log: %s — %s", action, e)

    async def log_auth(self, action: str, user_id: str, ip: Optional[str] = None, **kwargs: Any) -> None:
        """Convenience: log an auth-related action."""
        await self.log(action=f"auth.{action}", user_id=user_id, resource_type="auth", ip_address=ip, **kwargs)

    async def log_resource(
        self,
        action: str,
        user_id: str,
        resource_type: str,
        resource_id: str,
        description: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        """Convenience: log a resource CRUD action."""
        await self.log(
            action=f"{resource_type}.{action}",
            user_id=user_id,
            resource_type=resource_type,
            resource_id=resource_id,
            description=description,
            **kwargs,
        )


# Singleton
_audit_service: Optional[AuditService] = None


def get_audit_service() -> AuditService:
    global _audit_service
    if _audit_service is None:
        _audit_service = AuditService()
    return _audit_service
