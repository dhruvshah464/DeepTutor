"""
Unified WebSocket Endpoint
==========================

Single ``/api/v1/ws`` endpoint for turn-based execution and replayable streaming.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect

from meridian.platform.auth.dependencies import get_ws_user

router = APIRouter()
logger = logging.getLogger(__name__)


@router.websocket("/ws")
async def unified_websocket(ws: WebSocket, user: dict = Depends(get_ws_user)) -> None:
    await ws.accept()
    closed = False
    user_id = str(user.get("sub") or "")
    org_id = user.get("org_id")
    owned_session_ids: set[str] = set()
    subscription_tasks: dict[str, asyncio.Task[None]] = {}

    async def _authorized_for_session(session_id: str) -> bool:
        """Deny cross-user access to another user's turn/session stream.

        A session this connection itself created (via ``message``/``start_turn``)
        is trusted immediately without a lookup. Any other session_id must
        resolve, via the Postgres mirror, to a ChatSession owned by this
        connection's user (or the same org). Anonymous/local (non-SaaS)
        deployments — where AUTH_REQUIRED=false and user_id is "anonymous" —
        skip this check entirely, matching get_ws_user's own dev-mode bypass.
        """
        if user_id == "anonymous":
            return True
        if session_id in owned_session_ids:
            return True
        from meridian.persistence.mirror import get_session_owner

        owner_user_id, owner_org_id = await get_session_owner(session_id)
        if owner_user_id is None:
            # Not mirrored yet (mirror lag, or a pre-SaaS/legacy session) —
            # fail closed rather than guessing at ownership.
            return False
        if owner_user_id == user_id:
            return True
        return bool(org_id) and owner_org_id == org_id

    async def safe_send(data: dict[str, Any]) -> None:
        nonlocal closed
        if closed:
            return
        try:
            await ws.send_json(data)
        except Exception:
            closed = True

    async def stop_subscription(key: str) -> None:
        task = subscription_tasks.pop(key, None)
        if task is None:
            return
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

    async def subscribe_turn(turn_id: str, after_seq: int = 0) -> bool:
        from deeptutor.services.session import get_turn_runtime_manager

        runtime = get_turn_runtime_manager()
        turn = await runtime.store.get_turn(turn_id)
        session_id = str((turn or {}).get("session_id") or "")
        if not session_id or not await _authorized_for_session(session_id):
            await safe_send({"type": "error", "content": f"Turn not found: {turn_id}"})
            return False
        owned_session_ids.add(session_id)

        async def _forward() -> None:
            async for event in runtime.subscribe_turn(turn_id, after_seq=after_seq):
                await safe_send(event)

        await stop_subscription(turn_id)
        subscription_tasks[turn_id] = asyncio.create_task(_forward())
        return True

    async def subscribe_session(session_id: str, after_seq: int = 0) -> bool:
        from deeptutor.services.session import get_turn_runtime_manager

        if not await _authorized_for_session(session_id):
            await safe_send({"type": "error", "content": f"Session not found: {session_id}"})
            return False

        async def _forward() -> None:
            runtime = get_turn_runtime_manager()
            async for event in runtime.subscribe_session(session_id, after_seq=after_seq):
                await safe_send(event)

        key = f"session:{session_id}"
        await stop_subscription(key)
        subscription_tasks[key] = asyncio.create_task(_forward())
        return True

    try:
        while not closed:
            raw = await ws.receive_text()
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                await safe_send({"type": "error", "content": "Invalid JSON."})
                continue

            msg_type = msg.get("type")

            if msg_type in {"message", "start_turn"}:
                from deeptutor.services.session import get_turn_runtime_manager

                runtime = get_turn_runtime_manager()
                msg = {**msg, "user_id": user_id, "org_id": org_id}
                try:
                    session, turn = await runtime.start_turn(msg)
                except RuntimeError as exc:
                    await safe_send(
                        {
                            "type": "error",
                            "source": "unified_ws",
                            "stage": "",
                            "content": str(exc),
                            "metadata": {"turn_terminal": True, "status": "rejected"},
                            "session_id": str(msg.get("session_id") or ""),
                            "turn_id": "",
                            "seq": 0,
                        }
                    )
                    continue
                owned_session_ids.add(str(session.get("id") or ""))
                await subscribe_turn(turn["id"], after_seq=0)
                continue

            if msg_type == "subscribe_turn":
                turn_id = str(msg.get("turn_id") or "").strip()
                if not turn_id:
                    await safe_send({"type": "error", "content": "Missing turn_id."})
                    continue
                await subscribe_turn(turn_id, after_seq=int(msg.get("after_seq") or 0))
                continue

            if msg_type == "subscribe_session":
                session_id = str(msg.get("session_id") or "").strip()
                if not session_id:
                    await safe_send({"type": "error", "content": "Missing session_id."})
                    continue
                await subscribe_session(session_id, after_seq=int(msg.get("after_seq") or 0))
                continue

            if msg_type == "resume_from":
                turn_id = str(msg.get("turn_id") or "").strip()
                if not turn_id:
                    await safe_send({"type": "error", "content": "Missing turn_id."})
                    continue
                await subscribe_turn(turn_id, after_seq=int(msg.get("seq") or 0))
                continue

            if msg_type == "unsubscribe":
                turn_id = str(msg.get("turn_id") or "").strip()
                if turn_id:
                    await stop_subscription(turn_id)
                session_id = str(msg.get("session_id") or "").strip()
                if session_id:
                    await stop_subscription(f"session:{session_id}")
                continue

            if msg_type == "cancel_turn":
                turn_id = str(msg.get("turn_id") or "").strip()
                if not turn_id:
                    await safe_send({"type": "error", "content": "Missing turn_id."})
                    continue
                from deeptutor.services.session import get_turn_runtime_manager

                runtime = get_turn_runtime_manager()
                turn = await runtime.store.get_turn(turn_id)
                session_id = str((turn or {}).get("session_id") or "")
                if not session_id or not await _authorized_for_session(session_id):
                    await safe_send({"type": "error", "content": f"Turn not found: {turn_id}"})
                    continue
                cancelled = await runtime.cancel_turn(turn_id)
                if not cancelled:
                    await safe_send({"type": "error", "content": f"Turn not found: {turn_id}"})
                continue

            await safe_send({"type": "error", "content": f"Unknown type: {msg_type}"})

    except WebSocketDisconnect:
        logger.debug("Client disconnected from /ws")
    except Exception as exc:
        logger.error("Unified WS error: %s", exc, exc_info=True)
        await safe_send({"type": "error", "content": str(exc)})
    finally:
        closed = True
        for key in list(subscription_tasks.keys()):
            await stop_subscription(key)
