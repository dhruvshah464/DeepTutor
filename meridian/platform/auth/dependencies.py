"""
Auth Dependencies
==================

FastAPI dependency injection functions for authentication and authorization.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, Optional

from fastapi import Depends, HTTPException, Query, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from .jwt import decode_token

logger = logging.getLogger(__name__)

_bearer_scheme = HTTPBearer(auto_error=False)

# When AUTH_REQUIRED=false (dev/self-hosted), all endpoints are accessible
AUTH_REQUIRED = os.getenv("AUTH_REQUIRED", "true").lower() in ("true", "1", "yes")


def _make_anonymous_user() -> Dict[str, Any]:
    """Return a synthetic anonymous user for unauthenticated access."""
    return {
        "sub": "anonymous",
        "email": "anonymous@local",
        "role": "user",
        "org_id": None,
        "org_role": None,
        "plan_tier": "free",
    }


async def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer_scheme),
) -> Dict[str, Any]:
    """
    Resolve the current authenticated user from the JWT bearer token.

    With ``AUTH_REQUIRED=false``, returns an anonymous user stub.
    """
    if not AUTH_REQUIRED:
        return _make_anonymous_user()

    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        payload = decode_token(credentials.credentials)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not payload.get("sub"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )

    return payload


async def get_optional_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer_scheme),
) -> Optional[Dict[str, Any]]:
    """
    Like get_current_user but returns None instead of 401 if not authenticated.
    Useful for endpoints that work differently for logged-in vs anonymous users.
    """
    if credentials is None:
        if not AUTH_REQUIRED:
            return _make_anonymous_user()
        return None

    try:
        return decode_token(credentials.credentials)
    except Exception:
        return None


def require_role(*allowed_roles: str):
    """
    Dependency factory: require that the current user has one of the specified roles.

    Usage::

        @router.get("/admin/users")
        async def admin_users(user=Depends(require_role("superadmin", "admin"))):
            ...
    """

    async def _check(user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
        user_role = user.get("role", "user")
        org_role = user.get("org_role", "")
        if user_role not in allowed_roles and org_role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions. Required: %s" % ", ".join(allowed_roles),
            )
        return user

    return _check


async def require_tenant(user: Dict[str, Any] = Depends(get_current_user)) -> str:
    """
    Dependency: require the current user to belong to an organization, and
    return its ``org_id``.

    Use this on any endpoint whose data must be filtered by ``TenantMixin.org_id``
    (e.g. an org-scoped analytics or knowledge-base listing) — it is the
    counterpart to the per-user ``user["sub"]`` filtering already applied
    throughout meridian/api/learning.py and analytics.py. Raises 403 for a
    user with no org membership rather than silently returning unscoped
    (cross-tenant) data.
    """
    org_id = user.get("org_id")
    if not org_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This endpoint requires organization membership",
        )
    return org_id


async def get_ws_user(token: Optional[str] = Query(default=None, alias="token")) -> Dict[str, Any]:
    """
    Authenticate a WebSocket connection via token query parameter.

    Usage: ws://host/api/v1/ws?token=<jwt>
    """
    if not AUTH_REQUIRED:
        return _make_anonymous_user()

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="WebSocket token required",
        )

    try:
        return decode_token(token)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid WebSocket token",
        )
