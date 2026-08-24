from __future__ import annotations

import asyncio

from deeptutor.services.llm.usage import (
    current_usage,
    record_usage,
    total_usage,
    usage_scope,
)


def test_record_usage_outside_scope_is_a_noop():
    record_usage(model="gpt-4o-mini", prompt_tokens=10, completion_tokens=5)
    assert current_usage() == []


def test_usage_scope_accumulates_entries():
    with usage_scope() as entries:
        record_usage(model="gpt-4o-mini", provider="openai", prompt_tokens=10, completion_tokens=5)
        record_usage(model="gpt-4o-mini", provider="openai", prompt_tokens=20, completion_tokens=8)
        assert len(entries) == 2

        total = total_usage()
        assert total.prompt_tokens == 30
        assert total.completion_tokens == 13
        assert total.total_tokens == 43

    # Scope closed: no leakage to the outer (unscoped) context.
    assert current_usage() == []


def test_record_usage_ignores_missing_token_counts():
    with usage_scope():
        record_usage(model="gpt-4o-mini", prompt_tokens=None, completion_tokens=None)
        assert current_usage() == []


def test_nested_scopes_do_not_leak_into_each_other():
    with usage_scope() as outer:
        record_usage(model="a", prompt_tokens=1, completion_tokens=1)
        with usage_scope() as inner:
            record_usage(model="b", prompt_tokens=2, completion_tokens=2)
            assert len(inner) == 1
        # Back in the outer scope: still just the one entry from before.
        assert len(outer) == 1
        record_usage(model="a", prompt_tokens=3, completion_tokens=3)
        assert len(outer) == 2


def test_concurrent_tasks_get_isolated_scopes():
    """Two 'requests' running concurrently must never see each other's usage.

    This is the exact bug _shared_stats has (a process-global dict keyed by
    module name): concurrent requests would commingle their token counts.
    contextvars are copied per-task, so each task's usage_scope() is private.
    """

    async def _one_request(prompt_tokens: int) -> int:
        with usage_scope():
            record_usage(model="m", prompt_tokens=prompt_tokens, completion_tokens=0)
            await asyncio.sleep(0)  # yield control to the other task mid-scope
            record_usage(model="m", prompt_tokens=prompt_tokens, completion_tokens=0)
            return total_usage().prompt_tokens

    async def _run():
        return await asyncio.gather(_one_request(10), _one_request(100))

    results = asyncio.run(_run())
    assert results == [20, 200]
