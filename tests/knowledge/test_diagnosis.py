from __future__ import annotations

from datetime import datetime, timedelta, timezone

from meridian.knowledge.diagnosis import diagnose, format_diagnosis
from meridian.knowledge.graph import ConceptGraph
from meridian.learner.mastery import initial_state, mastery, update

T0 = datetime(2026, 1, 1, tzinfo=timezone.utc)


def _calculus_chain() -> ConceptGraph:
    graph = ConceptGraph()
    graph.add_edge("calculus", "derivatives")
    graph.add_edge("derivatives", "optimization")
    graph.add_edge("optimization", "learning_rate")
    return graph


def test_diagnose_names_the_weakest_prerequisite_not_the_question_asked():
    """The exact demo scenario from ARCHITECTURE.md's headline behavior."""
    graph = _calculus_chain()
    mastery_scores = {
        "calculus": 0.91,
        "derivatives": 0.83,
        "optimization": 0.62,
        "learning_rate": 0.41,
    }

    result = diagnose("learning_rate", graph, mastery_scores.get, threshold=0.7)

    assert result is not None
    assert result.weak_concept_id == "learning_rate"
    assert result.weak_mastery == 0.41
    assert result.chain == ["calculus", "derivatives", "optimization", "learning_rate"]
    assert result.chain_mastery == [0.91, 0.83, 0.62, 0.41]


def test_diagnose_looks_upstream_when_the_target_itself_is_fine():
    """The concept the question is nominally about can be solid while an
    upstream prerequisite is the actual gap — that's the whole point.
    """
    graph = _calculus_chain()
    mastery_scores = {
        "calculus": 0.95,
        "derivatives": 0.30,  # the real gap
        "optimization": 0.85,
        "learning_rate": 0.88,  # target itself: looks fine in isolation
    }

    result = diagnose("learning_rate", graph, mastery_scores.get, threshold=0.7)

    assert result is not None
    assert result.weak_concept_id == "derivatives"
    assert result.is_target_itself is False


def test_diagnose_returns_none_when_everything_clears_the_threshold():
    graph = _calculus_chain()
    mastery_scores = {
        "calculus": 0.95,
        "derivatives": 0.90,
        "optimization": 0.85,
        "learning_rate": 0.80,
    }

    assert diagnose("learning_rate", graph, mastery_scores.get, threshold=0.7) is None


def test_diagnose_on_a_concept_with_no_prerequisites_only_considers_itself():
    graph = _calculus_chain()
    result = diagnose("calculus", graph, {"calculus": 0.2}.get, threshold=0.7)
    assert result is not None
    assert result.weak_concept_id == "calculus"
    assert result.is_target_itself is True
    assert result.chain == ["calculus"]


def test_format_diagnosis_renders_the_arrow_chain():
    graph = _calculus_chain()
    mastery_scores = {
        "calculus": 0.91,
        "derivatives": 0.83,
        "optimization": 0.62,
        "learning_rate": 0.41,
    }
    result = diagnose("learning_rate", graph, mastery_scores.get, threshold=0.7)
    names = {
        "calculus": "Calculus",
        "derivatives": "Derivatives",
        "optimization": "Optimization",
        "learning_rate": "Learning rate",
    }

    rendered = format_diagnosis(result, names)

    assert rendered == (
        "Calculus 0.91 → Derivatives 0.83 → Optimization 0.62 → Learning rate 0.41 "
        "← teach the prerequisite, not the question asked"
    )


def test_diagnose_replaying_a_scripted_event_log_through_the_real_mastery_kernel():
    """End-to-end: no hand-fed mastery scores this time — a scripted log of
    graded interactions is replayed through the actual Beta-Bernoulli
    kernel (meridian.learner.mastery), and diagnosis is run against the
    resulting live states. This is the full loop the demo actually runs.
    """
    graph = _calculus_chain()
    states = {cid: initial_state() for cid in ("calculus", "derivatives", "optimization", "learning_rate")}

    # Scripted event log: strong on calculus/derivatives, shaky on
    # optimization, weak on learning_rate — mirrors the demo's numbers
    # without hand-picking mastery scores directly.
    script = [
        ("calculus", True, 0.8),
        ("calculus", True, 0.9),
        ("calculus", True, 0.7),
        ("derivatives", True, 0.7),
        ("derivatives", True, 0.8),
        ("derivatives", False, 0.3),
        ("optimization", True, 0.6),
        ("optimization", False, 0.5),
        ("optimization", False, 0.4),
        ("learning_rate", False, 0.3),
        ("learning_rate", False, 0.2),
        ("learning_rate", False, 0.4),
        ("learning_rate", True, 0.9),
    ]
    t = T0
    for concept_id, correct, difficulty in script:
        t += timedelta(hours=1)
        states[concept_id] = update(states[concept_id], correct=correct, difficulty=difficulty, now=t)

    mastery_of = {cid: mastery(state) for cid, state in states.items()}.get

    result = diagnose("learning_rate", graph, mastery_of, threshold=0.7)

    assert result is not None
    assert result.weak_concept_id == "learning_rate"
    assert mastery_of("learning_rate") < mastery_of("optimization")
    assert mastery_of("optimization") < mastery_of("derivatives")
    assert mastery_of("derivatives") < mastery_of("calculus")
