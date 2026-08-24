from __future__ import annotations

import asyncio

import pytest

from deeptutor.events.event_bus import Event, EventBus, EventType


@pytest.fixture(autouse=True)
def _reset_event_bus():
    EventBus.reset()
    yield
    EventBus.reset()


@pytest.mark.asyncio
async def test_publish_without_a_subscriber_does_not_raise():
    """This was the bug: publishers existed, no subscribers did, and every
    event was silently dropped in _process_events' "no handlers" branch —
    which is correct, non-crashing behavior, just not useful on its own.
    """
    bus = EventBus()
    event = Event(type=EventType.SOLVE_COMPLETE, task_id="t1", user_input="q", agent_output="a")

    await bus.publish(event)
    await bus.flush(timeout=2.0)
    await bus.stop()


@pytest.mark.asyncio
async def test_a_subscribed_handler_receives_published_events():
    bus = EventBus()
    received: list[Event] = []

    async def handler(event: Event) -> None:
        received.append(event)

    bus.subscribe(EventType.SOLVE_COMPLETE, handler)
    event = Event(type=EventType.SOLVE_COMPLETE, task_id="t1", user_input="q", agent_output="a")

    await bus.publish(event)
    await bus.flush(timeout=2.0)
    await bus.stop()

    assert received == [event]


@pytest.mark.asyncio
async def test_publish_drops_events_when_the_queue_is_full_without_blocking():
    bus = EventBus()
    bus.MAX_QUEUE_SIZE = 2  # instance override for a fast test
    bus._task_queue = asyncio.Queue(maxsize=2)

    # Fill the queue directly (bypassing start(), so nothing drains it).
    for i in range(2):
        bus._task_queue.put_nowait(
            Event(type=EventType.SOLVE_COMPLETE, task_id=str(i), user_input="q", agent_output="a")
        )

    # A third publish must return promptly (not block) and log a drop,
    # rather than awaiting forever on a full queue.
    await asyncio.wait_for(
        bus.publish(
            Event(type=EventType.SOLVE_COMPLETE, task_id="overflow", user_input="q", agent_output="a")
        ),
        timeout=1.0,
    )

    await bus.stop()


@pytest.mark.asyncio
async def test_log_event_handles_a_real_event_without_raising(caplog):
    import logging

    from meridian.observability.event_log import log_event

    with caplog.at_level(logging.INFO, logger="meridian.observability"):
        await log_event(
            Event(
                type=EventType.CAPABILITY_COMPLETE,
                task_id="t1",
                user_input="q",
                agent_output="a",
                success=True,
            )
        )

    records = [r for r in caplog.records if r.message == "domain_event"]
    assert len(records) == 1
    assert records[0].event_type == "CAPABILITY_COMPLETE"
    assert records[0].task_id == "t1"
