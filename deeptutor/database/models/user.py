"""
User Model
==========

User account, profile, and preferences.
"""

from __future__ import annotations
from typing import Optional

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin, _new_uuid, _utcnow

import enum


class UserRole(str, enum.Enum):
    """Global user roles (org-level roles are in OrgMembership)."""
    SUPERADMIN = "superadmin"
    USER = "user"


class User(Base, TimestampMixin):
    """Core user account."""

    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    email_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    password_hash: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    role: Mapped[str] = mapped_column(
        String(20), default=UserRole.USER.value, nullable=False
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_login_at: Mapped[Optional[str]] = mapped_column(DateTime(timezone=True), nullable=True)
    auth_provider: Mapped[str] = mapped_column(
        String(50), default="email", nullable=False,
        doc="Authentication provider: email, google, github"
    )
    auth_provider_id: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True,
        doc="External OAuth provider user ID"
    )

    # Relationships
    profile: Mapped[Optional["UserProfile"]] = relationship(
        "UserProfile", back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    preferences: Mapped[Optional["UserPreferences"]] = relationship(
        "UserPreferences", back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    org_memberships: Mapped[list[OrgMembership]] = relationship(
        "OrgMembership", back_populates="user", cascade="all, delete-orphan"
    )
    sessions: Mapped[list[ChatSession]] = relationship(
        "ChatSession", back_populates="user", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email}>"


class UserProfile(Base, TimestampMixin):
    """Extended user profile information."""

    __tablename__ = "user_profiles"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=False, unique=True, index=True
    )
    display_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    avatar_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    bio: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    timezone: Mapped[str] = mapped_column(String(50), default="UTC", nullable=False)
    language: Mapped[str] = mapped_column(String(10), default="en", nullable=False)

    # Learning profile
    education_level: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    learning_goals: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    subjects_of_interest: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)

    # Relationship
    user: Mapped[User] = relationship("User", back_populates="profile")

    def __repr__(self) -> str:
        return f"<UserProfile user_id={self.user_id}>"


class UserPreferences(Base, TimestampMixin):
    """User preferences and settings."""

    __tablename__ = "user_preferences"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=False, unique=True, index=True
    )

    # UI preferences
    theme: Mapped[str] = mapped_column(String(20), default="dark", nullable=False)
    font_size: Mapped[str] = mapped_column(String(20), default="medium", nullable=False)
    compact_mode: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # AI preferences
    default_model: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    explanation_level: Mapped[str] = mapped_column(
        String(20), default="intermediate", nullable=False,
        doc="new | intermediate | advanced"
    )
    auto_suggestions: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Notification preferences
    email_notifications: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    study_reminders: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    weekly_digest: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationship
    user: Mapped[User] = relationship("User", back_populates="preferences")

    def __repr__(self) -> str:
        return f"<UserPreferences user_id={self.user_id}>"


# Avoid circular import for type annotations
from .org import OrgMembership  # noqa: E402
from .session import ChatSession  # noqa: E402
