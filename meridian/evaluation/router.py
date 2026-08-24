"""
Model routing: pick the best model for a task from its metadata, not by
hardcoding a model name into every capability.

deeptutor.services.llm.factory.complete/stream (the chokepoint every agent
already goes through via BaseAgent — no agent bypasses it) already accepts
per-call model/api_key/base_url/binding overrides. select_model() is the
decision this router's insertion point needs: given a task and a policy,
which model+provider should this specific call use. Wiring it into
factory.complete as the *default* model resolution (instead of always
falling back to config.model) is the next integration step once a real,
measured benchmark (meridian.evaluation.harness) justifies a routing
table — see README's metric-honesty rule: no routing table is published
here from unmeasured guesses.
"""

from __future__ import annotations

from dataclasses import dataclass

from meridian.evaluation.model_metadata import ModelMetadata, get_model_metadata


@dataclass(frozen=True)
class RoutingCandidate:
    model: str
    provider: str


@dataclass(frozen=True)
class RoutingPolicy:
    """Constraints and preferences for one routing decision."""

    min_context_window: int = 0
    require_vision: bool = False
    require_tools: bool = False
    # Quality weight vs. cost weight when ranking survivors of the hard
    # constraints above, both in [0, 1] and expected to sum to 1.0.
    # quality_of(candidate) is caller-supplied (e.g. from a benchmark's
    # mean_score for this task_type) since the router has no opinion on
    # quality without one.
    cost_weight: float = 0.5
    quality_weight: float = 0.5


@dataclass(frozen=True)
class RoutingDecision:
    chosen: RoutingCandidate
    metadata: ModelMetadata
    excluded: list[tuple[RoutingCandidate, str]]  # (candidate, reason) for every one rejected


def _passes_constraints(metadata: ModelMetadata, policy: RoutingPolicy) -> str | None:
    """Return a rejection reason, or None if the model satisfies the policy."""
    if metadata.context_window < policy.min_context_window:
        return (
            f"context_window {metadata.context_window} < required {policy.min_context_window}"
        )
    if policy.require_vision and not metadata.supports_vision:
        return "does not support vision"
    if policy.require_tools and not metadata.supports_tools:
        return "does not support tool use"
    return None


def select_model(
    candidates: list[RoutingCandidate],
    policy: RoutingPolicy,
    *,
    quality_of: dict[str, float] | None = None,
) -> RoutingDecision:
    """Pick the candidate that best satisfies ``policy``.

    Raises ValueError if every candidate fails a hard constraint — a
    routing decision that silently falls through to some arbitrary default
    would defeat the point of routing.

    ``quality_of`` maps model name -> quality score in [0, 1] (e.g. a mean
    benchmark score for this task_type). Models with no entry are treated
    as quality 0.5 (neutral) rather than excluded — most callers won't have
    benchmarked every candidate model for every task type yet.
    """
    quality_of = quality_of or {}
    excluded: list[tuple[RoutingCandidate, str]] = []
    survivors: list[tuple[RoutingCandidate, ModelMetadata]] = []

    for candidate in candidates:
        metadata = get_model_metadata(candidate.model)
        reason = _passes_constraints(metadata, policy)
        if reason is not None:
            excluded.append((candidate, reason))
        else:
            survivors.append((candidate, metadata))

    if not survivors:
        raise ValueError(
            "No candidate satisfies the routing policy: "
            + "; ".join(f"{c.model}: {reason}" for c, reason in excluded)
        )

    def _score(pair: tuple[RoutingCandidate, ModelMetadata]) -> float:
        candidate, metadata = pair
        quality = quality_of.get(candidate.model, 0.5)
        # Cost score: cheaper is better, normalized against the most
        # expensive survivor so cost_weight is meaningful regardless of
        # the absolute price scale of the candidates under consideration.
        max_cost = max(m.input_price_per_1k + m.output_price_per_1k for _c, m in survivors) or 1.0
        this_cost = metadata.input_price_per_1k + metadata.output_price_per_1k
        cost_score = 1.0 - (this_cost / max_cost)
        return policy.quality_weight * quality + policy.cost_weight * cost_score

    best_candidate, best_metadata = max(survivors, key=_score)
    return RoutingDecision(chosen=best_candidate, metadata=best_metadata, excluded=excluded)
