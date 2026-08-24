"""
Prerequisite-gap diagnosis: the headline demo behavior.

Given a question about some concept, don't just grade the answer — walk
the prerequisite DAG upstream and find the weakest link. That's the
concept actually worth teaching next, which is often not the concept the
question was nominally about:

    "Why does gradient descent overshoot?"
      Calculus 0.91 -> Derivatives 0.83 -> Optimization 0.62 -> Learning rate 0.41
      -> teach the prerequisite, not the question asked

Pure function over a ConceptGraph and a mastery lookup — no LLM, no I/O.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from meridian.knowledge.graph import ConceptGraph

MasteryLookup = Callable[[str], float]


@dataclass(frozen=True)
class DiagnosisResult:
    target_concept_id: str
    weak_concept_id: str
    weak_mastery: float
    chain: list[str]  # ordered root-cause -> target, for display
    chain_mastery: list[float]

    @property
    def is_target_itself(self) -> bool:
        """True if the target concept has no weaker upstream prerequisite.

        Not necessarily "the target is mastered" — just that nothing
        further upstream is a better place to intervene.
        """
        return self.weak_concept_id == self.target_concept_id


def diagnose(
    target_concept_id: str,
    graph: ConceptGraph,
    mastery_of: MasteryLookup,
    *,
    threshold: float = 0.7,
) -> DiagnosisResult | None:
    """Find the weakest prerequisite (transitively) behind ``target_concept_id``.

    Considers the target concept itself plus every upstream prerequisite.
    Returns the one with the lowest mastery score if it's below
    ``threshold``; returns ``None`` if the target and everything behind it
    already clears the threshold (nothing to diagnose — the learner is
    fine on this whole chain).

    ``mastery_of`` is a plain callable rather than a dict so callers can
    back it with a live per-request cache, a DB lookup, or (as in tests) a
    fixed mapping — diagnosis itself doesn't care about the source.
    """
    candidates = graph.prerequisites_of(target_concept_id, transitive=True)
    candidates.add(target_concept_id)

    scored = [(cid, mastery_of(cid)) for cid in candidates]
    weak_concept_id, weak_mastery = min(scored, key=lambda pair: pair[1])

    if weak_mastery >= threshold:
        return None

    # An example root-cause -> target path for display. In a graph with a
    # single linear prerequisite chain (e.g. the seeded calculus domain),
    # this always contains the diagnosed weak concept. In a general DAG
    # with multiple prerequisite branches, the weak concept found above may
    # sit on a different branch than this particular example path — if so,
    # prepend it so the diagnosis is never silently left off the display.
    chain = graph.path_to_root(target_concept_id)
    if weak_concept_id not in chain:
        chain = [weak_concept_id, *chain]

    return DiagnosisResult(
        target_concept_id=target_concept_id,
        weak_concept_id=weak_concept_id,
        weak_mastery=weak_mastery,
        chain=chain,
        chain_mastery=[mastery_of(cid) for cid in chain],
    )


def format_diagnosis(result: DiagnosisResult, names: dict[str, str] | None = None) -> str:
    """Render a DiagnosisResult as the arrow-chain display from the demo."""

    def label(cid: str) -> str:
        return (names or {}).get(cid, cid)

    parts = [
        f"{label(cid)} {score:.2f}" for cid, score in zip(result.chain, result.chain_mastery)
    ]
    line = " → ".join(parts)
    return f"{line} ← teach the prerequisite, not the question asked"
