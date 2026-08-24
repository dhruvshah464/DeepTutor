"""
Consolidated model pricing/metadata catalog.

Was three separate, silently-diverging MODEL_PRICING dicts:
  deeptutor/logging/stats/llm_stats.py
  deeptutor/agents/research/utils/token_tracker.py
  deeptutor/agents/solve/utils/token_tracker.py
Same shape ({"input": ..., "output": ...} USD per 1K tokens), same fuzzy
matching algorithm (exact, then substring, then fall back to gpt-4o-mini),
copy-pasted three times and already inconsistent in coverage (research's
table is missing every non-OpenAI/DeepSeek model the solve one has).

This is one source of truth; the three original modules now delegate here
(see their get_model_pricing()/get_pricing() functions) rather than being
deleted outright, since dozens of call sites across agents/solve and
agents/research import MODEL_PRICING and get_model_pricing directly by
name — changing those call sites is out of scope for a pricing-table
consolidation.

Context window and capability fields are metadata this project didn't
track anywhere before; they exist here for meridian/evaluation/'s router
and benchmark harness, which need to know what a model *can* do, not just
what it costs. Extend PROVIDERS in deeptutor/services/provider_registry.py
first when adding a new provider; add its models' pricing/metadata here.
"""

from __future__ import annotations

from dataclasses import dataclass

FALLBACK_MODEL = "gpt-4o-mini"


@dataclass(frozen=True)
class ModelMetadata:
    name: str
    input_price_per_1k: float
    output_price_per_1k: float
    context_window: int = 128_000
    supports_vision: bool = False
    supports_tools: bool = True
    supports_reasoning: bool = False


# Prices are illustrative list prices as of the three source tables'
# last update, not a live-fetched or contractually guaranteed figure —
# see README's metric-honesty rule: don't publish a number nothing
# reproduces. meridian/evaluation/'s benchmark harness is where a real,
# dated, sourced pricing table belongs once it exists.
MODEL_CATALOG: dict[str, ModelMetadata] = {
    # --- OpenAI ---
    "gpt-4o": ModelMetadata("gpt-4o", 0.0025, 0.010, context_window=128_000, supports_vision=True),
    "gpt-4o-mini": ModelMetadata("gpt-4o-mini", 0.00015, 0.0006, context_window=128_000, supports_vision=True),
    "gpt-4-turbo": ModelMetadata("gpt-4-turbo", 0.01, 0.03, context_window=128_000, supports_vision=True),
    "gpt-4": ModelMetadata("gpt-4", 0.03, 0.06, context_window=8_192),
    "gpt-4-32k": ModelMetadata("gpt-4-32k", 0.06, 0.12, context_window=32_768),
    "gpt-3.5-turbo": ModelMetadata("gpt-3.5-turbo", 0.0005, 0.0015, context_window=16_385),
    "gpt-3.5-turbo-16k": ModelMetadata("gpt-3.5-turbo-16k", 0.003, 0.004, context_window=16_385),
    # --- DeepSeek ---
    "deepseek-chat": ModelMetadata("deepseek-chat", 0.00014, 0.00028, context_window=64_000),
    "deepseek-coder": ModelMetadata("deepseek-coder", 0.00014, 0.00028, context_window=64_000),
    # --- Anthropic ---
    "claude-3-opus": ModelMetadata("claude-3-opus", 0.015, 0.075, context_window=200_000, supports_vision=True),
    "claude-3-sonnet": ModelMetadata("claude-3-sonnet", 0.003, 0.015, context_window=200_000, supports_vision=True),
    "claude-3-haiku": ModelMetadata("claude-3-haiku", 0.00025, 0.00125, context_window=200_000, supports_vision=True),
    "claude-3-5-sonnet": ModelMetadata("claude-3-5-sonnet", 0.003, 0.015, context_window=200_000, supports_vision=True),
    # --- Google ---
    "gemini-pro": ModelMetadata("gemini-pro", 0.0005, 0.0015, context_window=32_760),
    "gemini-1.5-pro": ModelMetadata("gemini-1.5-pro", 0.00125, 0.005, context_window=2_000_000, supports_vision=True),
    "gemini-1.5-flash": ModelMetadata("gemini-1.5-flash", 0.000075, 0.0003, context_window=1_000_000, supports_vision=True),
}


def get_model_metadata(model: str) -> ModelMetadata:
    """Exact match, then substring fuzzy match, then FALLBACK_MODEL's metadata."""
    if model in MODEL_CATALOG:
        return MODEL_CATALOG[model]
    model_lower = model.lower()
    for key, metadata in MODEL_CATALOG.items():
        if key.lower() in model_lower or model_lower in key.lower():
            return metadata
    return MODEL_CATALOG[FALLBACK_MODEL]


def get_pricing(model: str) -> dict[str, float]:
    """Back-compat shape matching the three original MODEL_PRICING tables."""
    metadata = get_model_metadata(model)
    return {"input": metadata.input_price_per_1k, "output": metadata.output_price_per_1k}
