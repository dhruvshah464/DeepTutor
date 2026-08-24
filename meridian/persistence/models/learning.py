"""
Learning Models
================

Learning paths, progress tracking, quizzes, flashcards, and spaced repetition.
"""

from __future__ import annotations

from typing import Optional

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TenantMixin, TimestampMixin, _new_uuid


class LearningPath(Base, TimestampMixin, TenantMixin):
    """A structured learning path with ordered topics."""

    __tablename__ = "learning_paths"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)
    user_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    subject: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    difficulty: Mapped[str] = mapped_column(
        String(20), default="intermediate", nullable=False,
        doc="beginner | intermediate | advanced"
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_public: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Progress
    total_topics: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    completed_topics: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    progress_pct: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    # Structure: list of {title, description, order, status, kb_refs}
    topics: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    # AI-generated curriculum metadata
    curriculum_data: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Deadline
    target_completion: Mapped[Optional[str]] = mapped_column(DateTime(timezone=True), nullable=True)

    def __repr__(self) -> str:
        return f"<LearningPath id={self.id} title={self.title}>"


class LearningProgress(Base, TimestampMixin):
    """Granular progress tracking for learning activities."""

    __tablename__ = "learning_progress"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)
    user_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    path_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True, index=True)

    # Activity tracking
    activity_type: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True,
        doc="session | quiz | flashcard | reading | exercise"
    )
    topic: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    subject: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Performance
    score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    time_spent_seconds: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    difficulty_level: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)

    # Skill tracking
    skills_practiced: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    competency_delta: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    def __repr__(self) -> str:
        return f"<LearningProgress id={self.id} user={self.user_id} type={self.activity_type}>"


class Quiz(Base, TimestampMixin, TenantMixin):
    """An AI-generated quiz."""

    __tablename__ = "quizzes"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)
    user_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    topic: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    difficulty: Mapped[str] = mapped_column(String(20), default="intermediate", nullable=False)
    question_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Questions: list of {question, options, correct_answer, explanation, type}
    questions: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)

    # Source tracking
    kb_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    session_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    path_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)

    # Exam mode
    time_limit_minutes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    is_exam_mode: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Relationships
    attempts: Mapped[list[QuizAttempt]] = relationship(
        "QuizAttempt", back_populates="quiz", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Quiz id={self.id} title={self.title}>"


class QuizAttempt(Base, TimestampMixin):
    """A user's attempt at a quiz."""

    __tablename__ = "quiz_attempts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)
    quiz_id: Mapped[str] = mapped_column(String(36), ForeignKey("quizzes.id"), nullable=False, index=True)
    user_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)

    # Results
    score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    total_questions: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    correct_answers: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    time_taken_seconds: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Answers: list of {question_id, selected_answer, is_correct}
    answers: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)

    # Status
    completed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    completed_at: Mapped[Optional[str]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationship
    quiz: Mapped[Quiz] = relationship("Quiz", back_populates="attempts")

    def __repr__(self) -> str:
        return f"<QuizAttempt id={self.id} quiz={self.quiz_id} score={self.score}>"


class FlashcardDeck(Base, TimestampMixin, TenantMixin):
    """A collection of flashcards for spaced repetition."""

    __tablename__ = "flashcard_decks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)
    user_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    topic: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    card_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_public: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Source
    kb_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    session_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)

    # Relationships
    cards: Mapped[list[Flashcard]] = relationship(
        "Flashcard", back_populates="deck", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<FlashcardDeck id={self.id} title={self.title}>"


class Flashcard(Base, TimestampMixin):
    """A single flashcard with spaced repetition metadata (SM-2 algorithm)."""

    __tablename__ = "flashcards"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)
    deck_id: Mapped[str] = mapped_column(String(36), ForeignKey("flashcard_decks.id"), nullable=False, index=True)
    user_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)

    # Content
    front: Mapped[str] = mapped_column(Text, nullable=False)
    back: Mapped[str] = mapped_column(Text, nullable=False)
    hint: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    tags: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)

    # SM-2 Spaced Repetition fields
    ease_factor: Mapped[float] = mapped_column(Float, default=2.5, nullable=False)
    interval_days: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    repetitions: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    next_review_at: Mapped[Optional[str]] = mapped_column(DateTime(timezone=True), nullable=True)
    last_reviewed_at: Mapped[Optional[str]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Stats
    total_reviews: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    correct_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Relationship
    deck: Mapped[FlashcardDeck] = relationship("FlashcardDeck", back_populates="cards")

    def __repr__(self) -> str:
        return f"<Flashcard id={self.id} deck={self.deck_id}>"
