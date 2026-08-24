"""
Learning API Router
====================

Learning paths, quizzes, flashcards, and spaced repetition endpoints.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from meridian.persistence.engine import get_db_session
from meridian.persistence.models.learning import (
    Flashcard,
    FlashcardDeck,
    LearningPath,
    LearningProgress,
    Quiz,
    QuizAttempt,
)
from meridian.platform.auth.dependencies import get_current_user

router = APIRouter()
logger = logging.getLogger(__name__)


# ── Schemas ──

class CreatePathRequest(BaseModel):
    title: str = Field(min_length=1, max_length=500)
    description: str | None = None
    subject: str | None = None
    difficulty: str = "intermediate"
    topics: list[dict] | None = None
    target_completion: str | None = None


class CreateQuizRequest(BaseModel):
    title: str = Field(min_length=1, max_length=500)
    topic: str | None = None
    difficulty: str = "intermediate"
    question_count: int = Field(default=10, ge=1, le=50)
    kb_id: str | None = None
    session_id: str | None = None
    is_exam_mode: bool = False
    time_limit_minutes: int | None = None


class SubmitQuizRequest(BaseModel):
    answers: list[dict]
    time_taken_seconds: int | None = None


class CreateDeckRequest(BaseModel):
    title: str = Field(min_length=1, max_length=500)
    description: str | None = None
    topic: str | None = None


class CreateFlashcardRequest(BaseModel):
    front: str
    back: str
    hint: str | None = None
    tags: list[str] | None = None


class ReviewFlashcardRequest(BaseModel):
    quality: int = Field(ge=0, le=5, description="SM-2 quality rating: 0=blackout, 5=perfect")


# ── Learning Paths ──

@router.post("/learning/paths", status_code=201)
async def create_learning_path(
    body: CreatePathRequest,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Create a new learning path."""
    path = LearningPath(
        user_id=user["sub"],
        title=body.title,
        description=body.description,
        subject=body.subject,
        difficulty=body.difficulty,
        topics=body.topics or [],
        total_topics=len(body.topics) if body.topics else 0,
    )
    db.add(path)
    await db.flush()
    return {"id": path.id, "title": path.title}


@router.get("/learning/paths")
async def list_learning_paths(
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """List the user's learning paths."""
    paths = (
        await db.execute(
            select(LearningPath)
            .where(LearningPath.user_id == user["sub"])
            .order_by(LearningPath.created_at.desc())
        )
    ).scalars().all()

    return [
        {
            "id": p.id,
            "title": p.title,
            "subject": p.subject,
            "difficulty": p.difficulty,
            "progress_pct": p.progress_pct,
            "total_topics": p.total_topics,
            "completed_topics": p.completed_topics,
            "is_active": p.is_active,
            "created_at": str(p.created_at),
        }
        for p in paths
    ]


@router.get("/learning/progress")
async def get_learning_progress(
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
    days: int = Query(default=30, le=365),
):
    """Get learning progress summary."""
    user_id = user["sub"]
    since = datetime.now(timezone.utc) - timedelta(days=days)

    # Activity count by type
    activities = (
        await db.execute(
            select(LearningProgress.activity_type, func.count(LearningProgress.id))
            .where(LearningProgress.user_id == user_id, LearningProgress.created_at >= since)
            .group_by(LearningProgress.activity_type)
        )
    ).all()

    # Total time spent
    total_time = (
        await db.execute(
            select(func.sum(LearningProgress.time_spent_seconds))
            .where(LearningProgress.user_id == user_id, LearningProgress.created_at >= since)
        )
    ).scalar() or 0

    # Average scores
    avg_score = (
        await db.execute(
            select(func.avg(LearningProgress.score))
            .where(
                LearningProgress.user_id == user_id,
                LearningProgress.score.isnot(None),
                LearningProgress.created_at >= since,
            )
        )
    ).scalar()

    return {
        "period_days": days,
        "activities": {t: c for t, c in activities},
        "total_time_seconds": total_time,
        "average_score": round(float(avg_score), 2) if avg_score else None,
    }


# ── Quizzes ──

@router.post("/learning/quizzes", status_code=201)
async def create_quiz(
    body: CreateQuizRequest,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Create a quiz (questions can be AI-generated later via capability)."""
    quiz = Quiz(
        user_id=user["sub"],
        title=body.title,
        topic=body.topic,
        difficulty=body.difficulty,
        question_count=body.question_count,
        kb_id=body.kb_id,
        session_id=body.session_id,
        is_exam_mode=body.is_exam_mode,
        time_limit_minutes=body.time_limit_minutes,
    )
    db.add(quiz)
    await db.flush()
    return {"id": quiz.id, "title": quiz.title}


@router.get("/learning/quizzes")
async def list_quizzes(
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
    limit: int = 20,
):
    """List the user's quizzes."""
    quizzes = (
        await db.execute(
            select(Quiz)
            .where(Quiz.user_id == user["sub"])
            .order_by(Quiz.created_at.desc())
            .limit(limit)
        )
    ).scalars().all()

    return [
        {
            "id": q.id,
            "title": q.title,
            "topic": q.topic,
            "difficulty": q.difficulty,
            "question_count": q.question_count,
            "is_exam_mode": q.is_exam_mode,
            "created_at": str(q.created_at),
        }
        for q in quizzes
    ]


@router.get("/learning/quizzes/{quiz_id}")
async def get_quiz(
    quiz_id: str,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Get quiz details with questions."""
    quiz = (
        await db.execute(
            select(Quiz).where(Quiz.id == quiz_id, Quiz.user_id == user["sub"])
        )
    ).scalar_one_or_none()
    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz not found")

    return {
        "id": quiz.id,
        "title": quiz.title,
        "topic": quiz.topic,
        "difficulty": quiz.difficulty,
        "question_count": quiz.question_count,
        "questions": quiz.questions or [],
        "is_exam_mode": quiz.is_exam_mode,
        "time_limit_minutes": quiz.time_limit_minutes,
    }


@router.post("/learning/quizzes/{quiz_id}/submit")
async def submit_quiz(
    quiz_id: str,
    body: SubmitQuizRequest,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Submit quiz answers and get results."""
    quiz = (
        await db.execute(
            select(Quiz).where(Quiz.id == quiz_id, Quiz.user_id == user["sub"])
        )
    ).scalar_one_or_none()
    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz not found")

    # Score the quiz
    questions = quiz.questions or []
    correct = 0
    for answer in body.answers:
        q_idx = answer.get("question_index", -1)
        if 0 <= q_idx < len(questions):
            if answer.get("selected") == questions[q_idx].get("correct_answer"):
                correct += 1

    total = len(questions)
    score = (correct / total * 100) if total > 0 else 0

    attempt = QuizAttempt(
        quiz_id=quiz.id,
        user_id=user["sub"],
        score=score,
        total_questions=total,
        correct_answers=correct,
        time_taken_seconds=body.time_taken_seconds,
        answers=body.answers,
        completed=True,
        completed_at=datetime.now(timezone.utc),
    )
    db.add(attempt)

    # Track progress
    progress = LearningProgress(
        user_id=user["sub"],
        activity_type="quiz",
        topic=quiz.topic,
        score=score,
        time_spent_seconds=body.time_taken_seconds or 0,
        difficulty_level=quiz.difficulty,
    )
    db.add(progress)
    await db.flush()

    return {
        "attempt_id": attempt.id,
        "score": score,
        "correct": correct,
        "total": total,
    }


# ── Flashcards ──

@router.post("/learning/flashcard-decks", status_code=201)
async def create_deck(
    body: CreateDeckRequest,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Create a flashcard deck."""
    deck = FlashcardDeck(
        user_id=user["sub"],
        title=body.title,
        description=body.description,
        topic=body.topic,
    )
    db.add(deck)
    await db.flush()
    return {"id": deck.id, "title": deck.title}


@router.get("/learning/flashcard-decks")
async def list_decks(
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """List the user's flashcard decks."""
    decks = (
        await db.execute(
            select(FlashcardDeck)
            .where(FlashcardDeck.user_id == user["sub"])
            .order_by(FlashcardDeck.created_at.desc())
        )
    ).scalars().all()

    return [
        {
            "id": d.id,
            "title": d.title,
            "description": d.description,
            "topic": d.topic,
            "card_count": d.card_count,
            "created_at": str(d.created_at),
        }
        for d in decks
    ]


@router.post("/learning/flashcard-decks/{deck_id}/cards", status_code=201)
async def add_flashcard(
    deck_id: str,
    body: CreateFlashcardRequest,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Add a flashcard to a deck."""
    deck = (
        await db.execute(
            select(FlashcardDeck).where(
                FlashcardDeck.id == deck_id, FlashcardDeck.user_id == user["sub"]
            )
        )
    ).scalar_one_or_none()
    if not deck:
        raise HTTPException(status_code=404, detail="Deck not found")

    card = Flashcard(
        deck_id=deck_id,
        user_id=user["sub"],
        front=body.front,
        back=body.back,
        hint=body.hint,
        tags=body.tags,
        next_review_at=datetime.now(timezone.utc),
    )
    db.add(card)
    deck.card_count += 1
    await db.flush()

    return {"id": card.id}


@router.get("/learning/flashcard-decks/{deck_id}/review")
async def get_review_cards(
    deck_id: str,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
    limit: int = Query(default=20, le=50),
):
    """Get flashcards due for review (spaced repetition)."""
    now = datetime.now(timezone.utc)
    cards = (
        await db.execute(
            select(Flashcard)
            .where(
                Flashcard.deck_id == deck_id,
                Flashcard.user_id == user["sub"],
                (Flashcard.next_review_at <= now) | (Flashcard.next_review_at.is_(None)),
            )
            .order_by(Flashcard.next_review_at.asc())
            .limit(limit)
        )
    ).scalars().all()

    return [
        {
            "id": c.id,
            "front": c.front,
            "back": c.back,
            "hint": c.hint,
            "tags": c.tags,
            "repetitions": c.repetitions,
            "ease_factor": c.ease_factor,
        }
        for c in cards
    ]


@router.post("/learning/flashcards/{card_id}/review")
async def review_flashcard(
    card_id: str,
    body: ReviewFlashcardRequest,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Submit a flashcard review result using SM-2 algorithm."""
    card = (
        await db.execute(select(Flashcard).where(Flashcard.id == card_id, Flashcard.user_id == user["sub"]))
    ).scalar_one_or_none()
    if not card:
        raise HTTPException(status_code=404, detail="Flashcard not found")

    q = body.quality  # 0-5 rating
    now = datetime.now(timezone.utc)

    # SM-2 Algorithm
    if q >= 3:
        # Correct response
        if card.repetitions == 0:
            card.interval_days = 1
        elif card.repetitions == 1:
            card.interval_days = 6
        else:
            card.interval_days = round(card.interval_days * card.ease_factor)
        card.repetitions += 1
        card.correct_count += 1
    else:
        # Incorrect — reset
        card.repetitions = 0
        card.interval_days = 1

    # Update ease factor
    card.ease_factor = max(
        1.3,
        card.ease_factor + (0.1 - (5 - q) * (0.08 + (5 - q) * 0.02)),
    )

    card.total_reviews += 1
    card.last_reviewed_at = now
    card.next_review_at = now + timedelta(days=card.interval_days)

    # Track progress
    progress = LearningProgress(
        user_id=user["sub"],
        activity_type="flashcard",
        score=q / 5 * 100,
        time_spent_seconds=5,
    )
    db.add(progress)
    await db.flush()

    return {
        "card_id": card.id,
        "next_review_at": str(card.next_review_at),
        "interval_days": card.interval_days,
        "ease_factor": round(card.ease_factor, 2),
    }
