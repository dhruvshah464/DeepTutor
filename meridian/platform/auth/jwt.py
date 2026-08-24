"""
JWT Token Service
=================

Create and validate JWT access/refresh tokens.
"""

from __future__ import annotations

import os
import time
from typing import Any, Dict, Optional

from jose import JWTError, jwt

SECRET_KEY = os.getenv("JWT_SECRET_KEY", "dev-secret-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_SECONDS = int(os.getenv("JWT_ACCESS_EXPIRE", str(60 * 60)))  # 1 hour
REFRESH_TOKEN_EXPIRE_SECONDS = int(os.getenv("JWT_REFRESH_EXPIRE", str(60 * 60 * 24 * 30)))  # 30 days


def create_access_token(
    user_id: str,
    email: str,
    role: str = "user",
    org_id: Optional[str] = None,
    org_role: Optional[str] = None,
    extra: Optional[Dict[str, Any]] = None,
) -> str:
    """Create a JWT access token."""
    now = time.time()
    payload: Dict[str, Any] = {
        "sub": user_id,
        "email": email,
        "role": role,
        "type": "access",
        "iat": now,
        "exp": now + ACCESS_TOKEN_EXPIRE_SECONDS,
    }
    if org_id:
        payload["org_id"] = org_id
    if org_role:
        payload["org_role"] = org_role
    if extra:
        payload.update(extra)
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def create_refresh_token(user_id: str) -> str:
    """Create a JWT refresh token."""
    now = time.time()
    payload = {
        "sub": user_id,
        "type": "refresh",
        "iat": now,
        "exp": now + REFRESH_TOKEN_EXPIRE_SECONDS,
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> Dict[str, Any]:
    """
    Decode and validate a JWT token.

    Raises:
        JWTError: If the token is invalid or expired.

    Returns:
        The decoded payload dict.
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("exp", 0) < time.time():
            raise JWTError("Token has expired")
        return payload
    except JWTError:
        raise


def create_magic_link_token(email: str, expires_in: int = 600) -> str:
    """Create a short-lived token for magic link authentication (10 min default)."""
    now = time.time()
    payload = {
        "email": email,
        "type": "magic_link",
        "iat": now,
        "exp": now + expires_in,
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_magic_link_token(token: str) -> str:
    """Decode a magic link token and return the email."""
    payload = decode_token(token)
    if payload.get("type") != "magic_link":
        raise JWTError("Invalid token type")
    email = payload.get("email")
    if not email:
        raise JWTError("Missing email in token")
    return email
