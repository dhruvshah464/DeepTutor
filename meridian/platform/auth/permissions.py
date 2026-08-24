"""
RBAC Permissions
=================

Permission definitions and checking utilities for role-based access control.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, Set


class Permission(str, Enum):
    """Granular permissions for the platform."""

    # Session
    SESSION_CREATE = "session:create"
    SESSION_READ = "session:read"
    SESSION_DELETE = "session:delete"

    # Knowledge Base
    KB_CREATE = "kb:create"
    KB_READ = "kb:read"
    KB_UPDATE = "kb:update"
    KB_DELETE = "kb:delete"
    KB_UPLOAD = "kb:upload"

    # Organization
    ORG_CREATE = "org:create"
    ORG_READ = "org:read"
    ORG_UPDATE = "org:update"
    ORG_DELETE = "org:delete"
    ORG_INVITE = "org:invite"
    ORG_MANAGE_MEMBERS = "org:manage_members"

    # Billing
    BILLING_VIEW = "billing:view"
    BILLING_MANAGE = "billing:manage"

    # Admin
    ADMIN_USERS = "admin:users"
    ADMIN_ORGS = "admin:orgs"
    ADMIN_BILLING = "admin:billing"
    ADMIN_AUDIT = "admin:audit"
    ADMIN_SYSTEM = "admin:system"
    ADMIN_IMPERSONATE = "admin:impersonate"

    # Learning
    LEARNING_PATH_CREATE = "learning:path:create"
    LEARNING_PATH_READ = "learning:path:read"
    QUIZ_CREATE = "quiz:create"
    QUIZ_TAKE = "quiz:take"
    FLASHCARD_CREATE = "flashcard:create"
    FLASHCARD_REVIEW = "flashcard:review"

    # Analytics
    ANALYTICS_SELF = "analytics:self"
    ANALYTICS_ORG = "analytics:org"
    ANALYTICS_GLOBAL = "analytics:global"


# Role → Permission mapping
ROLE_PERMISSIONS: Dict[str, Set[Permission]] = {
    "superadmin": set(Permission),  # All permissions
    "owner": {
        Permission.SESSION_CREATE, Permission.SESSION_READ, Permission.SESSION_DELETE,
        Permission.KB_CREATE, Permission.KB_READ, Permission.KB_UPDATE, Permission.KB_DELETE, Permission.KB_UPLOAD,
        Permission.ORG_READ, Permission.ORG_UPDATE, Permission.ORG_DELETE, Permission.ORG_INVITE, Permission.ORG_MANAGE_MEMBERS,
        Permission.BILLING_VIEW, Permission.BILLING_MANAGE,
        Permission.LEARNING_PATH_CREATE, Permission.LEARNING_PATH_READ,
        Permission.QUIZ_CREATE, Permission.QUIZ_TAKE,
        Permission.FLASHCARD_CREATE, Permission.FLASHCARD_REVIEW,
        Permission.ANALYTICS_SELF, Permission.ANALYTICS_ORG,
    },
    "admin": {
        Permission.SESSION_CREATE, Permission.SESSION_READ, Permission.SESSION_DELETE,
        Permission.KB_CREATE, Permission.KB_READ, Permission.KB_UPDATE, Permission.KB_DELETE, Permission.KB_UPLOAD,
        Permission.ORG_READ, Permission.ORG_UPDATE, Permission.ORG_INVITE, Permission.ORG_MANAGE_MEMBERS,
        Permission.BILLING_VIEW,
        Permission.LEARNING_PATH_CREATE, Permission.LEARNING_PATH_READ,
        Permission.QUIZ_CREATE, Permission.QUIZ_TAKE,
        Permission.FLASHCARD_CREATE, Permission.FLASHCARD_REVIEW,
        Permission.ANALYTICS_SELF, Permission.ANALYTICS_ORG,
    },
    "educator": {
        Permission.SESSION_CREATE, Permission.SESSION_READ,
        Permission.KB_CREATE, Permission.KB_READ, Permission.KB_UPDATE, Permission.KB_UPLOAD,
        Permission.ORG_READ,
        Permission.LEARNING_PATH_CREATE, Permission.LEARNING_PATH_READ,
        Permission.QUIZ_CREATE, Permission.QUIZ_TAKE,
        Permission.FLASHCARD_CREATE, Permission.FLASHCARD_REVIEW,
        Permission.ANALYTICS_SELF, Permission.ANALYTICS_ORG,
    },
    "learner": {
        Permission.SESSION_CREATE, Permission.SESSION_READ,
        Permission.KB_READ,
        Permission.ORG_READ,
        Permission.LEARNING_PATH_READ,
        Permission.QUIZ_TAKE,
        Permission.FLASHCARD_REVIEW,
        Permission.ANALYTICS_SELF,
    },
    "analyst": {
        Permission.SESSION_READ,
        Permission.KB_READ,
        Permission.ORG_READ,
        Permission.ANALYTICS_SELF, Permission.ANALYTICS_ORG,
    },
    "support": {
        Permission.SESSION_READ,
        Permission.KB_READ,
        Permission.ORG_READ,
        Permission.ADMIN_USERS,
    },
    "user": {
        Permission.SESSION_CREATE, Permission.SESSION_READ, Permission.SESSION_DELETE,
        Permission.KB_CREATE, Permission.KB_READ, Permission.KB_UPDATE, Permission.KB_DELETE, Permission.KB_UPLOAD,
        Permission.ORG_CREATE,
        Permission.LEARNING_PATH_CREATE, Permission.LEARNING_PATH_READ,
        Permission.QUIZ_CREATE, Permission.QUIZ_TAKE,
        Permission.FLASHCARD_CREATE, Permission.FLASHCARD_REVIEW,
        Permission.ANALYTICS_SELF,
        Permission.BILLING_VIEW, Permission.BILLING_MANAGE,
    },
}


def has_permission(user: dict[str, Any], permission: Permission) -> bool:
    """Check if a user has a specific permission."""
    role = user.get("role", "user")
    org_role = user.get("org_role", "")

    # Check global role
    if permission in ROLE_PERMISSIONS.get(role, set()):
        return True

    # Check org role
    if org_role and permission in ROLE_PERMISSIONS.get(org_role, set()):
        return True

    return False


def check_permission(user: dict[str, Any], permission: Permission) -> None:
    """Raise HTTPException if user lacks permission."""
    from fastapi import HTTPException, status

    if not has_permission(user, permission):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Permission denied: {permission.value}",
        )
