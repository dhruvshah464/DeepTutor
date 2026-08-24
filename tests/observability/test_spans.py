from __future__ import annotations

import asyncio
import contextvars

from meridian.observability.spans import current_span, end_span, span, start_span


def test_span_context_manager_records_duration_and_ok_status():
    with span("do_work") as s:
        assert s.status == "running"
        assert s.end_time is None

    assert s.status == "ok"
    assert s.end_time is not None
    assert s.duration_ms is not None
    assert s.duration_ms >= 0


def test_span_context_manager_records_error_status_and_reraises():
    try:
        with span("do_work") as s:
            raise ValueError("boom")
    except ValueError:
        pass
    else:
        raise AssertionError("expected the exception to propagate")

    assert s.status == "error"
    assert s.error == "boom"


def test_nested_spans_have_a_parent_child_relationship():
    with span("outer") as outer:
        with span("inner") as inner:
            assert inner.parent_span_id == outer.span_id
            assert inner.trace_id == outer.trace_id


def test_span_context_manager_restores_the_previous_current_span_on_exit():
    with span("outer") as outer:
        with span("inner"):
            pass
        assert current_span() is outer
    assert current_span() is None


def test_current_span_is_none_outside_any_span():
    assert current_span() is None


def test_attributes_are_captured_as_kwargs():
    with span("work", capability="chat", turn_id="t1") as s:
        pass
    assert s.attributes == {"capability": "chat", "turn_id": "t1"}


def test_manual_start_and_end_span_produce_the_same_shape_as_the_context_manager():
    # start_span() sets the module's current-span contextvar and, unlike
    # span(), leaves callers responsible for restoring it (mirroring
    # OpenTelemetry's own manual span API) — run in an isolated copied
    # context so this doesn't leak "current span" state into later tests
    # in the same process.
    def _do():
        s = start_span("manual")
        assert s.status == "running"
        end_span(s, status="ok")
        assert s.status == "ok"
        assert s.duration_ms is not None

    contextvars.copy_context().run(_do)


def test_concurrent_tasks_get_isolated_span_stacks():
    """Same isolation guarantee as usage.py's contextvars scope: two
    concurrently-running turns must never see each other's current span,
    even though asyncio.gather interleaves them on the same event loop.
    """

    async def _one_turn(name: str) -> tuple[str, str | None, str]:
        with span(name) as s:
            await asyncio.sleep(0)
            # current_span() must be *this* task's own span, never the
            # other concurrently-running task's — that's the isolation
            # contextvars.Task-local copying is supposed to guarantee.
            seen = current_span()
            return (seen.span_id if seen else None, s.parent_span_id, s.trace_id)

    async def _run():
        return await asyncio.gather(_one_turn("turn-a"), _one_turn("turn-b"))

    (seen_a, parent_a, trace_a), (seen_b, parent_b, trace_b) = asyncio.run(_run())
    assert seen_a != seen_b  # each task saw its own span, not the other's
    assert parent_a is None  # neither task's top-level span leaked a parent
    assert parent_b is None
    assert trace_a != trace_b
