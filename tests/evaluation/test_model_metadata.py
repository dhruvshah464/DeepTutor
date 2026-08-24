from __future__ import annotations

from meridian.evaluation.model_metadata import (
    MODEL_CATALOG,
    get_model_metadata,
    get_pricing,
)


def test_exact_match_returns_the_named_model():
    metadata = get_model_metadata("gpt-4o")
    assert metadata.name == "gpt-4o"
    assert metadata.context_window == 128_000


def test_fuzzy_match_finds_a_versioned_model_name():
    # e.g. "gpt-4o-2024-08-06" isn't a catalog key, but should fuzzy-match "gpt-4o".
    metadata = get_model_metadata("gpt-4o-2024-08-06")
    assert metadata.name == "gpt-4o"


def test_unknown_model_falls_back_to_gpt_4o_mini():
    metadata = get_model_metadata("some-totally-unknown-model-xyz")
    assert metadata.name == "gpt-4o-mini"


def test_get_pricing_matches_the_backcompat_dict_shape():
    pricing = get_pricing("claude-3-opus")
    assert pricing == {"input": 0.015, "output": 0.075}


def test_catalog_is_shared_across_the_three_formerly_divergent_modules():
    from deeptutor.agents.research.utils.token_tracker import (
        MODEL_PRICING as research_pricing,
    )
    from deeptutor.agents.solve.utils.token_tracker import MODEL_PRICING as solve_pricing
    from deeptutor.logging.stats.llm_stats import MODEL_PRICING as stats_pricing

    for name, metadata in MODEL_CATALOG.items():
        expected = {"input": metadata.input_price_per_1k, "output": metadata.output_price_per_1k}
        assert research_pricing[name] == expected
        assert solve_pricing[name] == expected
        assert stats_pricing[name] == expected
