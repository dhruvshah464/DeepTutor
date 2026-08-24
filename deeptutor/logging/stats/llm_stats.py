"""
LLM Stats Tracker
=================

Simple utility for tracking LLM token usage and costs across all modules.
Outputs summary via the unified logging system.

Usage:
    from deeptutor.logging import LLMStats

    stats = LLMStats("Solver")

    # After each LLM call:
    stats.add_call(
        model="gpt-4o-mini",
        prompt_tokens=100,
        completion_tokens=50
    )

    # At the end:
    stats.log_summary()  # Uses logging system
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING, Any, Optional

from meridian.evaluation.model_metadata import MODEL_CATALOG, get_pricing

if TYPE_CHECKING:
    from ..logger import Logger

try:
    import tiktoken

    _ENCODING = tiktoken.get_encoding("cl100k_base")
except Exception:  # pragma: no cover - tiktoken is a declared dependency
    _ENCODING = None

# Model pricing per 1K tokens (USD). Sourced from meridian.evaluation.model_metadata
# (the consolidated catalog — see its module docstring for why this used to
# be three separate, diverging copies of this dict). MODEL_PRICING is kept
# as a derived dict, not deleted, since deeptutor/logging/__init__.py
# re-exports it as a public symbol other code may import directly.
MODEL_PRICING = {
    name: {"input": m.input_price_per_1k, "output": m.output_price_per_1k}
    for name, m in MODEL_CATALOG.items()
}


def estimate_tokens(text: str) -> int:
    """Estimate token count via tiktoken's cl100k_base BPE encoding.

    Only used when real usage numbers aren't available (add_call's
    prompt_tokens/completion_tokens args, populated from the API's actual
    response.usage, are always preferred — see BaseAgent._track_tokens).
    The previous `len(text.split()) * 1.3` word-count heuristic was
    catastrophically wrong for CJK content this project handles: a Chinese
    paragraph with no whitespace splits into ~1 "word" regardless of its
    actual length. BPE tokenization doesn't depend on whitespace.
    """
    if not text:
        return 0
    if _ENCODING is not None:
        return len(_ENCODING.encode(text))
    # Fallback if tiktoken's encoding data can't be loaded (e.g. no network
    # access to fetch it on first use in a sandboxed environment): a
    # character-based estimate is still far closer for CJK text than a
    # whitespace word count.
    return max(1, len(text) // 3)


@dataclass
class LLMCall:
    """Single LLM call record."""

    model: str
    prompt_tokens: int
    completion_tokens: int
    cost: float
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


class LLMStats:
    """
    LLM usage statistics tracker.
    Tracks token usage and costs, outputs summary to terminal.
    """

    def __init__(self, module_name: str = "Module"):
        """
        Initialize stats tracker.

        Args:
            module_name: Name of the module (for display)
        """
        self.module_name = module_name
        self.calls: list[LLMCall] = []
        self.total_prompt_tokens = 0
        self.total_completion_tokens = 0
        self.total_cost = 0.0
        self.model_used: Optional[str] = None

    def add_call(
        self,
        model: str,
        prompt_tokens: Optional[int] = None,
        completion_tokens: Optional[int] = None,
        # Alternative: estimate from text
        system_prompt: Optional[str] = None,
        user_prompt: Optional[str] = None,
        response: Optional[str] = None,
    ):
        """
        Add an LLM call to the stats.

        Args:
            model: Model name
            prompt_tokens: Number of prompt tokens (if known)
            completion_tokens: Number of completion tokens (if known)
            system_prompt: System prompt text (for estimation)
            user_prompt: User prompt text (for estimation)
            response: Response text (for estimation)
        """
        # Estimate tokens if not provided
        if prompt_tokens is None and (system_prompt or user_prompt):
            prompt_text = (system_prompt or "") + "\n" + (user_prompt or "")
            prompt_tokens = estimate_tokens(prompt_text)

        if completion_tokens is None and response:
            completion_tokens = estimate_tokens(response)

        prompt_tokens = prompt_tokens or 0
        completion_tokens = completion_tokens or 0

        # Calculate cost
        pricing = get_pricing(model)
        cost = (prompt_tokens / 1000.0) * pricing["input"] + (completion_tokens / 1000.0) * pricing[
            "output"
        ]

        # Record call
        call = LLMCall(
            model=model, prompt_tokens=prompt_tokens, completion_tokens=completion_tokens, cost=cost
        )
        self.calls.append(call)

        # Update totals
        self.total_prompt_tokens += prompt_tokens
        self.total_completion_tokens += completion_tokens
        self.total_cost += cost

        # Track primary model
        if self.model_used is None:
            self.model_used = model

    def get_summary(self) -> dict[str, Any]:
        """Get summary as dictionary."""
        return {
            "module": self.module_name,
            "model": self.model_used or "Unknown",
            "calls": len(self.calls),
            "prompt_tokens": self.total_prompt_tokens,
            "completion_tokens": self.total_completion_tokens,
            "total_tokens": self.total_prompt_tokens + self.total_completion_tokens,
            "cost_usd": self.total_cost,
        }

    def log_summary(self, logger: Optional["Logger"] = None):
        """
        Log summary using the unified logging system.

        Args:
            logger: Optional Logger instance. If None, creates one using module_name.
        """
        if len(self.calls) == 0:
            return

        # Import here to avoid circular imports
        from ..logger import get_logger

        if logger is None:
            logger = get_logger(self.module_name)

        total_tokens = self.total_prompt_tokens + self.total_completion_tokens

        logger.info("=" * 60)
        logger.info(f"LLM Usage Summary for {self.module_name}")
        logger.info("=" * 60)
        logger.info(f"Model       : {self.model_used or 'Unknown'}")
        logger.info(f"API Calls   : {len(self.calls)}")
        logger.info(
            f"Tokens      : {total_tokens:,} (Input: {self.total_prompt_tokens:,}, Output: {self.total_completion_tokens:,})"
        )
        logger.info(f"Cost        : ${self.total_cost:.6f} USD")
        logger.info("=" * 60)

    def print_summary(self):
        """
        Print summary to terminal.

        Deprecated: Use log_summary() instead for consistent logging.
        """
        self.log_summary()

    def reset(self):
        """Reset all statistics."""
        self.calls.clear()
        self.total_prompt_tokens = 0
        self.total_completion_tokens = 0
        self.total_cost = 0.0
        self.model_used = None
