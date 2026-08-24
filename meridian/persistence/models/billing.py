"""
Billing Models
===============

Plans, subscriptions, usage records, and invoices.
"""

from __future__ import annotations

import enum
from typing import Optional

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, TimestampMixin, _new_uuid


class PlanTier(str, enum.Enum):
    FREE = "free"
    PRO = "pro"
    TEAM = "team"
    SCHOOL = "school"
    ENTERPRISE = "enterprise"


class Plan(Base, TimestampMixin):
    """A subscription plan definition."""

    __tablename__ = "plans"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    tier: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Pricing
    price_monthly: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    price_yearly: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)
    stripe_price_id_monthly: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    stripe_price_id_yearly: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Limits
    max_sessions_per_day: Mapped[int] = mapped_column(Integer, default=10, nullable=False)
    max_messages_per_day: Mapped[int] = mapped_column(Integer, default=50, nullable=False)
    max_tokens_per_month: Mapped[int] = mapped_column(Integer, default=100000, nullable=False)
    max_knowledge_bases: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    max_uploads_per_month: Mapped[int] = mapped_column(Integer, default=5, nullable=False)
    max_upload_size_mb: Mapped[int] = mapped_column(Integer, default=10, nullable=False)
    max_searches_per_day: Mapped[int] = mapped_column(Integer, default=20, nullable=False)
    max_org_seats: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Feature flags
    features: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    def __repr__(self) -> str:
        return f"<Plan id={self.id} name={self.name} tier={self.tier}>"


class SubscriptionStatus(str, enum.Enum):
    ACTIVE = "active"
    TRIALING = "trialing"
    PAST_DUE = "past_due"
    CANCELED = "canceled"
    PAUSED = "paused"


class Subscription(Base, TimestampMixin):
    """A user or org subscription to a plan."""

    __tablename__ = "subscriptions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)
    user_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    org_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True, index=True)
    plan_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    status: Mapped[str] = mapped_column(
        String(20), default=SubscriptionStatus.ACTIVE.value, nullable=False
    )
    billing_cycle: Mapped[str] = mapped_column(
        String(20), default="monthly", nullable=False,
        doc="monthly | yearly"
    )

    # Stripe
    stripe_subscription_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, unique=True)
    stripe_customer_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Dates
    current_period_start: Mapped[Optional[str]] = mapped_column(DateTime(timezone=True), nullable=True)
    current_period_end: Mapped[Optional[str]] = mapped_column(DateTime(timezone=True), nullable=True)
    trial_end: Mapped[Optional[str]] = mapped_column(DateTime(timezone=True), nullable=True)
    canceled_at: Mapped[Optional[str]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Seats (for team/school plans)
    seat_count: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    def __repr__(self) -> str:
        return f"<Subscription id={self.id} user={self.user_id} status={self.status}>"


class UsageRecord(Base, TimestampMixin):
    """Tracks resource usage for billing and rate limiting."""

    __tablename__ = "usage_records"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)
    user_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    org_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True, index=True)
    resource_type: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True,
        doc="tokens | messages | uploads | searches | exports | sessions"
    )
    quantity: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    metadata_: Mapped[Optional[dict]] = mapped_column("metadata", JSON, nullable=True)

    # Period tracking
    period_start: Mapped[Optional[str]] = mapped_column(DateTime(timezone=True), nullable=True)
    period_end: Mapped[Optional[str]] = mapped_column(DateTime(timezone=True), nullable=True)

    def __repr__(self) -> str:
        return f"<UsageRecord user={self.user_id} type={self.resource_type} qty={self.quantity}>"


class Invoice(Base, TimestampMixin):
    """Invoice records for billing history."""

    __tablename__ = "invoices"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)
    user_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    org_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    subscription_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    stripe_invoice_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, unique=True)

    # Amounts
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), default="draft", nullable=False,
        doc="draft | open | paid | void | uncollectible"
    )

    # Dates
    period_start: Mapped[Optional[str]] = mapped_column(DateTime(timezone=True), nullable=True)
    period_end: Mapped[Optional[str]] = mapped_column(DateTime(timezone=True), nullable=True)
    paid_at: Mapped[Optional[str]] = mapped_column(DateTime(timezone=True), nullable=True)

    # PDF
    invoice_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    pdf_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    def __repr__(self) -> str:
        return f"<Invoice id={self.id} user={self.user_id} amount={self.amount} status={self.status}>"
