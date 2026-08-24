"""
Auth Module
============

JWT authentication, password hashing, RBAC, and OAuth stubs
for the DeepTutor SaaS platform.

Core functions (jwt, passwords, permissions) are always available.
FastAPI-specific dependencies require the server extras to be installed.
"""

from .jwt import create_access_token, create_refresh_token, decode_token
from .passwords import hash_password, verify_password

__all__ = [
    "create_access_token",
    "create_refresh_token",
    "decode_token",
    "hash_password",
    "verify_password",
]

# FastAPI dependencies are conditionally available
try:
    from .dependencies import get_current_user, get_optional_user, require_role
    __all__ += ["get_current_user", "get_optional_user", "require_role"]
except ImportError:
    pass
