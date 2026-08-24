from __future__ import annotations

from datetime import datetime, timedelta, timezone

from meridian.curriculum.autopilot import LearnerState, diagnose_and_plan
from meridian.knowledge.graph import ConceptGraph

T0 = datetime(2026, 1, 1, tzinfo=timezone.utc)


def _calculus_chain() -> ConceptGraph:
    graph = ConceptGraph()
    graph.add_edge("calculus", "derivatives")
    graph.add_edge("derivatives", "optimization")
    graph.add_edge("optimization", "learning_rate")
    return graph


def test_full_loop_diagnoses_teaches_assesses_and_replans():
    """The closed loop the whole project is about: interaction -> learner
    state -> diagnosis -> strategy -> response -> assessment -> state
    update -> replan. Every step here is the real kernel, not a stub.
    """
    graph = _calculus_chain()
    learner = LearnerState()
    t = T0

    # Learner starts strong on everything except the deepest prerequisite.
    for concept, correct, difficulty in [
        ("calculus", True, 0.7),
        ("calculus", True, 0.8),
        ("derivatives", True, 0.7),
        ("derivatives", True, 0.7),
        ("optimization", True, 0.6),
        ("optimization", True, 0.6),
        ("learning_rate", False, 0.4),
        ("learning_rate", False, 0.3),
    ]:
        t += timedelta(hours=1)
        learner.record(concept, correct=correct, difficulty=difficulty, now=t)

    first = diagnose_and_plan("learning_rate", graph, learner, available_hours=10)

    assert first.diagnosis is not None
    assert first.diagnosis.weak_concept_id == "learning_rate"
    assert first.diagnosis.is_target_itself is True
    # The plan should schedule the weak concept as new/high-priority study,
    # not a light review.
    learning_rate_item = next(
        item for item in first.plan.scheduled if item.concept_id == "learning_rate"
    )
    assert learning_rate_item.reason == "new"

    # "Teach" happens (out of scope for this module — the inherited engine's
    # job), then an assessment comes back: the learner gets it right this time.
    for _ in range(6):
        t += timedelta(hours=1)
        learner.record("learning_rate", correct=True, difficulty=0.6, now=t)

    # Replanning is just calling diagnose_and_plan() again with the updated
    # learner state — no separate invalidation step.
    second = diagnose_and_plan("learning_rate", graph, learner, available_hours=10)

    assert second.diagnosis is None or second.diagnosis.weak_mastery > first.diagnosis.weak_mastery
    if second.plan.scheduled:
        maybe_item = next(
            (item for item in second.plan.scheduled if item.concept_id == "learning_rate"), None
        )
        if maybe_item is not None:
            assert maybe_item.hours <= learning_rate_item.hours


def test_diagnosis_finds_the_true_upstream_gap_even_when_the_target_looks_fine():
    graph = _calculus_chain()
    learner = LearnerState()
    t = T0

    # The target concept itself looks great; a deep prerequisite is broken.
    for concept, correct, difficulty in [
        ("calculus", True, 0.9),
        ("derivatives", False, 0.2),
        ("derivatives", False, 0.2),
        ("optimization", True, 0.8),
        ("learning_rate", True, 0.9),
    ]:
        t += timedelta(hours=1)
        learner.record(concept, correct=correct, difficulty=difficulty, now=t)

    step = diagnose_and_plan("learning_rate", graph, learner, available_hours=10)

    assert step.diagnosis is not None
    assert step.diagnosis.weak_concept_id == "derivatives"
    assert step.diagnosis.is_target_itself is False


def test_no_evidence_at_all_diagnoses_the_full_chain_as_unknown():
    graph = _calculus_chain()
    learner = LearnerState()  # no events recorded at all

    step = diagnose_and_plan("learning_rate", graph, learner, available_hours=10)

    # Every concept starts at the uninformative prior (mastery 0.5), which
    # is below the default 0.7 threshold — there's a "gap" everywhere, and
    # the plan should cover the whole prerequisite chain.
    assert step.diagnosis is not None
    assert set(step.plan.concept_order) == {
        "calculus",
        "derivatives",
        "optimization",
        "learning_rate",
    }
