"""
Beta-Bernoulli mastery kernel.

The learner digital twin's core model: each (learner, concept) pair is a
Beta(alpha, beta) posterior over "probability this learner answers a
question on this concept correctly." Chosen over a black-box heuristic
because it is testable, explainable, and gives two quantities for free
from one model:

    mastery    = alpha / (alpha + beta)                 — the posterior mean
    confidence = 1 - variance(state) / variance(prior)   — how peaked the
                                                            posterior is,
                                                            relative to the
                                                            least-informative
                                                            (prior) state

Every function here is a pure `(state, ...) -> state` transform over the
``MasteryState`` dataclass — no I/O, no LLM calls, no database. This is
what makes it unit-testable (see tests/learner/test_mastery.py) and is
deliberately kept separate from meridian/persistence/models/learner.py,
which only stores this state's fields; ``meridian/learner/service.py`` is
the adapter between the two.

Forgetting: ``decay()`` pulls both parameters back toward the prior as a
function of elapsed time, which is mathematically an Ebbinghaus-shaped
curve falling out of the same Beta-Bernoulli math — no separate model
needed. This generalizes the SM-2 spaced-repetition implementation already
in deeptutor.api.routers.learning (`ease_factor` per flashcard): here,
`decay_rate` plays the same role per concept, continuously rather than as
discrete review intervals.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timezone
import math

# Uninformative (Jeffreys-adjacent, symmetric) prior: "we have no idea,
# 50/50." Both mastery() and confidence() are defined relative to this.
PRIOR_ALPHA = 1.0
PRIOR_BETA = 1.0

# Per-day exponential decay constant. At this rate, evidence "half-forgets"
# (moves halfway back to the prior) in ln(2)/0.15 ≈ 4.6 days without further
# practice — a deliberately short horizon so the demo/tests show visible
# decay over a few simulated days rather than requiring weeks.
DEFAULT_DECAY_RATE = 0.15

# Beta(1, 1) variance = (1*1) / (2^2 * 3) = 1/12. This is the maximum
# variance any Beta(a>=1, b>=1) posterior can have — the least-informative
# point, i.e. the prior itself. confidence() normalizes against it so that
# a brand-new concept (no evidence) is exactly confidence=0.
_PRIOR_VARIANCE = (PRIOR_ALPHA * PRIOR_BETA) / (
    (PRIOR_ALPHA + PRIOR_BETA) ** 2 * (PRIOR_ALPHA + PRIOR_BETA + 1)
)


def _clamp(value: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, value))


@dataclass(frozen=True)
class MasteryState:
    """The persisted fields of LearnerConceptState, as a pure-Python value."""

    alpha: float = PRIOR_ALPHA
    beta: float = PRIOR_BETA
    decay_rate: float = DEFAULT_DECAY_RATE
    last_seen_at: datetime | None = None
    evidence_count: int = 0
    velocity: float = 0.0


def initial_state(decay_rate: float = DEFAULT_DECAY_RATE) -> MasteryState:
    """A fresh, no-evidence state for a (learner, concept) pair."""
    return MasteryState(alpha=PRIOR_ALPHA, beta=PRIOR_BETA, decay_rate=decay_rate)


def mastery(state: MasteryState) -> float:
    """Posterior mean: P(this learner answers correctly on this concept)."""
    return state.alpha / (state.alpha + state.beta)


def variance(state: MasteryState) -> float:
    """Posterior variance of the Beta(alpha, beta) distribution."""
    a, b = state.alpha, state.beta
    return (a * b) / ((a + b) ** 2 * (a + b + 1))


def confidence(state: MasteryState) -> float:
    """How peaked the posterior is, in [0, 1]. 0 at the prior, ->1 as evidence grows."""
    return _clamp(1.0 - variance(state) / _PRIOR_VARIANCE)


def decay(state: MasteryState, now: datetime | None = None) -> MasteryState:
    """Project ``state`` forward to ``now``, pulling (alpha, beta) toward the prior.

    A no-op if there's no prior evidence (nothing to forget) or if ``now``
    is not after ``last_seen_at``. Idempotent: decaying an already-decayed
    state to the same ``now`` again is a no-op, since it only reads
    ``last_seen_at`` (unchanged by decay) to compute elapsed time — decay is
    a read-time projection, not an event that advances the log.
    """
    if state.last_seen_at is None or state.evidence_count == 0:
        return state
    now = now or datetime.now(timezone.utc)
    elapsed_days = (now - state.last_seen_at).total_seconds() / 86400.0
    if elapsed_days <= 0:
        return state
    factor = math.exp(-state.decay_rate * elapsed_days)
    return replace(
        state,
        alpha=PRIOR_ALPHA + (state.alpha - PRIOR_ALPHA) * factor,
        beta=PRIOR_BETA + (state.beta - PRIOR_BETA) * factor,
    )


def update(
    state: MasteryState,
    *,
    correct: bool,
    difficulty: float = 0.5,
    now: datetime | None = None,
) -> MasteryState:
    """Fold one graded interaction into ``state``.

    ``difficulty`` in [0, 1] weights the evidence: a correct answer on a
    harder item is stronger evidence of mastery (larger alpha increment);
    an incorrect answer on an easier item is stronger evidence against it
    (larger beta increment). Weight is bounded to [1, 2] either way, so a
    single interaction can never dominate the posterior outright.
    """
    now = now or datetime.now(timezone.utc)
    difficulty = _clamp(difficulty)
    decayed = decay(state, now)
    prior_mastery = mastery(decayed)

    weight = 1.0 + (difficulty if correct else (1.0 - difficulty))
    new_alpha = decayed.alpha + (weight if correct else 0.0)
    new_beta = decayed.beta + (0.0 if correct else weight)

    updated = replace(
        decayed,
        alpha=new_alpha,
        beta=new_beta,
        last_seen_at=now,
        evidence_count=decayed.evidence_count + 1,
    )
    return replace(updated, velocity=mastery(updated) - prior_mastery)
