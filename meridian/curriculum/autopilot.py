"""
Learning Autopilot: the signature feature composing Phases 2-4.

diagnose -> plan -> teach -> assess -> update -> replan, as one traceable
loop over the real mastery kernel (meridian.learner.mastery), concept DAG
(meridian.knowledge.graph/diagnosis), and curriculum planner
(meridian.curriculum.planner) — no mocks standing in for the actual
model. "Teach" is intentionally out of scope here: producing tutoring
content is the inherited DeepTutor engine's job (agents/guide,
agents/question), reached through meridian/bridge/ in a real deployment,
not something this module fabricates. What this module demonstrates is
the *decision* loop around teaching, which is Meridian's original
contribution.

Every step here is a pure function over explicit state — no hidden
mutation, no LLM call — so a full autopilot run is exactly as testable as
its parts (see tests/curriculum/test_autopilot.py, which runs a full
loop and asserts the plan actually changes after a scripted assessment
failure).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from meridian.curriculum.planner import Plan
from meridian.curriculum.planner import plan as build_plan
from meridian.knowledge.diagnosis import DiagnosisResult, diagnose
from meridian.knowledge.graph import ConceptGraph
from meridian.learner.mastery import MasteryState, mastery, update


@dataclass
class LearnerState:
    """In-memory learner mastery state for one autopilot run.

    A thin, dict-backed stand-in for meridian.learner.service's DB-backed
    LearnerConceptState rows — the autopilot loop is the same either way,
    since both expose the same (state, event) -> state kernel via
    meridian.learner.mastery. This lets the full loop run and be tested
    without a database.
    """

    states: dict[str, MasteryState] = field(default_factory=dict)

    def mastery_of(self, concept_id: str) -> float:
        return mastery(self.states.get(concept_id, MasteryState()))

    def record(self, concept_id: str, *, correct: bool, difficulty: float, now: datetime) -> None:
        current = self.states.get(concept_id, MasteryState())
        self.states[concept_id] = update(current, correct=correct, difficulty=difficulty, now=now)


@dataclass(frozen=True)
class AutopilotStep:
    """One iteration of the loop: what was diagnosed and planned at that point."""

    diagnosis: DiagnosisResult | None
    plan: Plan


def diagnose_and_plan(
    target_concept_id: str,
    graph: ConceptGraph,
    learner: LearnerState,
    *,
    available_hours: float,
    threshold: float = 0.7,
) -> AutopilotStep:
    """One pass of diagnose -> plan against the learner's current state.

    This is the whole "decide what to do next" step. Calling it again
    after learner.record() has been called *is* replanning — there is no
    separate plan-invalidation mechanism (see meridian.curriculum.planner's
    module docstring for why).
    """
    diagnosis = diagnose(target_concept_id, graph, learner.mastery_of, threshold=threshold)
    schedule = build_plan(
        [target_concept_id],
        graph,
        learner.mastery_of,
        available_hours=available_hours,
    )
    return AutopilotStep(diagnosis=diagnosis, plan=schedule)
