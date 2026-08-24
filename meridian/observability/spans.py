"""
Real span model with context propagation — what core/trace.py isn't.

deeptutor/core/trace.py builds dicts (call_id, phase, label, call_kind) for
rendering UI trace cards; it has no notion of a span's duration, no
parent-child relationship beyond a flat trace_group string, and nothing
exports it anywhere. This module is the actual tracing primitive:
contextvars-propagated spans with start/end timestamps, parent linkage,
and status, via start_span()/end_span() or the span() context manager.

Reconstructing full sub-span coverage from the existing StreamEvent stream
(STAGE_START/STAGE_END, used inconsistently by only 3 of BaseAgent's ~12
capabilities, plus core/trace.py's separately-keyed call_id metadata used
by 2 of them) would be fragile — those two mechanisms don't correlate
cleanly enough to reconstruct a reliable span tree after the fact. Instead
this is wired into the one chokepoint that's actually reliable for every
capability: TurnRuntimeManager wraps each turn in span("turn", ...) the
same way it already wraps it in usage_scope() (see
deeptutor/services/session/turn_runtime.py) — one real, exportable span
per turn today, with attributes including that turn's LLM usage totals.
Extending coverage to per-stage spans is future work, tracked here rather
than silently claimed.
"""

from __future__ import annotations

from collections.abc import Iterator
import contextlib
import contextvars
from dataclasses import dataclass, field
from datetime import datetime, timezone
import uuid

_current_span: contextvars.ContextVar["Span | None"] = contextvars.ContextVar(
    "current_span", default=None
)


@dataclass
class Span:
    span_id: str
    trace_id: str
    name: str
    parent_span_id: str | None = None
    start_time: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    end_time: datetime | None = None
    status: str = "running"  # "running" | "ok" | "error"
    attributes: dict[str, object] = field(default_factory=dict)
    error: str | None = None

    @property
    def duration_ms(self) -> float | None:
        if self.end_time is None:
            return None
        return (self.end_time - self.start_time).total_seconds() * 1000


def start_span(
    name: str,
    *,
    trace_id: str | None = None,
    attributes: dict[str, object] | None = None,
) -> Span:
    """Start a span as a child of the current span (if any), and make it current.

    Callers own ending it via end_span() — most code should prefer the
    span() context manager below, which does this automatically.
    """
    parent = _current_span.get()
    resolved_trace_id = trace_id or (parent.trace_id if parent else uuid.uuid4().hex)
    new_span = Span(
        span_id=uuid.uuid4().hex,
        trace_id=resolved_trace_id,
        name=name,
        parent_span_id=parent.span_id if parent else None,
        attributes=dict(attributes or {}),
    )
    _current_span.set(new_span)
    return new_span


def end_span(target: Span, *, status: str = "ok", error: str | None = None) -> Span:
    target.end_time = datetime.now(timezone.utc)
    target.status = status
    target.error = error
    return target


def current_span() -> Span | None:
    return _current_span.get()


@contextlib.contextmanager
def span(name: str, **attributes: object) -> Iterator[Span]:
    """Start a span, make it current for the duration of the block, and end it.

    Restores the previous current span on exit (success or exception) —
    nesting spans is just nesting this context manager.
    """
    parent = _current_span.get()
    new_span = start_span(name, attributes=attributes)
    try:
        yield new_span
    except Exception as exc:
        end_span(new_span, status="error", error=str(exc))
        raise
    else:
        end_span(new_span, status="ok")
    finally:
        _current_span.set(parent)
