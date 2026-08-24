"""
Password Hashing
=================

Secure password hashing using bcrypt via passlib. ``passlib[bcrypt]`` is a
declared dependency (pyproject.toml, requirements/server.txt) — its absence
means a broken install, not a condition to silently work around. Previously
this module fell back to a single-round salted SHA-256 scheme on any
passlib/bcrypt import failure, which meant a clean install missing that
dependency would silently issue weak password hashes with no error. It now
raises at import time instead.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

try:
    from passlib.context import CryptContext
except Exception as exc:  # pragma: no cover - exercised only on a broken install
    raise ImportError(
        "passlib[bcrypt] is required for password hashing but is not installed "
        "or failed to import. Install it with `pip install 'passlib[bcrypt]'` "
        "(declared in pyproject.toml and requirements/server.txt) — do not "
        "silently fall back to a weaker hashing scheme."
    ) from exc

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """Hash a plaintext password with bcrypt."""
    return _pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plaintext password against a bcrypt hash."""
    if hashed_password.startswith("sha256$"):
        # Reject legacy fallback hashes explicitly rather than silently
        # failing verification with no explanation — these can only exist
        # from installs that predate this module raising on missing bcrypt.
        logger.error(
            "Refusing to verify a legacy sha256$ password hash; the user "
            "must reset their password."
        )
        return False
    try:
        return _pwd_context.verify(plain_password, hashed_password)
    except Exception:
        return False
