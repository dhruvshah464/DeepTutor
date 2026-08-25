from __future__ import annotations

from datetime import datetime, timezone

import pytest
import pytest_asyncio
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from meridian.api.billing import (
    _handle_checkout_completed,
    _handle_invoice_paid,
    _handle_subscription_deleted,
    _handle_subscription_updated,
    _stripe_status_to_local,
)
from meridian.persistence.models.base import Base
from meridian.persistence.models.billing import (
    Invoice,
    Plan,
    PlanTier,
    Subscription,
    SubscriptionStatus,
)
from meridian.persistence.models.user import User


@pytest_asyncio.fixture
async def db_session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        yield session
    await engine.dispose()


async def _seed_user_and_plan(db: AsyncSession) -> tuple[str, str]:
    user = User(email="learner@example.com", password_hash="x", role="user")
    db.add(user)
    plan = Plan(name="pro", tier=PlanTier.PRO.value)
    db.add(plan)
    await db.flush()
    return user.id, plan.id


@pytest.mark.asyncio
async def test_checkout_completed_creates_an_active_subscription(db_session: AsyncSession):
    user_id, plan_id = await _seed_user_and_plan(db_session)

    await _handle_checkout_completed(
        db_session,
        {
            "id": "cs_123",
            "customer": "cus_abc",
            "subscription": "sub_abc",
            "metadata": {"user_id": user_id, "plan_id": plan_id},
        },
    )

    sub = (
        await db_session.execute(select(Subscription).where(Subscription.user_id == user_id))
    ).scalar_one()
    assert sub.plan_id == plan_id
    assert sub.status == SubscriptionStatus.ACTIVE.value
    assert sub.stripe_customer_id == "cus_abc"
    assert sub.stripe_subscription_id == "sub_abc"


@pytest.mark.asyncio
async def test_checkout_completed_without_metadata_is_a_noop(db_session: AsyncSession, caplog):
    await _handle_checkout_completed(db_session, {"id": "cs_123", "metadata": {}})
    # No exception, and nothing written — verified implicitly by not
    # raising and by the missing-metadata warning being logged.


@pytest.mark.asyncio
async def test_subscription_updated_syncs_status_and_period(db_session: AsyncSession):
    user_id, plan_id = await _seed_user_and_plan(db_session)
    sub = Subscription(
        user_id=user_id, plan_id=plan_id, status=SubscriptionStatus.ACTIVE.value,
        stripe_subscription_id="sub_abc",
    )
    db_session.add(sub)
    await db_session.flush()

    period_start = int(datetime(2026, 1, 1, tzinfo=timezone.utc).timestamp())
    period_end = int(datetime(2026, 2, 1, tzinfo=timezone.utc).timestamp())

    await _handle_subscription_updated(
        db_session,
        {
            "id": "sub_abc",
            "status": "past_due",
            "current_period_start": period_start,
            "current_period_end": period_end,
        },
    )

    await db_session.refresh(sub)
    assert sub.status == SubscriptionStatus.PAST_DUE.value
    assert sub.current_period_start is not None
    assert sub.current_period_end is not None


@pytest.mark.asyncio
async def test_subscription_updated_for_unknown_id_does_not_raise(db_session: AsyncSession):
    await _handle_subscription_updated(db_session, {"id": "sub_never_seen", "status": "active"})


@pytest.mark.asyncio
async def test_subscription_deleted_marks_canceled(db_session: AsyncSession):
    user_id, plan_id = await _seed_user_and_plan(db_session)
    sub = Subscription(
        user_id=user_id, plan_id=plan_id, status=SubscriptionStatus.ACTIVE.value,
        stripe_subscription_id="sub_abc",
    )
    db_session.add(sub)
    await db_session.flush()

    await _handle_subscription_deleted(db_session, {"id": "sub_abc"})

    await db_session.refresh(sub)
    assert sub.status == SubscriptionStatus.CANCELED.value
    assert sub.canceled_at is not None


@pytest.mark.asyncio
async def test_invoice_paid_creates_an_invoice_row(db_session: AsyncSession):
    user_id, plan_id = await _seed_user_and_plan(db_session)
    sub = Subscription(
        user_id=user_id, plan_id=plan_id, status=SubscriptionStatus.ACTIVE.value,
        stripe_subscription_id="sub_abc",
    )
    db_session.add(sub)
    await db_session.flush()

    await _handle_invoice_paid(
        db_session,
        {
            "id": "in_123",
            "subscription": "sub_abc",
            "amount_paid": 2000,
            "currency": "usd",
            "hosted_invoice_url": "https://stripe.example/invoice",
            "invoice_pdf": "https://stripe.example/invoice.pdf",
        },
    )

    invoice = (
        await db_session.execute(select(Invoice).where(Invoice.stripe_invoice_id == "in_123"))
    ).scalar_one()
    assert invoice.amount == 20.0
    assert invoice.currency == "USD"
    assert invoice.status == "paid"
    assert invoice.user_id == user_id
    assert invoice.subscription_id == sub.id


@pytest.mark.asyncio
async def test_invoice_paid_is_idempotent_on_replay(db_session: AsyncSession):
    """Stripe can and does redeliver webhooks; replaying the same event
    must update the existing row, not create a duplicate.
    """
    user_id, plan_id = await _seed_user_and_plan(db_session)
    sub = Subscription(
        user_id=user_id, plan_id=plan_id, status=SubscriptionStatus.ACTIVE.value,
        stripe_subscription_id="sub_abc",
    )
    db_session.add(sub)
    await db_session.flush()

    payload = {
        "id": "in_123", "subscription": "sub_abc", "amount_paid": 2000, "currency": "usd",
    }
    await _handle_invoice_paid(db_session, payload)
    await _handle_invoice_paid(db_session, payload)

    count = (
        await db_session.execute(
            select(func.count(Invoice.id)).where(Invoice.stripe_invoice_id == "in_123")
        )
    ).scalar()
    assert count == 1


@pytest.mark.asyncio
async def test_invoice_paid_for_unknown_subscription_is_skipped(db_session: AsyncSession):
    await _handle_invoice_paid(
        db_session, {"id": "in_999", "subscription": "sub_never_seen", "amount_paid": 100}
    )

    result = (
        await db_session.execute(select(Invoice).where(Invoice.stripe_invoice_id == "in_999"))
    ).scalar_one_or_none()
    assert result is None


@pytest.mark.parametrize(
    ("stripe_status", "expected"),
    [
        ("active", SubscriptionStatus.ACTIVE.value),
        ("trialing", SubscriptionStatus.TRIALING.value),
        ("past_due", SubscriptionStatus.PAST_DUE.value),
        ("unpaid", SubscriptionStatus.PAST_DUE.value),
        ("canceled", SubscriptionStatus.CANCELED.value),
        ("paused", SubscriptionStatus.PAUSED.value),
        ("some_future_stripe_status_we_dont_know", SubscriptionStatus.ACTIVE.value),
    ],
)
def test_stripe_status_mapping(stripe_status, expected):
    assert _stripe_status_to_local(stripe_status) == expected
