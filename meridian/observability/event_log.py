"""
A durable sink for deeptutor.events.event_bus.EventBus.

EventBus had real publishers (orchestrator.py, main_solver.py,
tutorbot/manager.py all call .publish()) and zero subscribers — every
SOLVE_COMPLETE/QUESTION_COMPLETE/CAPABILITY_COMPLETE event was constructed,
queued, and then silently dropped inside _process_events' "no handlers"
branch. This module is the subscriber: it logs each event as a structured
record, the same durable-by-default pattern export_span() uses for spans
(a real sink with zero extra dependencies, not a promise of one).

Kept decoupled from deeptutor.events' Event/EventType classes (duck-typed
via Any) so this module doesn't need to import deeptutor.* — the
subscribe() calls that need those types live in deeptutor/api/main.py,
which is free to import both deeptutor.events and meridian.observability.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger("meridian.observability")


async def log_event(event: Any) -> None:
    """EventBus handler: log one Event as a structured record.

    Never raises — EventBus's own _process_events already logs a handler
    exception and moves on, but a broken sink shouldn't even risk that.
    """
    try:
        event_type = getattr(event, "type", None)
        type_value = getattr(event_type, "value", event_type)
        logger.info(
            "domain_event",
            extra={
                "event_id": getattr(event, "event_id", None),
                "event_type": type_value,
                "task_id": getattr(event, "task_id", None),
                "success": getattr(event, "success", None),
                "tools_used": getattr(event, "tools_used", None),
                "metadata": getattr(event, "metadata", None),
            },
        )
    except Exception:
        logger.debug("Failed to log domain event", exc_info=True)
