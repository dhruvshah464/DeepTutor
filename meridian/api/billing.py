"""
Billing API Router
===================

Plan listing, subscription management, Stripe checkout, and usage tracking.
"""

from __future__ import annotations

from datetime import datetime, timezone
import logging
import os

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from meridian.persistence.engine import get_db_session
from meridian.persistence.models.billing import (
    Invoice,
    Plan,
    Subscription,
    SubscriptionStatus,
    UsageRecord,
)
from meridian.platform.auth.dependencies import get_current_user

router = APIRouter()
logger = logging.getLogger(__name__)

STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY", "")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "")


def _get_stripe():
    """Lazy-load Stripe SDK."""
    if not STRIPE_SECRET_KEY:
        return None
    try:
        import stripe
        stripe.api_key = STRIPE_SECRET_KEY
        return stripe
    except ImportError:
        logger.warning("stripe package not installed")
        return None


# ── Schemas ──

class CheckoutRequest(BaseModel):
    plan_id: str
    billing_cycle: str = "monthly"
    success_url: str = "/billing?success=true"
    cancel_url: str = "/billing?canceled=true"


# ── Endpoints ──

@router.get("/billing/plans")
async def list_plans(db: AsyncSession = Depends(get_db_session)):
    """List all available plans."""
    plans = (
        await db.execute(select(Plan).where(Plan.is_active.is_(True)).order_by(Plan.price_monthly))
    ).scalars().all()

    return [
        {
            "id": p.id,
            "name": p.name,
            "tier": p.tier,
            "description": p.description,
            "price_monthly": p.price_monthly,
            "price_yearly": p.price_yearly,
            "currency": p.currency,
            "limits": {
                "sessions_per_day": p.max_sessions_per_day,
                "messages_per_day": p.max_messages_per_day,
                "tokens_per_month": p.max_tokens_per_month,
                "knowledge_bases": p.max_knowledge_bases,
                "uploads_per_month": p.max_uploads_per_month,
                "upload_size_mb": p.max_upload_size_mb,
                "searches_per_day": p.max_searches_per_day,
                "org_seats": p.max_org_seats,
            },
            "features": p.features or {},
        }
        for p in plans
    ]


@router.get("/billing/subscription")
async def get_subscription(
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Get the current user's active subscription."""
    user_id = user["sub"]
    result = (
        await db.execute(
            select(Subscription, Plan)
            .join(Plan, Subscription.plan_id == Plan.id)
            .where(Subscription.user_id == user_id, Subscription.status.in_(["active", "trialing"]))
            .limit(1)
        )
    ).first()

    if not result:
        return {"plan": "free", "status": "active", "tier": "free"}

    sub, plan = result
    return {
        "id": sub.id,
        "plan": plan.name,
        "tier": plan.tier,
        "status": sub.status,
        "billing_cycle": sub.billing_cycle,
        "current_period_start": str(sub.current_period_start) if sub.current_period_start else None,
        "current_period_end": str(sub.current_period_end) if sub.current_period_end else None,
        "trial_end": str(sub.trial_end) if sub.trial_end else None,
        "seat_count": sub.seat_count,
        "stripe_subscription_id": sub.stripe_subscription_id,
    }


@router.post("/billing/checkout")
async def create_checkout(
    body: CheckoutRequest,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Create a Stripe checkout session for plan upgrade."""
    stripe = _get_stripe()
    if not stripe:
        raise HTTPException(
            status_code=503,
            detail="Billing is not configured. Set STRIPE_SECRET_KEY to enable.",
        )

    plan = (await db.execute(select(Plan).where(Plan.id == body.plan_id))).scalar_one_or_none()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")

    price_id = (
        plan.stripe_price_id_monthly
        if body.billing_cycle == "monthly"
        else plan.stripe_price_id_yearly
    )
    if not price_id:
        raise HTTPException(status_code=400, detail="No Stripe price configured for this plan")

    try:
        session = stripe.checkout.Session.create(
            mode="subscription",
            customer_email=user.get("email"),
            line_items=[{"price": price_id, "quantity": 1}],
            success_url=body.success_url,
            cancel_url=body.cancel_url,
            metadata={"user_id": user["sub"], "plan_id": plan.id},
        )
        return {"checkout_url": session.url}
    except Exception as e:
        logger.error("Stripe checkout error: %s", e)
        raise HTTPException(status_code=500, detail="Failed to create checkout session")


@router.post("/billing/portal")
async def create_billing_portal(
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Create a Stripe billing portal session."""
    stripe = _get_stripe()
    if not stripe:
        raise HTTPException(status_code=503, detail="Billing is not configured")

    sub = (
        await db.execute(
            select(Subscription).where(
                Subscription.user_id == user["sub"],
                Subscription.stripe_customer_id.isnot(None),
            ).limit(1)
        )
    ).scalar_one_or_none()

    if not sub or not sub.stripe_customer_id:
        raise HTTPException(status_code=404, detail="No billing account found")

    try:
        session = stripe.billing_portal.Session.create(
            customer=sub.stripe_customer_id,
            return_url="/billing",
        )
        return {"portal_url": session.url}
    except Exception as e:
        logger.error("Stripe portal error: %s", e)
        raise HTTPException(status_code=500, detail="Failed to create portal session")


@router.get("/billing/usage")
async def get_usage(
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Get usage data for the current billing period."""
    user_id = user["sub"]

    # Get current period start (start of month)
    now = datetime.now(timezone.utc)
    period_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    # Aggregate usage by type
    usage_rows = (
        await db.execute(
            select(UsageRecord.resource_type, func.sum(UsageRecord.quantity))
            .where(
                UsageRecord.user_id == user_id,
                UsageRecord.created_at >= period_start,
            )
            .group_by(UsageRecord.resource_type)
        )
    ).all()

    usage = {row[0]: row[1] for row in usage_rows}

    # Get plan limits
    sub_result = (
        await db.execute(
            select(Subscription, Plan)
            .join(Plan, Subscription.plan_id == Plan.id)
            .where(Subscription.user_id == user_id, Subscription.status == "active")
            .limit(1)
        )
    ).first()

    limits = {}
    if sub_result:
        _, plan = sub_result
        limits = {
            "tokens_per_month": plan.max_tokens_per_month,
            "messages_per_day": plan.max_messages_per_day,
            "uploads_per_month": plan.max_uploads_per_month,
            "searches_per_day": plan.max_searches_per_day,
            "sessions_per_day": plan.max_sessions_per_day,
        }

    return {
        "period_start": str(period_start),
        "usage": usage,
        "limits": limits,
    }


@router.get("/billing/invoices")
async def list_invoices(
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
    limit: int = 20,
):
    """List invoice history."""
    invoices = (
        await db.execute(
            select(Invoice)
            .where(Invoice.user_id == user["sub"])
            .order_by(Invoice.created_at.desc())
            .limit(limit)
        )
    ).scalars().all()

    return [
        {
            "id": inv.id,
            "amount": inv.amount,
            "currency": inv.currency,
            "status": inv.status,
            "period_start": str(inv.period_start) if inv.period_start else None,
            "period_end": str(inv.period_end) if inv.period_end else None,
            "paid_at": str(inv.paid_at) if inv.paid_at else None,
            "invoice_url": inv.invoice_url,
            "pdf_url": inv.pdf_url,
        }
        for inv in invoices
    ]


# ── Webhook fulfillment ──
#
# Handlers below operate on plain dict-like objects (anything supporting
# .get(), which both a real stripe.StripeObject and a plain dict satisfy)
# so they're testable with synthetic payloads without the `stripe` package
# installed — see tests/api/test_stripe_webhook.py. Each is a best-effort
# fulfillment step: a webhook this repo doesn't fully understand (e.g. a
# subscription for a stripe_subscription_id we never recorded) is logged
# and skipped rather than raising, since Stripe retries on non-2xx and
# raising here would just retry the same unresolvable event forever.

_STRIPE_STATUS_MAP = {
    "active": SubscriptionStatus.ACTIVE.value,
    "trialing": SubscriptionStatus.TRIALING.value,
    "past_due": SubscriptionStatus.PAST_DUE.value,
    "unpaid": SubscriptionStatus.PAST_DUE.value,
    "incomplete": SubscriptionStatus.PAST_DUE.value,
    "canceled": SubscriptionStatus.CANCELED.value,
    "incomplete_expired": SubscriptionStatus.CANCELED.value,
    "paused": SubscriptionStatus.PAUSED.value,
}


def _stripe_status_to_local(stripe_status: str) -> str:
    return _STRIPE_STATUS_MAP.get(stripe_status, SubscriptionStatus.ACTIVE.value)


def _unix_to_datetime(timestamp) -> datetime | None:
    if timestamp is None:
        return None
    return datetime.fromtimestamp(timestamp, tz=timezone.utc)


async def _handle_checkout_completed(db: AsyncSession, session_obj: dict) -> None:
    metadata = session_obj.get("metadata") or {}
    user_id = metadata.get("user_id")
    plan_id = metadata.get("plan_id")
    if not user_id or not plan_id:
        logger.warning(
            "checkout.session.completed missing user_id/plan_id metadata (session=%s)",
            session_obj.get("id"),
        )
        return

    sub = (
        await db.execute(select(Subscription).where(Subscription.user_id == user_id))
    ).scalars().first()
    if sub is None:
        sub = Subscription(user_id=user_id, plan_id=plan_id)
        db.add(sub)

    sub.plan_id = plan_id
    sub.status = SubscriptionStatus.ACTIVE.value
    sub.stripe_customer_id = session_obj.get("customer") or sub.stripe_customer_id
    sub.stripe_subscription_id = session_obj.get("subscription") or sub.stripe_subscription_id
    await db.flush()


async def _handle_subscription_updated(db: AsyncSession, sub_obj: dict) -> None:
    stripe_subscription_id = sub_obj.get("id")
    sub = (
        await db.execute(
            select(Subscription).where(Subscription.stripe_subscription_id == stripe_subscription_id)
        )
    ).scalar_one_or_none()
    if sub is None:
        logger.warning(
            "customer.subscription.updated for unknown stripe_subscription_id=%s",
            stripe_subscription_id,
        )
        return

    sub.status = _stripe_status_to_local(sub_obj.get("status", ""))
    sub.current_period_start = _unix_to_datetime(sub_obj.get("current_period_start"))
    sub.current_period_end = _unix_to_datetime(sub_obj.get("current_period_end"))
    sub.trial_end = _unix_to_datetime(sub_obj.get("trial_end"))
    if sub_obj.get("canceled_at"):
        sub.canceled_at = _unix_to_datetime(sub_obj.get("canceled_at"))
    await db.flush()


async def _handle_subscription_deleted(db: AsyncSession, sub_obj: dict) -> None:
    stripe_subscription_id = sub_obj.get("id")
    sub = (
        await db.execute(
            select(Subscription).where(Subscription.stripe_subscription_id == stripe_subscription_id)
        )
    ).scalar_one_or_none()
    if sub is None:
        logger.warning(
            "customer.subscription.deleted for unknown stripe_subscription_id=%s",
            stripe_subscription_id,
        )
        return

    sub.status = SubscriptionStatus.CANCELED.value
    sub.canceled_at = _unix_to_datetime(sub_obj.get("canceled_at")) or datetime.now(timezone.utc)
    await db.flush()


async def _handle_invoice_paid(db: AsyncSession, invoice_obj: dict) -> None:
    stripe_invoice_id = invoice_obj.get("id")
    stripe_subscription_id = invoice_obj.get("subscription")

    local_subscription_id = None
    user_id = None
    if stripe_subscription_id:
        sub = (
            await db.execute(
                select(Subscription).where(
                    Subscription.stripe_subscription_id == stripe_subscription_id
                )
            )
        ).scalar_one_or_none()
        if sub is not None:
            local_subscription_id = sub.id
            user_id = sub.user_id

    if user_id is None:
        logger.warning(
            "invoice.paid for unrecognized subscription=%s; skipping invoice record",
            stripe_subscription_id,
        )
        return

    invoice = (
        await db.execute(select(Invoice).where(Invoice.stripe_invoice_id == stripe_invoice_id))
    ).scalar_one_or_none()
    if invoice is None:
        invoice = Invoice(
            user_id=user_id,
            subscription_id=local_subscription_id,
            stripe_invoice_id=stripe_invoice_id,
        )
        db.add(invoice)

    invoice.amount = (invoice_obj.get("amount_paid") or 0) / 100.0
    invoice.currency = (invoice_obj.get("currency") or "usd").upper()
    invoice.status = "paid"
    invoice.period_start = _unix_to_datetime(invoice_obj.get("period_start"))
    invoice.period_end = _unix_to_datetime(invoice_obj.get("period_end"))
    invoice.paid_at = datetime.now(timezone.utc)
    invoice.invoice_url = invoice_obj.get("hosted_invoice_url")
    invoice.pdf_url = invoice_obj.get("invoice_pdf")
    await db.flush()


_WEBHOOK_HANDLERS = {
    "checkout.session.completed": _handle_checkout_completed,
    "customer.subscription.updated": _handle_subscription_updated,
    "customer.subscription.deleted": _handle_subscription_deleted,
    "invoice.paid": _handle_invoice_paid,
}


@router.post("/billing/webhooks/stripe")
async def stripe_webhook(request: Request, db: AsyncSession = Depends(get_db_session)):
    """Handle Stripe webhook events: sync local Subscription/Invoice state."""
    stripe = _get_stripe()
    if not stripe:
        raise HTTPException(status_code=503, detail="Stripe not configured")

    payload = await request.body()
    sig_header = request.headers.get("stripe-signature", "")

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, STRIPE_WEBHOOK_SECRET)
    except Exception as e:
        logger.error("Stripe webhook verification failed: %s", e)
        raise HTTPException(status_code=400, detail="Webhook verification failed")

    event_type = event.get("type", "")
    logger.info("Stripe webhook: %s", event_type)

    handler = _WEBHOOK_HANDLERS.get(event_type)
    if handler is not None:
        try:
            await handler(db, event["data"]["object"])
        except Exception as e:
            # Never let a fulfillment bug surface as a 500 that makes
            # Stripe retry indefinitely against the same broken event —
            # log it and acknowledge receipt; the event is visible in the
            # Stripe dashboard for manual replay if it truly needs one.
            logger.error("Stripe webhook fulfillment failed for %s: %s", event_type, e, exc_info=True)

    return {"received": True}
