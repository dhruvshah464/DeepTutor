from __future__ import annotations

from meridian.curriculum.planner import plan
from meridian.knowledge.graph import ConceptGraph


def _calculus_chain() -> ConceptGraph:
    graph = ConceptGraph()
    graph.add_edge("calculus", "derivatives")
    graph.add_edge("derivatives", "optimization")
    graph.add_edge("optimization", "learning_rate")
    return graph


def test_plan_respects_topological_order():
    graph = _calculus_chain()
    mastery = {"calculus": 0.2, "derivatives": 0.2, "optimization": 0.2, "learning_rate": 0.2}

    result = plan(["learning_rate"], graph, mastery.get, available_hours=100)

    order = result.concept_order
    assert order.index("calculus") < order.index("derivatives")
    assert order.index("derivatives") < order.index("optimization")
    assert order.index("optimization") < order.index("learning_rate")


def test_plan_includes_transitive_prerequisites_of_the_target():
    graph = _calculus_chain()
    mastery = {"calculus": 0.9, "derivatives": 0.9, "optimization": 0.9, "learning_rate": 0.2}

    result = plan(["learning_rate"], graph, mastery.get, available_hours=100)

    assert set(result.concept_order) == {"calculus", "derivatives", "optimization", "learning_rate"}


def test_plan_prioritizes_weaker_concepts_among_topologically_tied_options():
    graph = ConceptGraph()
    graph.add_edge("root", "left")
    graph.add_edge("root", "right")
    mastery = {"root": 0.9, "left": 0.9, "right": 0.1}  # left and right are both ready at once

    result = plan(["left", "right"], graph, mastery.get, available_hours=100)

    order = result.concept_order
    assert order.index("root") < order.index("left")
    assert order.index("root") < order.index("right")
    # Among the tied-ready pair, the weaker one (right, mastery 0.1) goes first.
    assert order.index("right") < order.index("left")


def test_plan_respects_the_time_budget_deferring_what_does_not_fit():
    graph = _calculus_chain()
    mastery = {"calculus": 0.1, "derivatives": 0.1, "optimization": 0.1, "learning_rate": 0.1}

    # Each "new" concept costs 1 full hour by default; only 2 fit.
    result = plan(["learning_rate"], graph, mastery.get, available_hours=2.0, hours_per_concept=1.0)

    assert len(result.scheduled) == 2
    assert len(result.deferred) == 2
    assert result.total_hours <= 2.0
    # The scheduled ones must still be a valid topological prefix.
    assert result.concept_order == ["calculus", "derivatives"]


def test_already_mastered_concepts_get_a_light_review_not_a_full_study_block():
    graph = ConceptGraph()
    graph.add_concept("known")
    mastery = {"known": 0.95}

    result = plan(["known"], graph, mastery.get, available_hours=100, hours_per_concept=2.0)

    assert result.scheduled[0].reason == "review"
    assert result.scheduled[0].hours < 2.0


def test_decay_urgency_breaks_ties_toward_the_more_at_risk_concept():
    graph = ConceptGraph()
    graph.add_edge("root", "a")
    graph.add_edge("root", "b")
    mastery = {"root": 0.9, "a": 0.6, "b": 0.6}  # identical mastery
    urgency = {"root": 0.0, "a": 0.0, "b": 0.9}.get  # b is close to being forgotten

    result = plan(["a", "b"], graph, mastery.get, available_hours=100, decay_urgency_of=urgency)

    order = result.concept_order
    assert order.index("b") < order.index("a")


def test_replanning_after_a_failed_assessment_reprioritizes_without_extra_state():
    """'Replanning' is just calling plan() again with updated mastery —
    there's no separate plan-invalidation mechanism to test beyond that.
    """
    graph = _calculus_chain()
    mastery = {"calculus": 0.9, "derivatives": 0.9, "optimization": 0.9, "learning_rate": 0.9}

    first = plan(["learning_rate"], graph, mastery.get, available_hours=100)
    # Everything was already strong, so this whole chain is light review.
    assert all(item.reason == "review" for item in first.scheduled)

    # A failed assessment tanks mastery on "optimization".
    mastery["optimization"] = 0.1
    second = plan(["learning_rate"], graph, mastery.get, available_hours=100)

    optimization_item = next(i for i in second.scheduled if i.concept_id == "optimization")
    assert optimization_item.reason == "new"
    assert optimization_item.hours > first.scheduled[
        next(i for i, item in enumerate(first.scheduled) if item.concept_id == "optimization")
    ].hours
