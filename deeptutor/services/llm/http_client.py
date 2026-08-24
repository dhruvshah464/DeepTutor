"""
Shared httpx.AsyncClient for connection pooling across LLM provider calls.

Referenced by providers/anthropic.py (``from ..http_client import
get_shared_http_client``) but the module didn't exist — importing that
provider raised ModuleNotFoundError. A single pooled client avoids the
per-request TCP/TLS handshake overhead of constructing a fresh
httpx.AsyncClient (which is what anthropic.AsyncAnthropic does internally
if no http_client is passed) on every call.
"""

from __future__ import annotations

import asyncio

import httpx

_client: httpx.AsyncClient | None = None
_lock = asyncio.Lock()


async def get_shared_http_client() -> httpx.AsyncClient:
    """Return the process-wide pooled httpx.AsyncClient, creating it on first use."""
    global _client
    if _client is None:
        async with _lock:
            if _client is None:
                _client = httpx.AsyncClient(timeout=httpx.Timeout(120.0))
    return _client


async def close_shared_http_client() -> None:
    """Dispose the pooled client. Call on application shutdown."""
    global _client
    if _client is not None:
        await _client.aclose()
        _client = None
