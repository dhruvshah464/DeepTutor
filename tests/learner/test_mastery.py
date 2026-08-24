from __future__ import annotations

from datetime import datetime, timedelta, timezone

from meridian.learner.mastery import (
    confidence,
    decay,
    initial_state,
    mastery,
    update,
)

T0 = datetime(2026, 1, 1, tzinfo=timezone.utc)


def _advance(t: datetime, **kwargs) -> datetime:
    return t + timedelta(**kwargs)


def test_initial_state_is_uninformative():
    state = initial_state()
    assert mastery(state) == 0.5
    assert confidence(state) == 0.0
    assert state.evidence_count == 0


def test_repeated_correct_answers_converge_mastery_to_one_with_rising_confidence():
    state = initial_state()
    t = T0
    prev_mastery = mastery(state)
    prev_confidence = confidence(state)
    for _ in range(30):
        t = _advance(t, hours=1)
        state = update(state, correct=True, difficulty=0.7, now=t)
        new_mastery = mastery(state)
        new_confidence = confidence(state)
        # Monotonic under sustained correct answers with negligible decay
        # between them (1 hour at decay_rate=0.15/day is ~0.6% pull).
        assert new_mastery >= prev_mastery - 1e-9
        assert new_confidence >= prev_confidence - 1e-9
        prev_mastery, prev_confidence = new_mastery, new_confidence

    assert mastery(state) > 0.95
    assert confidence(state) > 0.9


def test_repeated_incorrect_answers_converge_mastery_to_zero():
    state = initial_state()
    t = T0
    for _ in range(30):
        t = _advance(t, hours=1)
        state = update(state, correct=False, difficulty=0.3, now=t)

    assert mastery(state) < 0.05
    assert confidence(state) > 0.9


def test_elapsed_time_with_no_evidence_decays_mastery_and_confidence_toward_prior():
    state = initial_state()
    t = T0
    for _ in range(20):
        t = _advance(t, hours=1)
        state = update(state, correct=True, difficulty=0.8, now=t)

    mastery_before = mastery(state)
    confidence_before = confidence(state)
    assert mastery_before > 0.9
    assert confidence_before > 0.8

    # No further evidence for a long time.
    decayed = decay(state, now=_advance(t, days=60))

    assert mastery(decayed) < mastery_before
    assert abs(mastery(decayed) - 0.5) < abs(mastery_before - 0.5)
    assert confidence(decayed) < confidence_before
    assert confidence(decayed) < 0.05  # effectively back to "unknown"


def test_decay_is_a_noop_without_prior_evidence():
    state = initial_state()
    decayed = decay(state, now=_advance(T0, days=365))
    assert decayed == state


def test_decay_is_a_noop_going_backwards_or_staying_put():
    state = update(initial_state(), correct=True, difficulty=0.5, now=T0)
    assert decay(state, now=T0) == state
    assert decay(state, now=_advance(T0, hours=-1)) == state


def test_alternating_correct_and_incorrect_holds_mastery_near_half():
    state = initial_state()
    t = T0
    for i in range(20):
        t = _advance(t, hours=1)
        state = update(state, correct=(i % 2 == 0), difficulty=0.5, now=t)

    assert abs(mastery(state) - 0.5) < 0.05


def test_alternating_evidence_yields_lower_confidence_than_consistent_evidence():
    """Same amount of evidence, but alternating outcomes should leave the
    learner's mastery estimate less useful (closer to 0.5, "could be
    anything") than a consistent run: confidence is lower for the same N.
    """
    t = T0
    alternating = initial_state()
    consistent = initial_state()
    for i in range(20):
        t = _advance(t, hours=1)
        alternating = update(alternating, correct=(i % 2 == 0), difficulty=0.5, now=t)
        consistent = update(consistent, correct=True, difficulty=0.5, now=t)

    assert confidence(alternating) < confidence(consistent)
    # Not fully certain either way — meaningfully bounded away from 1.
    assert confidence(alternating) < 0.97


def test_harder_correct_answers_move_mastery_more_than_easier_ones():
    t = T0
    easy_state = update(initial_state(), correct=True, difficulty=0.1, now=t)
    hard_state = update(initial_state(), correct=True, difficulty=0.9, now=t)
    assert mastery(hard_state) > mastery(easy_state)


def test_easier_incorrect_answers_hurt_mastery_more_than_harder_ones():
    t = T0
    easy_wrong = update(initial_state(), correct=False, difficulty=0.1, now=t)
    hard_wrong = update(initial_state(), correct=False, difficulty=0.9, now=t)
    assert mastery(easy_wrong) < mastery(hard_wrong)


def test_velocity_reflects_the_last_updates_mastery_delta():
    t = T0
    state = initial_state()
    state = update(state, correct=True, difficulty=0.5, now=t)
    first_velocity = state.velocity
    assert first_velocity > 0

    t = _advance(t, hours=1)
    state = update(state, correct=False, difficulty=0.5, now=t)
    assert state.velocity < 0
    assert state.velocity != first_velocity


def test_evidence_count_increments_once_per_update_not_per_decay():
    t = T0
    state = update(initial_state(), correct=True, difficulty=0.5, now=t)
    assert state.evidence_count == 1

    decayed = decay(state, now=_advance(t, days=10))
    assert decayed.evidence_count == 1

    updated_again = update(decayed, correct=True, difficulty=0.5, now=_advance(t, days=10))
    assert updated_again.evidence_count == 2
