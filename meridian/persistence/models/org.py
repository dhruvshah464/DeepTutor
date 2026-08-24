"""
Organization Model
==================

Multi-tenant organizations, memberships, and invitations.
"""

from __future__ import annotations

import enum
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin, _new_uuid, _utcnow


class OrgRole(str, enum.Enum):
    """Roles within an organization."""
    OWNER = "owner"
    ADMIN = "admin"
    EDUCATOR = "educator"
    LEARNER = "learner"
    ANALYST = "analyst"
    SUPPORT = "support"


class Organization(Base, TimestampMixin):
    """A tenant organization / workspace."""

    __tablename__ = "organizations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    logo_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Settings
    settings: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    max_seats: Mapped[Optional[int]] = mapped_column(nullable=True, doc="Max members, NULL = unlimited")
    plan_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True, index=True)

    # Relationships
    members: Mapped[list[OrgMembership]] = relationship(
        "OrgMembership", back_populates="organization", cascade="all, delete-orphan"
    )
    invitations: Mapped[list[Invitation]] = relationship(
        "Invitation", back_populates="organization", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Organization id={self.id} name={self.name}>"


class OrgMembership(Base, TimestampMixin):
    """Association between users and organizations with roles."""

    __tablename__ = "org_memberships"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    org_id: Mapped[str] = mapped_column(String(36), ForeignKey("organizations.id"), nullable=False, index=True)
    role: Mapped[str] = mapped_column(
        String(20), default=OrgRole.LEARNER.value, nullable=False
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    joined_at: Mapped[str] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="org_memberships")
    organization: Mapped[Organization] = relationship("Organization", back_populates="members")

    def __repr__(self) -> str:
        return f"<OrgMembership user={self.user_id} org={self.org_id} role={self.role}>"


class InvitationStatus(str, enum.Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    EXPIRED = "expired"
    REVOKED = "revoked"


class Invitation(Base, TimestampMixin):
    """Email invitation to join an organization."""

    __tablename__ = "invitations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)
    org_id: Mapped[str] = mapped_column(String(36), ForeignKey("organizations.id"), nullable=False, index=True)
    email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    role: Mapped[str] = mapped_column(
        String(20), default=OrgRole.LEARNER.value, nullable=False
    )
    invited_by: Mapped[str] = mapped_column(String(36), nullable=False)
    token: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    status: Mapped[str] = mapped_column(
        String(20), default=InvitationStatus.PENDING.value, nullable=False
    )
    expires_at: Mapped[str] = mapped_column(DateTime(timezone=True), nullable=False)

    # Relationships
    organization: Mapped[Organization] = relationship("Organization", back_populates="invitations")

    def __repr__(self) -> str:
        return f"<Invitation email={self.email} org={self.org_id} status={self.status}>"


# Deferred import for type checking
from .user import User  # noqa: E402
