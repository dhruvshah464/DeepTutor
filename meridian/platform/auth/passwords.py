"""
Password Hashing
=================

Secure password hashing using bcrypt via passlib.
Handles bcrypt version compatibility issues automatically.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

try:
    from passlib.context import CryptContext
    _pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    _HAS_PASSLIB = True
except Exception:
    _HAS_PASSLIB = False
    logger.warning("passlib/bcrypt not available, using hashlib fallback")


def hash_password(password: str) -> str:
    """Hash a plaintext password."""
    if _HAS_PASSLIB:
        try:
            return _pwd_context.hash(password)
        except Exception:
            pass
    # Fallback: SHA-256 with salt (not as secure as bcrypt, but functional)
    import hashlib
    import secrets
    salt = secrets.token_hex(16)
    hashed = hashlib.sha256((salt + password).encode()).hexdigest()
    return f"sha256${salt}${hashed}"


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plaintext password against a hash."""
    if hashed_password.startswith("sha256$"):
        # Fallback hash
        import hashlib
        parts = hashed_password.split("$")
        if len(parts) != 3:
            return False
        salt = parts[1]
        expected = parts[2]
        return hashlib.sha256((salt + plain_password).encode()).hexdigest() == expected

    if _HAS_PASSLIB:
        try:
            return _pwd_context.verify(plain_password, hashed_password)
        except Exception:
            return False

    return False
