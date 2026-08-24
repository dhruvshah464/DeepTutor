from __future__ import annotations

import pytest

from meridian.evaluation.router import (
    RoutingCandidate,
    RoutingPolicy,
    select_model,
)


def test_select_model_prefers_cheaper_model_when_quality_is_tied():
    candidates = [
        RoutingCandidate(model="gpt-4o", provider="openai"),
        RoutingCandidate(model="gpt-4o-mini", provider="openai"),
    ]
    policy = RoutingPolicy(cost_weight=1.0, quality_weight=0.0)

    decision = select_model(candidates, policy)

    assert decision.chosen.model == "gpt-4o-mini"


def test_select_model_prefers_higher_quality_when_cost_is_ignored():
    candidates = [
        RoutingCandidate(model="gpt-4o", provider="openai"),
        RoutingCandidate(model="gpt-4o-mini", provider="openai"),
    ]
    policy = RoutingPolicy(cost_weight=0.0, quality_weight=1.0)
    quality = {"gpt-4o": 0.95, "gpt-4o-mini": 0.7}

    decision = select_model(candidates, policy, quality_of=quality)

    assert decision.chosen.model == "gpt-4o"


def test_select_model_excludes_models_below_the_required_context_window():
    candidates = [
        RoutingCandidate(model="gpt-4", provider="openai"),  # 8192 context
        RoutingCandidate(model="claude-3-opus", provider="anthropic"),  # 200000 context
    ]
    policy = RoutingPolicy(min_context_window=100_000)

    decision = select_model(candidates, policy)

    assert decision.chosen.model == "claude-3-opus"
    excluded_models = {c.model for c, _reason in decision.excluded}
    assert excluded_models == {"gpt-4"}


def test_select_model_excludes_models_without_required_vision_support():
    candidates = [
        RoutingCandidate(model="gpt-3.5-turbo", provider="openai"),  # no vision
        RoutingCandidate(model="gpt-4o", provider="openai"),  # vision
    ]
    policy = RoutingPolicy(require_vision=True)

    decision = select_model(candidates, policy)

    assert decision.chosen.model == "gpt-4o"


def test_select_model_raises_when_nothing_satisfies_the_policy():
    candidates = [RoutingCandidate(model="gpt-3.5-turbo", provider="openai")]
    policy = RoutingPolicy(require_vision=True)

    with pytest.raises(ValueError, match="gpt-3.5-turbo"):
        select_model(candidates, policy)


def test_select_model_treats_unbenchmarked_models_as_neutral_quality():
    candidates = [RoutingCandidate(model="gpt-4o-mini", provider="openai")]
    policy = RoutingPolicy()

    # No quality_of entry for gpt-4o-mini at all — must not raise a KeyError.
    decision = select_model(candidates, policy, quality_of={})

    assert decision.chosen.model == "gpt-4o-mini"
