from __future__ import annotations

import pytest

from meridian.knowledge.graph import ConceptGraph, CycleError


def _calculus_chain() -> ConceptGraph:
    graph = ConceptGraph()
    graph.add_edge("calculus", "derivatives")
    graph.add_edge("derivatives", "optimization")
    graph.add_edge("optimization", "learning_rate")
    return graph


def test_direct_and_transitive_prerequisites():
    graph = _calculus_chain()
    assert graph.direct_prerequisites_of("learning_rate") == {"optimization"}
    assert graph.prerequisites_of("learning_rate", transitive=True) == {
        "calculus",
        "derivatives",
        "optimization",
    }
    assert graph.prerequisites_of("calculus", transitive=True) == set()


def test_dependents_of_is_the_inverse_relation():
    graph = _calculus_chain()
    assert graph.dependents_of("calculus") == {"derivatives"}
    assert graph.dependents_of("calculus", transitive=True) == {
        "derivatives",
        "optimization",
        "learning_rate",
    }


def test_adding_an_edge_that_would_cycle_is_rejected():
    graph = _calculus_chain()
    with pytest.raises(CycleError):
        graph.add_edge("learning_rate", "calculus")
    with pytest.raises(CycleError):
        graph.add_edge("optimization", "optimization")


def test_related_edges_do_not_participate_in_cycle_detection_or_ordering():
    graph = _calculus_chain()
    # A "related" edge in the "wrong" direction relative to the prerequisite
    # chain must not be rejected, and must not affect prerequisites_of().
    graph.add_edge("learning_rate", "calculus", relation="related")
    assert graph.prerequisites_of("learning_rate", transitive=True) == {
        "calculus",
        "derivatives",
        "optimization",
    }


def test_topological_order_respects_prerequisite_edges():
    graph = _calculus_chain()
    order = graph.topological_order()
    for concept in ("calculus", "derivatives", "optimization", "learning_rate"):
        assert concept in order
    assert order.index("calculus") < order.index("derivatives")
    assert order.index("derivatives") < order.index("optimization")
    assert order.index("optimization") < order.index("learning_rate")


def test_topological_order_is_deterministic_among_ties():
    graph = ConceptGraph()
    graph.add_edge("a", "c")
    graph.add_edge("b", "c")
    # a and b are both roots with no ordering constraint between them;
    # ties broken lexicographically should always yield the same order.
    assert graph.topological_order() == ["a", "b", "c"]
    assert graph.topological_order() == graph.topological_order()


def test_path_to_root_follows_the_deepest_chain():
    graph = _calculus_chain()
    assert graph.path_to_root("learning_rate") == [
        "calculus",
        "derivatives",
        "optimization",
        "learning_rate",
    ]
    assert graph.path_to_root("calculus") == ["calculus"]


def test_diamond_shaped_graph_prerequisites_and_topo_order():
    graph = ConceptGraph()
    graph.add_edge("root", "left")
    graph.add_edge("root", "right")
    graph.add_edge("left", "join")
    graph.add_edge("right", "join")

    assert graph.prerequisites_of("join", transitive=True) == {"root", "left", "right"}
    order = graph.topological_order()
    assert order.index("root") < order.index("left")
    assert order.index("root") < order.index("right")
    assert order.index("left") < order.index("join")
    assert order.index("right") < order.index("join")
