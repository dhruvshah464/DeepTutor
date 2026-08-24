"""
Non-fatal Postgres mirror for the DeepTutor engine's turn/session store.

The engine's authoritative turn state lives in SQLite
(``deeptutor/services/session/sqlite_store.py``); this module mirrors it
into ``ChatSession``/``ChatMessage`` rows so the Meridian SaaS layer has
something to query for ``/admin/stats``, ``/analytics/learner``, usage
metering, and WebSocket-subscription authorization (see
``deeptutor/api/routers/unified_ws.py``).

Called from ``deeptutor/services/session/turn_runtime.py::_persist_and_publish``,
modeled on that module's own non-fatal ``_mirror_event_to_workspace`` hook:
best-effort, wrapped in try/except, never raises, and never blocks or fails
a turn. A bug here must never break a tutoring turn.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

# Per-turn accumulation buffer. Streamed CONTENT events arrive one chunk at a
# time via _persist_and_publish; we buffer the assistant's text here and only
# write it out once, on the terminal DONE event, to avoid one Postgres write
# per token.
_turn_buffers: dict[str, dict[str, Any]] = {}


async def mirror_turn_event(
    *,
    session_id: str,
    turn_id: str,
    capability: str,
    user_id: str | None,
    org_id: str | None,
    language: str,
    user_content: str,
    event_type: str,
    event_content: str,
    event_metadata: dict[str, Any] | None,
) -> None:
    """Mirror one turn event into the Postgres ChatSession/ChatMessage tables.

    No-op for anonymous/local (non-SaaS) usage, i.e. when ``user_id`` is
    absent — most of the inherited engine's tests and the CLI run without
    a user at all, and there is nothing meaningful to mirror for them.
    """
    if not user_id or user_id == "anonymous":
        return

    try:
        if event_type == "session":
            await _ensure_session(
                session_id=session_id,
                user_id=user_id,
                org_id=org_id,
                capability=capability,
                language=language,
            )
            _turn_buffers[turn_id] = {"assistant_content": ""}
            return

        if event_type == "content" and (event_metadata or {}).get("call_kind") in (
            None,
            "llm_final_response",
        ):
            buf = _turn_buffers.setdefault(turn_id, {"assistant_content": ""})
            buf["assistant_content"] += event_content
            return

        if event_type == "done":
            buf = _turn_buffers.pop(turn_id, {"assistant_content": ""})
            usage = (event_metadata or {}).get("usage") or {}
            await _flush_turn(
                session_id=session_id,
                turn_id=turn_id,
                capability=capability,
                user_content=user_content,
                assistant_content=buf.get("assistant_content", ""),
                prompt_tokens=usage.get("prompt_tokens"),
                completion_tokens=usage.get("completion_tokens"),
            )
    except Exception:
        logger.debug("Postgres turn mirror failed for turn %s", turn_id, exc_info=True)


async def _ensure_session(
    *,
    session_id: str,
    user_id: str,
    org_id: str | None,
    capability: str,
    language: str,
) -> None:
    from sqlalchemy import select

    from .engine import get_async_session
    from .models.session import ChatSession

    async with get_async_session() as db:
        existing = (
            await db.execute(select(ChatSession).where(ChatSession.id == session_id))
        ).scalar_one_or_none()
        if existing is not None:
            return
        db.add(
            ChatSession(
                id=session_id,
                user_id=user_id,
                org_id=org_id,
                capability=capability,
                language=language or "en",
            )
        )


async def _flush_turn(
    *,
    session_id: str,
    turn_id: str,
    capability: str,
    user_content: str,
    assistant_content: str,
    prompt_tokens: int | None,
    completion_tokens: int | None,
) -> None:
    from sqlalchemy import func, select

    from .engine import get_async_session
    from .models.session import ChatMessage, ChatSession

    async with get_async_session() as db:
        session_row = (
            await db.execute(select(ChatSession).where(ChatSession.id == session_id))
        ).scalar_one_or_none()
        if session_row is None:
            # Session event never mirrored (e.g. mirror was down when the
            # turn started); nothing to attach messages to.
            return

        next_seq = (
            await db.execute(
                select(func.coalesce(func.max(ChatMessage.seq), 0)).where(
                    ChatMessage.session_id == session_id
                )
            )
        ).scalar_one()

        if user_content:
            db.add(
                ChatMessage(
                    session_id=session_id,
                    role="user",
                    content=user_content,
                    seq=next_seq + 1,
                    turn_id=turn_id,
                    capability=capability,
                )
            )
            next_seq += 1

        if assistant_content:
            db.add(
                ChatMessage(
                    session_id=session_id,
                    role="assistant",
                    content=assistant_content,
                    seq=next_seq + 1,
                    turn_id=turn_id,
                    capability=capability,
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                )
            )

        session_row.turn_count = (session_row.turn_count or 0) + 1


async def get_session_owner(session_id: str) -> tuple[str | None, str | None]:
    """Return ``(user_id, org_id)`` for a mirrored session, or ``(None, None)``.

    Used by ``unified_ws.py`` to authorize ``subscribe_session``/
    ``subscribe_turn`` against the connected user.
    """
    try:
        from sqlalchemy import select

        from .engine import get_async_session
        from .models.session import ChatSession

        async with get_async_session() as db:
            row = (
                await db.execute(select(ChatSession).where(ChatSession.id == session_id))
            ).scalar_one_or_none()
            if row is None:
                return None, None
            return row.user_id, row.org_id
    except Exception:
        logger.debug("Failed to look up session owner for %s", session_id, exc_info=True)
        return None, None


