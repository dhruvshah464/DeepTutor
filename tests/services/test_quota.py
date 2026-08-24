from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import HTTPException
import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from meridian.persistence.models.base import Base
from meridian.persistence.models.billing import Plan, PlanTier, Subscription, SubscriptionStatus
from meridian.persistence.models.session import ChatMessage, ChatSession
from meridian.persistence.models.user import User
from meridian.platform.quota import check_message_quota


@pytest_asyncio.fixture
async def db_session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        yield session
    await engine.dispose()


async def _seed_user_on_plan(db: AsyncSession, *, max_messages_per_day: int) -> str:
    user = User(email="learner@example.com", password_hash="x", role="user")
    db.add(user)
    await db.flush()

    plan = Plan(
        name=f"test-plan-{max_messages_per_day}",
        tier=PlanTier.FREE.value,
        max_messages_per_day=max_messages_per_day,
    )
    db.add(plan)
    await db.flush()

    db.add(
        Subscription(
            user_id=user.id,
            plan_id=plan.id,
            status=SubscriptionStatus.ACTIVE.value,
        )
    )

    session = ChatSession(id="sess-1", user_id=user.id)
    db.add(session)
    await db.flush()
    return user.id


async def _add_user_messages(db: AsyncSession, *, count: int) -> None:
    for i in range(count):
        db.add(
            ChatMessage(
                session_id="sess-1",
                role="user",
                content=f"message {i}",
                seq=i,
            )
        )
    await db.flush()


@pytest.mark.asyncio
async def test_check_message_quota_allows_under_limit(db_session: AsyncSession):
    user_id = await _seed_user_on_plan(db_session, max_messages_per_day=3)
    await _add_user_messages(db_session, count=2)

    await check_message_quota({"sub": user_id, "org_id": None}, db_session)


@pytest.mark.asyncio
async def test_check_message_quota_rejects_at_limit(db_session: AsyncSession):
    user_id = await _seed_user_on_plan(db_session, max_messages_per_day=3)
    await _add_user_messages(db_session, count=3)

    with pytest.raises(HTTPException) as exc_info:
        await check_message_quota({"sub": user_id, "org_id": None}, db_session)
    assert exc_info.value.status_code == 429


@pytest.mark.asyncio
async def test_check_message_quota_ignores_messages_from_previous_days(db_session: AsyncSession):
    user_id = await _seed_user_on_plan(db_session, max_messages_per_day=1)
    await _add_user_messages(db_session, count=1)

    # Backdate the one message to yesterday: today's count should be 0.
    message_id = (await db_session.execute(select(ChatMessage.id))).scalar_one()
    message = await db_session.get(ChatMessage, message_id)
    message.created_at = datetime.now(timezone.utc) - timedelta(days=1)
    await db_session.flush()

    await check_message_quota({"sub": user_id, "org_id": None}, db_session)


@pytest.mark.asyncio
async def test_check_message_quota_exempts_anonymous_user(db_session: AsyncSession):
    await check_message_quota({"sub": "anonymous", "org_id": None}, db_session)


@pytest.mark.asyncio
async def test_check_message_quota_falls_back_to_free_defaults_without_subscription(
    db_session: AsyncSession,
):
    user = User(email="nosub@example.com", password_hash="x", role="user")
    db_session.add(user)
    await db_session.flush()
    db_session.add(ChatSession(id="sess-2", user_id=user.id))
    await db_session.flush()

    # Default free limit is 50/day (meridian/platform/quota.py); 1 message is fine.
    db_session.add(ChatMessage(session_id="sess-2", role="user", content="hi", seq=0))
    await db_session.flush()

    await check_message_quota({"sub": user.id, "org_id": None}, db_session)
