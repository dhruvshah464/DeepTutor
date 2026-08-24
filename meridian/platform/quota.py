"""
Plan quota enforcement.

Plan.max_messages_per_day (and its siblings) were seeded and returned by
the billing API but never checked anywhere — a free-tier user could send
unlimited messages. This module is the missing enforcement point.

Message counts are read from the Postgres mirror
(meridian/persistence/mirror.py, ChatMessage rows written from the engine's
turn runtime), the same tap point /admin/stats and /analytics/learner use.
Anonymous/local (non-SaaS, AUTH_REQUIRED=false) usage is exempt — there is
no billing relationship to enforce a quota against.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from meridian.persistence.engine import get_db_session
from meridian.persistence.models.billing import Plan, Subscription
from meridian.persistence.models.session import ChatMessage, ChatSession
from meridian.platform.auth.dependencies import get_current_user

_DEFAULT_FREE_LIMITS = {
    "max_sessions_per_day": 10,
    "max_messages_per_day": 50,
    "max_tokens_per_month": 100_000,
}


async def get_active_plan(user_id: str, org_id: str | None, db: AsyncSession) -> Plan | None:
    """Return the Plan backing the user's (or their org's) active subscription.

    Returns None if no subscription row exists at all (e.g. a user created
    before billing.seed_plans ran, or a deployment that never seeded plans).
    Callers should treat None as "fall back to the free tier's defaults"
    rather than as unlimited.
    """
    query = select(Subscription).where(
        Subscription.user_id == user_id,
        Subscription.status.in_(["active", "trialing"]),
    )
    if org_id:
        query = select(Subscription).where(
            Subscription.org_id == org_id,
            Subscription.status.in_(["active", "trialing"]),
        )
    subscription = (await db.execute(query)).scalars().first()
    if subscription is None:
        return None
    return (
        await db.execute(select(Plan).where(Plan.id == subscription.plan_id))
    ).scalar_one_or_none()


async def check_message_quota(user: dict[str, Any], db: AsyncSession) -> None:
    """Raise HTTPException(429) if the user is at/over max_messages_per_day.

    Callable directly (for the WS chat path, which has no HTTP status codes
    to hang a FastAPI dependency off of) or via the check_quota dependency
    below (for HTTP endpoints).
    """
    user_id = str(user.get("sub") or "")
    if not user_id or user_id == "anonymous":
        return

    plan = await get_active_plan(user_id, user.get("org_id"), db)
    limit = plan.max_messages_per_day if plan else _DEFAULT_FREE_LIMITS["max_messages_per_day"]

    since = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    count = (
        await db.execute(
            select(func.count(ChatMessage.id))
            .join(ChatSession, ChatMessage.session_id == ChatSession.id)
            .where(
                ChatSession.user_id == user_id,
                ChatMessage.role == "user",
                ChatMessage.created_at >= since,
            )
        )
    ).scalar() or 0

    if count >= limit:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=(
                f"Daily message limit reached ({limit}/day on your current plan). "
                "Upgrade your plan or try again tomorrow."
            ),
        )


async def check_quota(
    user: dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """FastAPI dependency: enforce the daily message quota on an HTTP endpoint."""
    await check_message_quota(user, db)
    return user
