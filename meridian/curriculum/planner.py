"""
Adaptive curriculum planner: constrained optimization, not prompt-and-hope.

Given target concepts, the learner's current mastery, an available-hours
budget, and the prerequisite DAG (meridian.knowledge.graph.ConceptGraph),
produce an ordered study schedule: a priority-weighted topological sort —
respecting prerequisite order strictly, but among concepts whose
prerequisites are already satisfied, always picking the one with the
biggest mastery deficit (and, optionally, the most urgent decay) first.

Continuous replanning is not a separate mechanism: plan() is a pure
function of its inputs, so "a failed assessment updates the learner state,
which invalidates and regenerates the plan" (ARCHITECTURE.md's closed
loop) is just calling plan() again with the updated mastery_of callable —
there is no separate stale-plan-invalidation state to manage.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

from meridian.knowledge.graph import ConceptGraph

MasteryLookup = Callable[[str], float]

# Default hours to budget for studying one concept from scratch. Deliberately
# a single constant rather than per-concept metadata the domain doesn't
# have yet (see ARCHITECTURE.md's note on prototyping concept tagging on
# one domain before generalizing) — callers can override via
# hours_per_concept for a richer estimate once that data exists.
DEFAULT_HOURS_PER_CONCEPT = 1.0

# A concept at/above this mastery is considered "already known" and gets
# a much smaller time allocation (light review) rather than a full study
# block.
MASTERY_KNOWN_THRESHOLD = 0.85
REVIEW_HOURS_FRACTION = 0.2


@dataclass(frozen=True)
class ScheduleItem:
    concept_id: str
    mastery: float
    priority: float
    hours: float
    reason: str  # "new" | "review" | "reinforce"


@dataclass(frozen=True)
class Plan:
    scheduled: list[ScheduleItem] = field(default_factory=list)
    deferred: list[ScheduleItem] = field(default_factory=list)  # didn't fit the time budget
    total_hours: float = 0.0

    @property
    def concept_order(self) -> list[str]:
        return [item.concept_id for item in self.scheduled]


def _priority(mastery: float, *, velocity: float = 0.0, decay_urgency: float = 0.0) -> float:
    """Higher = study sooner. Mastery deficit dominates; velocity and decay
    urgency are secondary tie-breaking signals.

    - Deficit (1 - mastery): the core driver — weakest concepts first.
    - velocity < 0 (mastery trending down, e.g. from recent wrong answers)
      raises priority slightly; velocity > 0 (already improving) lowers it.
    - decay_urgency in [0, 1] (how close a concept is to being forgotten,
      caller-supplied — e.g. from meridian.learner.mastery.decay) adds
      urgency independent of the current point-in-time mastery estimate.
    """
    deficit = 1.0 - mastery
    return deficit + 0.1 * max(0.0, -velocity) + 0.2 * decay_urgency


def _hours_for(mastery: float, hours_per_concept: float) -> tuple[float, str]:
    if mastery >= MASTERY_KNOWN_THRESHOLD:
        return hours_per_concept * REVIEW_HOURS_FRACTION, "review"
    if mastery >= 0.5:
        return hours_per_concept * 0.6, "reinforce"
    return hours_per_concept, "new"


def plan(
    target_concept_ids: list[str],
    graph: ConceptGraph,
    mastery_of: MasteryLookup,
    *,
    available_hours: float,
    velocity_of: MasteryLookup | None = None,
    decay_urgency_of: MasteryLookup | None = None,
    hours_per_concept: float = DEFAULT_HOURS_PER_CONCEPT,
) -> Plan:
    """Build a study schedule for reaching ``target_concept_ids``.

    Includes every transitive prerequisite of every target, not just the
    targets themselves — you can't study "gradient descent" without also
    scheduling "derivatives" if it isn't mastered yet.
    """
    velocity_of = velocity_of or (lambda _cid: 0.0)
    decay_urgency_of = decay_urgency_of or (lambda _cid: 0.0)

    universe: set[str] = set(target_concept_ids)
    for target in target_concept_ids:
        universe |= graph.prerequisites_of(target, transitive=True)

    remaining_prereqs = {
        cid: graph.direct_prerequisites_of(cid) & universe for cid in universe
    }
    ready = [cid for cid, prereqs in remaining_prereqs.items() if not prereqs]

    ordered: list[str] = []
    while ready:
        ready.sort(
            key=lambda cid: (
                -_priority(
                    mastery_of(cid),
                    velocity=velocity_of(cid),
                    decay_urgency=decay_urgency_of(cid),
                ),
                cid,  # deterministic tie-break
            )
        )
        current = ready.pop(0)
        ordered.append(current)
        for cid, prereqs in remaining_prereqs.items():
            if current in prereqs:
                prereqs.discard(current)
                if not prereqs and cid not in ordered and cid not in ready:
                    ready.append(cid)

    scheduled: list[ScheduleItem] = []
    deferred: list[ScheduleItem] = []
    hours_used = 0.0
    for cid in ordered:
        mastery = mastery_of(cid)
        hours, reason = _hours_for(mastery, hours_per_concept)
        item = ScheduleItem(
            concept_id=cid,
            mastery=mastery,
            priority=_priority(
                mastery, velocity=velocity_of(cid), decay_urgency=decay_urgency_of(cid)
            ),
            hours=hours,
            reason=reason,
        )
        if hours_used + hours <= available_hours:
            scheduled.append(item)
            hours_used += hours
        else:
            deferred.append(item)

    return Plan(scheduled=scheduled, deferred=deferred, total_hours=hours_used)
