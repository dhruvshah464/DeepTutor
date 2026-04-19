"""
Analytics API Router
=====================

Learner analytics, org analytics, and usage metrics.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from deeptutor.auth.dependencies import get_current_user
from deeptutor.database.engine import get_db_session
from deeptutor.database.models.billing import UsageRecord
from deeptutor.database.models.learning import (
    FlashcardDeck,
    LearningPath,
    LearningProgress,
    QuizAttempt,
)
from deeptutor.database.models.session import ChatMessage, ChatSession

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/analytics/learner")
async def learner_analytics(
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
    days: int = Query(default=30, le=365),
):
    """Get comprehensive learner analytics."""
    user_id = user["sub"]
    since = datetime.now(timezone.utc) - timedelta(days=days)

    # Session stats
    total_sessions = (
        await db.execute(
            select(func.count(ChatSession.id)).where(
                ChatSession.user_id == user_id, ChatSession.created_at >= since
            )
        )
    ).scalar() or 0

    total_messages = (
        await db.execute(
            select(func.count(ChatMessage.id))
            .join(ChatSession, ChatMessage.session_id == ChatSession.id)
            .where(ChatSession.user_id == user_id, ChatMessage.created_at >= since)
        )
    ).scalar() or 0

    # Learning progress
    progress_entries = (
        await db.execute(
            select(LearningProgress)
            .where(LearningProgress.user_id == user_id, LearningProgress.created_at >= since)
            .order_by(LearningProgress.created_at.desc())
        )
    ).scalars().all()

    total_study_time = sum(p.time_spent_seconds for p in progress_entries)
    avg_score = (
        sum(p.score for p in progress_entries if p.score is not None)
        / max(1, sum(1 for p in progress_entries if p.score is not None))
    ) if progress_entries else 0

    # Activity by type
    activity_by_type = {}
    for p in progress_entries:
        activity_by_type[p.activity_type] = activity_by_type.get(p.activity_type, 0) + 1

    # Daily activity (for streak calculation)
    daily_activity = {}
    for p in progress_entries:
        day = str(p.created_at)[:10] if p.created_at else ""
        if day:
            daily_activity[day] = daily_activity.get(day, 0) + 1

    # Calculate streak
    streak = 0
    today = datetime.now(timezone.utc).date()
    current = today
    while str(current) in daily_activity:
        streak += 1
        current -= timedelta(days=1)

    # Quiz stats
    quiz_attempts = (
        await db.execute(
            select(func.count(QuizAttempt.id), func.avg(QuizAttempt.score))
            .where(QuizAttempt.user_id == user_id, QuizAttempt.created_at >= since)
        )
    ).one()

    # Active paths
    active_paths = (
        await db.execute(
            select(func.count(LearningPath.id)).where(
                LearningPath.user_id == user_id, LearningPath.is_active == True
            )
        )
    ).scalar() or 0

    # Flashcard stats
    total_decks = (
        await db.execute(
            select(func.count(FlashcardDeck.id)).where(FlashcardDeck.user_id == user_id)
        )
    ).scalar() or 0

    return {
        "period_days": days,
        "sessions": {"total": total_sessions, "messages": total_messages},
        "learning": {
            "total_study_time_seconds": total_study_time,
            "average_score": round(avg_score, 1),
            "activity_by_type": activity_by_type,
            "streak_days": streak,
            "active_days": len(daily_activity),
        },
        "quizzes": {
            "total_attempts": quiz_attempts[0] or 0,
            "average_score": round(float(quiz_attempts[1] or 0), 1),
        },
        "paths": {"active": active_paths},
        "flashcards": {"total_decks": total_decks},
    }


@router.get("/analytics/usage")
async def usage_analytics(
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
    days: int = Query(default=30, le=365),
):
    """Get AI usage analytics (tokens, costs)."""
    user_id = user["sub"]
    since = datetime.now(timezone.utc) - timedelta(days=days)

    # Token usage by day
    daily_usage = (
        await db.execute(
            select(
                func.date(UsageRecord.created_at).label("day"),
                UsageRecord.resource_type,
                func.sum(UsageRecord.quantity),
            )
            .where(UsageRecord.user_id == user_id, UsageRecord.created_at >= since)
            .group_by("day", UsageRecord.resource_type)
            .order_by("day")
        )
    ).all()

    # Format into daily buckets
    daily_data = {}
    for day, resource_type, qty in daily_usage:
        day_str = str(day)
        if day_str not in daily_data:
            daily_data[day_str] = {}
        daily_data[day_str][resource_type] = qty

    # Totals
    totals = (
        await db.execute(
            select(UsageRecord.resource_type, func.sum(UsageRecord.quantity))
            .where(UsageRecord.user_id == user_id, UsageRecord.created_at >= since)
            .group_by(UsageRecord.resource_type)
        )
    ).all()

    return {
        "period_days": days,
        "totals": {t: q for t, q in totals},
        "daily": daily_data,
    }
