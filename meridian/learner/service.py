"""
Adapter between the pure mastery kernel (meridian.learner.mastery) and
the persistence layer (meridian.persistence.models.learner).

Every graded interaction goes through record_event(): it appends an
immutable LearnerEvent row, then loads/creates and updates the
corresponding LearnerConceptState using the Beta-Bernoulli kernel — the
only place MasteryState gets converted to/from ORM rows.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from meridian.learner.mastery import MasteryState, update
from meridian.learner.mastery import mastery as mastery_of
from meridian.persistence.models.learner import LearnerConceptState, LearnerEvent


def state_from_row(row: LearnerConceptState | None) -> MasteryState:
    if row is None:
        return MasteryState()
    last_seen = datetime.fromisoformat(row.last_seen_at) if row.last_seen_at else None
    return MasteryState(
        alpha=row.alpha,
        beta=row.beta,
        decay_rate=row.decay_rate,
        last_seen_at=last_seen,
        evidence_count=row.evidence_count,
        velocity=row.velocity,
    )


def _apply_state_to_row(row: LearnerConceptState, state: MasteryState) -> None:
    row.alpha = state.alpha
    row.beta = state.beta
    row.decay_rate = state.decay_rate
    row.last_seen_at = state.last_seen_at.isoformat() if state.last_seen_at else None
    row.evidence_count = state.evidence_count
    row.velocity = state.velocity


async def get_concept_state(
    db: AsyncSession, *, user_id: str, concept_id: str
) -> LearnerConceptState | None:
    return (
        await db.execute(
            select(LearnerConceptState).where(
                LearnerConceptState.user_id == user_id,
                LearnerConceptState.concept_id == concept_id,
            )
        )
    ).scalar_one_or_none()


async def record_event(
    db: AsyncSession,
    *,
    user_id: str,
    concept_id: str,
    correct: bool,
    difficulty: float = 0.5,
    event_type: str = "quiz",
    confidence: float | None = None,
    response_time_ms: int | None = None,
    misconception_id: str | None = None,
    source_turn_id: str | None = None,
    now: datetime | None = None,
) -> LearnerConceptState:
    """Record one graded interaction and update the learner's mastery state.

    Writes an append-only LearnerEvent (the permanent log — never mutated
    or deleted) and upserts the derived LearnerConceptState (the current
    posterior, recomputed from the kernel — safe to ever recompute from
    the LearnerEvent log alone since the kernel is a pure fold).
    """
    now = now or datetime.now(timezone.utc)

    db.add(
        LearnerEvent(
            user_id=user_id,
            concept_id=concept_id,
            event_type=event_type,
            difficulty=difficulty,
            correctness=correct,
            confidence=confidence,
            response_time_ms=response_time_ms,
            misconception_id=misconception_id,
            source_turn_id=source_turn_id,
        )
    )

    row = await get_concept_state(db, user_id=user_id, concept_id=concept_id)
    if row is None:
        # Column defaults (alpha=1.0 etc.) only apply at flush/INSERT time,
        # not on construction — set them explicitly since state_from_row()
        # below reads them immediately, before this row has been flushed.
        default_state = MasteryState()
        row = LearnerConceptState(
            user_id=user_id,
            concept_id=concept_id,
            alpha=default_state.alpha,
            beta=default_state.beta,
            decay_rate=default_state.decay_rate,
            evidence_count=default_state.evidence_count,
            velocity=default_state.velocity,
        )
        db.add(row)

    current = state_from_row(row)
    updated = update(current, correct=correct, difficulty=difficulty, now=now)
    _apply_state_to_row(row, updated)
    await db.flush()
    return row


async def get_mastery_map(
    db: AsyncSession, *, user_id: str, concept_ids: list[str] | None = None
) -> dict[str, float]:
    """Live mastery scores for a user, decayed to "now" for every requested concept.

    Concepts with no recorded state yet fall back to the prior (0.5,
    uninformative) rather than being omitted — diagnosis over a DAG needs a
    score for every ancestor, seen or not.
    """
    from meridian.learner.mastery import decay

    query = select(LearnerConceptState).where(LearnerConceptState.user_id == user_id)
    if concept_ids is not None:
        query = query.where(LearnerConceptState.concept_id.in_(concept_ids))
    rows = (await db.execute(query)).scalars().all()

    now = datetime.now(timezone.utc)
    result = {row.concept_id: mastery_of(decay(state_from_row(row), now)) for row in rows}

    if concept_ids is not None:
        for cid in concept_ids:
            result.setdefault(cid, 0.5)
    return result
