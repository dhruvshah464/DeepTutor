"""
Prerequisite concept graph.

A minimal, in-memory DAG over concept ids, built from
meridian.persistence.models.learner.Concept/ConceptEdge rows (or, for
tests and the demo, constructed directly — see tests/knowledge/test_diagnosis.py
and meridian/knowledge/seed_calculus.py). Deliberately not a general graph
library dependency: the operations diagnosis.py and curriculum/planner.py
need are exactly "prerequisites of X, transitively" and "topological
order," both a few lines over a plain adjacency dict.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Edge:
    src: str  # prerequisite concept id
    dst: str  # dependent concept id
    relation: str = "prerequisite"
    weight: float = 1.0


class CycleError(ValueError):
    """Raised when an edge would introduce a cycle into the prerequisite DAG."""


@dataclass
class ConceptGraph:
    """A directed acyclic graph of concept_id -> concept_id prerequisite edges."""

    concept_ids: set[str] = field(default_factory=set)
    _edges: list[Edge] = field(default_factory=list)
    _prereqs_of: dict[str, set[str]] = field(default_factory=dict)  # dst -> {src, ...}
    _dependents_of: dict[str, set[str]] = field(default_factory=dict)  # src -> {dst, ...}

    def add_concept(self, concept_id: str) -> None:
        self.concept_ids.add(concept_id)
        self._prereqs_of.setdefault(concept_id, set())
        self._dependents_of.setdefault(concept_id, set())

    def add_edge(self, src: str, dst: str, *, relation: str = "prerequisite", weight: float = 1.0) -> None:
        """Add a "src is a prerequisite of dst" edge.

        Only ``relation="prerequisite"`` edges participate in cycle
        detection and traversal; ``"related"`` edges are stored but not
        used for diagnosis/planning (they don't imply an ordering).
        """
        self.add_concept(src)
        self.add_concept(dst)
        if relation == "prerequisite" and self._would_cycle(src, dst):
            raise CycleError(f"Adding {src} -> {dst} would create a prerequisite cycle")
        self._edges.append(Edge(src=src, dst=dst, relation=relation, weight=weight))
        if relation == "prerequisite":
            self._prereqs_of[dst].add(src)
            self._dependents_of[src].add(dst)

    def _would_cycle(self, src: str, dst: str) -> bool:
        # Edges point prerequisite -> dependent. Adding src -> dst creates a
        # cycle exactly when dst is already an (transitive) prerequisite of
        # src — i.e. there's already a path src's-ancestor-chain reaching
        # dst, so this new edge would close a loop back to it.
        if src == dst:
            return True
        return dst in self.prerequisites_of(src, transitive=True)

    def direct_prerequisites_of(self, concept_id: str) -> set[str]:
        return set(self._prereqs_of.get(concept_id, set()))

    def prerequisites_of(self, concept_id: str, *, transitive: bool = False) -> set[str]:
        """All prerequisite concept ids for ``concept_id``.

        With ``transitive=False``, only direct prerequisites. With
        ``transitive=True`` (the default use in diagnosis), the full
        upstream closure — prerequisites of prerequisites, and so on.
        """
        if not transitive:
            return self.direct_prerequisites_of(concept_id)

        seen: set[str] = set()
        frontier = list(self._prereqs_of.get(concept_id, set()))
        while frontier:
            current = frontier.pop()
            if current in seen:
                continue
            seen.add(current)
            frontier.extend(self._prereqs_of.get(current, set()) - seen)
        return seen

    def dependents_of(self, concept_id: str, *, transitive: bool = False) -> set[str]:
        """The inverse of prerequisites_of: concepts that depend on this one."""
        if not transitive:
            return set(self._dependents_of.get(concept_id, set()))
        seen: set[str] = set()
        frontier = list(self._dependents_of.get(concept_id, set()))
        while frontier:
            current = frontier.pop()
            if current in seen:
                continue
            seen.add(current)
            frontier.extend(self._dependents_of.get(current, set()) - seen)
        return seen

    def topological_order(self, concept_ids: set[str] | None = None) -> list[str]:
        """Kahn's algorithm, restricted to ``concept_ids`` if given.

        Deterministic among ties: at each step, the eligible node with the
        lexicographically smallest id is chosen, so the same graph always
        yields the same order (useful for reproducible tests/demos).
        """
        universe = concept_ids if concept_ids is not None else self.concept_ids
        in_degree = {
            cid: len(self._prereqs_of.get(cid, set()) & universe) for cid in universe
        }
        ready = sorted(cid for cid, deg in in_degree.items() if deg == 0)
        order: list[str] = []
        while ready:
            ready.sort()
            current = ready.pop(0)
            order.append(current)
            for dependent in sorted(self._dependents_of.get(current, set()) & universe):
                in_degree[dependent] -= 1
                if in_degree[dependent] == 0:
                    ready.append(dependent)
        if len(order) != len(universe):
            raise CycleError("Graph contains a cycle within the given concept_ids")
        return order

    def path_to_root(self, concept_id: str) -> list[str]:
        """One example chain from a "most fundamental" ancestor down to ``concept_id``.

        Walks the deepest direct-prerequisite chain at each step (ties
        broken lexicographically) purely for a legible demo/diagnosis
        display — not a claim that it's the unique or "correct" path
        through a DAG that may have many.
        """
        chain = [concept_id]
        current = concept_id
        while True:
            prereqs = self.direct_prerequisites_of(current)
            if not prereqs:
                break
            current = min(prereqs)
            chain.append(current)
        return list(reversed(chain))
