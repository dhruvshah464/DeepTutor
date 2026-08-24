"""
Request-scoped LLM usage accounting.

``response.usage`` (prompt/completion token counts) used to be discarded
entirely in ``executors.py`` — the majority of production LLM calls left no
trace of their token cost. This module gives every call a place to record
that usage without changing the ``-> str`` / ``AsyncGenerator[str, None]``
return contracts that hundreds of call sites across the codebase depend on
(``factory.complete``/``factory.stream`` and everything built on them).

Uses ``contextvars`` rather than a process-global dict (see
``BaseAgent._shared_stats``, which is exactly that anti-pattern: a
class-level dict keyed by module name, shared and mutated across concurrent
requests with no isolation). Each turn/request establishes its own context
via ``usage_scope()``; nested LLM calls within that context record into the
same accumulator; unrelated concurrent requests never see each other's
entries, because contextvars are copied per-task, not shared.
"""

from __future__ import annotations

from collections.abc import Iterator
import contextlib
import contextvars
from dataclasses import dataclass

_usage_var: contextvars.ContextVar[list["LLMUsage"] | None] = contextvars.ContextVar(
    "llm_usage", default=None
)


@dataclass
class LLMUsage:
    model: str
    provider: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


@contextlib.contextmanager
def usage_scope() -> Iterator[list[LLMUsage]]:
    """Establish a fresh usage-recording scope (e.g. for one turn).

    Nested calls to ``record_usage`` while this scope is active append to
    the yielded list. Restores the previous scope (if any) on exit, so
    nesting is safe.
    """
    entries: list[LLMUsage] = []
    token = _usage_var.set(entries)
    try:
        yield entries
    finally:
        _usage_var.reset(token)


def record_usage(
    *,
    model: str,
    provider: str = "",
    prompt_tokens: int | None,
    completion_tokens: int | None,
    total_tokens: int | None = None,
) -> None:
    """Record one completion's token usage into the active scope, if any.

    A no-op outside of ``usage_scope()`` — callers that never opened a scope
    (e.g. a one-off script) simply don't get accounting, rather than
    erroring or leaking into a shared global.
    """
    entries = _usage_var.get()
    if entries is None:
        return
    if prompt_tokens is None and completion_tokens is None:
        return
    entries.append(
        LLMUsage(
            model=model,
            provider=provider,
            prompt_tokens=prompt_tokens or 0,
            completion_tokens=completion_tokens or 0,
            total_tokens=total_tokens
            if total_tokens is not None
            else (prompt_tokens or 0) + (completion_tokens or 0),
        )
    )


def current_usage() -> list[LLMUsage]:
    """Return the entries recorded so far in the active scope (or empty)."""
    return list(_usage_var.get() or [])


def total_usage() -> LLMUsage:
    """Sum every entry recorded so far in the active scope into one total."""
    entries = _usage_var.get() or []
    total = LLMUsage(model="", provider="")
    for entry in entries:
        total.prompt_tokens += entry.prompt_tokens
        total.completion_tokens += entry.completion_tokens
        total.total_tokens += entry.total_tokens
    return total
