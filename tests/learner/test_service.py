from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from meridian.learner.mastery import mastery
from meridian.learner.service import get_concept_state, get_mastery_map, record_event
from meridian.persistence.models.base import Base
from meridian.persistence.models.learner import LearnerEvent


@pytest_asyncio.fixture
async def db_session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        yield session
    await engine.dispose()


@pytest.mark.asyncio
async def test_record_event_creates_state_on_first_call(db_session: AsyncSession):
    row = await record_event(
        db_session, user_id="u1", concept_id="derivatives", correct=True, difficulty=0.6
    )
    assert row.evidence_count == 1
    assert mastery(_row_to_state(row)) > 0.5


@pytest.mark.asyncio
async def test_record_event_writes_an_append_only_learner_event(db_session: AsyncSession):
    await record_event(db_session, user_id="u1", concept_id="derivatives", correct=True)
    await record_event(db_session, user_id="u1", concept_id="derivatives", correct=False)

    events = (
        await db_session.execute(
            select(LearnerEvent).where(LearnerEvent.user_id == "u1")
        )
    ).scalars().all()
    assert len(events) == 2
    assert [e.correctness for e in events] == [True, False]


@pytest.mark.asyncio
async def test_record_event_accumulates_state_across_calls(db_session: AsyncSession):
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    for i in range(5):
        await record_event(
            db_session,
            user_id="u1",
            concept_id="derivatives",
            correct=True,
            difficulty=0.7,
            now=now + timedelta(hours=i),
        )

    row = await get_concept_state(db_session, user_id="u1", concept_id="derivatives")
    assert row is not None
    assert row.evidence_count == 5
    assert mastery(_row_to_state(row)) > 0.8


@pytest.mark.asyncio
async def test_different_users_get_isolated_states(db_session: AsyncSession):
    await record_event(db_session, user_id="alice", concept_id="derivatives", correct=True)
    await record_event(db_session, user_id="bob", concept_id="derivatives", correct=False)

    alice_state = await get_concept_state(db_session, user_id="alice", concept_id="derivatives")
    bob_state = await get_concept_state(db_session, user_id="bob", concept_id="derivatives")
    assert alice_state.alpha > alice_state.beta
    assert bob_state.beta > bob_state.alpha


@pytest.mark.asyncio
async def test_get_mastery_map_defaults_unseen_concepts_to_prior(db_session: AsyncSession):
    await record_event(db_session, user_id="u1", concept_id="calculus", correct=True, difficulty=0.9)

    scores = await get_mastery_map(
        db_session, user_id="u1", concept_ids=["calculus", "derivatives"]
    )
    assert scores["calculus"] > 0.5
    assert scores["derivatives"] == 0.5


def _row_to_state(row):
    from meridian.learner.mastery import MasteryState

    return MasteryState(
        alpha=row.alpha,
        beta=row.beta,
        decay_rate=row.decay_rate,
        evidence_count=row.evidence_count,
        velocity=row.velocity,
    )
