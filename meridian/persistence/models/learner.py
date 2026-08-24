"""
Learner Digital Twin Models
============================

The concept graph and per-learner mastery state that back
meridian/learner/ and meridian/knowledge/. See ARCHITECTURE.md — this is
new original work, not inherited from DeepTutor.

Concept / ConceptEdge form a prerequisite DAG. LearnerEvent is an
append-only log of graded interactions. LearnerConceptState is the
Beta-Bernoulli mastery estimate derived from that log (see
meridian/learner/mastery.py for the pure update math — this module only
persists its inputs/outputs).
"""

from __future__ import annotations

from typing import Optional

from sqlalchemy import (
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TenantMixin, TimestampMixin, _new_uuid


class Concept(Base, TimestampMixin, TenantMixin):
    """A single teachable unit in the knowledge graph (e.g. "Derivatives")."""

    __tablename__ = "concepts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)
    slug: Mapped[str] = mapped_column(String(200), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    domain: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    # Embedding stored as a plain JSON float array rather than a vector
    # column type — the knowledge graph here is small and hand-curated
    # (see ARCHITECTURE.md's note on prototyping on one domain first), not
    # yet at a scale that needs pgvector/ANN search.
    embedding: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)

    def __repr__(self) -> str:
        return f"<Concept id={self.id} slug={self.slug}>"


class ConceptEdge(Base, TimestampMixin):
    """A directed edge in the prerequisite DAG: src must precede dst."""

    __tablename__ = "concept_edges"
    __table_args__ = (
        UniqueConstraint("src_id", "dst_id", "relation", name="uq_concept_edge"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)
    src_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("concepts.id"), nullable=False, index=True
    )
    dst_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("concepts.id"), nullable=False, index=True
    )
    relation: Mapped[str] = mapped_column(
        String(20), nullable=False, default="prerequisite", doc="prerequisite | related"
    )
    weight: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)

    def __repr__(self) -> str:
        return f"<ConceptEdge {self.src_id} -{self.relation}-> {self.dst_id}>"


class Misconception(Base, TimestampMixin):
    """A named, recognizable error pattern tied to a concept."""

    __tablename__ = "misconceptions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)
    concept_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("concepts.id"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    signature: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, doc="Pattern used to detect this misconception in a response"
    )
    remediation: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    def __repr__(self) -> str:
        return f"<Misconception id={self.id} name={self.name}>"


class LearnerEvent(Base, TimestampMixin):
    """Append-only log of one graded interaction. Never updated in place."""

    __tablename__ = "learner_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)
    user_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    concept_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("concepts.id"), nullable=False, index=True
    )
    event_type: Mapped[str] = mapped_column(
        String(30), nullable=False, doc="quiz | flashcard | question | chat_assessment"
    )
    difficulty: Mapped[float] = mapped_column(Float, default=0.5, nullable=False)
    correctness: Mapped[bool] = mapped_column(nullable=False)
    confidence: Mapped[Optional[float]] = mapped_column(
        Float, nullable=True, doc="Learner's self-reported confidence, if collected"
    )
    response_time_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    misconception_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("misconceptions.id"), nullable=True
    )
    source_turn_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True, index=True)

    def __repr__(self) -> str:
        return f"<LearnerEvent user={self.user_id} concept={self.concept_id} correct={self.correctness}>"


class LearnerConceptState(Base, TimestampMixin):
    """The current Beta-Bernoulli mastery estimate for one (user, concept) pair."""

    __tablename__ = "learner_concept_states"
    __table_args__ = (
        UniqueConstraint("user_id", "concept_id", name="uq_learner_concept_state"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)
    user_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    concept_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("concepts.id"), nullable=False, index=True
    )
    alpha: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    beta: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    decay_rate: Mapped[float] = mapped_column(Float, default=0.15, nullable=False)
    last_seen_at: Mapped[Optional[str]] = mapped_column(
        String(40), nullable=True, doc="ISO 8601 UTC timestamp of the last recorded event"
    )
    evidence_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    velocity: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    concept: Mapped["Concept"] = relationship("Concept")

    def __repr__(self) -> str:
        return (
            f"<LearnerConceptState user={self.user_id} concept={self.concept_id} "
            f"alpha={self.alpha:.2f} beta={self.beta:.2f}>"
        )
