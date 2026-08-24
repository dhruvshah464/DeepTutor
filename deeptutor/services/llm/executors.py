"""Provider-backed LLM executors (openai + anthropic SDKs, no litellm)."""

from __future__ import annotations

from collections.abc import AsyncGenerator
import os
from typing import Any
import uuid

from openai import AsyncOpenAI

from deeptutor.logging import get_logger
from deeptutor.services.llm.provider_registry import find_by_name, strip_provider_prefix

from .config import get_token_limit_kwargs
from .usage import record_usage
from .utils import extract_response_content

logger = get_logger("LLMExecutors")


def _build_messages(
    *,
    prompt: str,
    system_prompt: str,
    messages: list[dict[str, object]] | None,
) -> list[dict[str, object]]:
    if messages:
        return messages
    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": prompt},
    ]


def _setup_provider_env(provider_name: str, api_key: str | None, api_base: str | None) -> None:
    """Set provider credential/config env vars some SDKs read as a fallback.

    Was ``os.environ.setdefault(...)``: once any request set a provider's
    env var, it stuck for the lifetime of the process — every later request
    for that provider silently reused the *first* caller's credentials
    (any downstream code reading the env var directly, bypassing the
    explicit api_key this function's caller already passes to the SDK
    client, would leak across tenants). Always overwriting instead means
    the current request's credentials are always the ones in effect at the
    point of the call.

    This does not fully close the race under concurrency — os.environ is
    still process-global, so two requests for the same provider truly
    in flight at once can still interleave — but nothing here reads these
    env vars mid-request; they're set synchronously immediately before the
    SDK client is constructed with its own explicit api_key, so the window
    is effectively just this function's own callers.
    """
    spec = find_by_name(provider_name)
    if not spec or not api_key:
        return
    if spec.env_key:
        os.environ[spec.env_key] = api_key
    effective_base = api_base or spec.default_api_base
    for env_name, env_val in spec.env_extras:
        resolved = env_val.replace("{api_key}", api_key).replace("{api_base}", effective_base or "")
        os.environ[env_name] = resolved


def _resolve_model_and_base(
    provider_name: str,
    model: str,
    api_key: str | None,
    base_url: str | None,
) -> tuple[str, str | None, str | None]:
    """Resolve the actual model name, base_url, and api_key for the provider.

    Returns (resolved_model, effective_base_url, effective_api_key).
    """
    spec = find_by_name(provider_name)
    resolved_model = strip_provider_prefix(model, spec) if spec else model
    effective_base = base_url or (spec.default_api_base if spec else None) or None
    effective_key = api_key
    return resolved_model, effective_base, effective_key


async def sdk_complete(
    *,
    prompt: str,
    system_prompt: str,
    provider_name: str,
    model: str,
    api_key: str | None,
    base_url: str | None,
    messages: list[dict[str, object]] | None = None,
    api_version: str | None = None,
    extra_headers: dict[str, str] | None = None,
    reasoning_effort: str | None = None,
    **kwargs: object,
) -> str:
    """Non-streaming completion using the openai SDK."""
    _setup_provider_env(provider_name, api_key, base_url)
    resolved_model, effective_base, effective_key = _resolve_model_and_base(
        provider_name, model, api_key, base_url,
    )

    default_headers: dict[str, str] = {"x-session-affinity": uuid.uuid4().hex}
    if extra_headers:
        default_headers.update(extra_headers)

    client = AsyncOpenAI(
        api_key=effective_key or "no-key",
        base_url=effective_base,
        default_headers=default_headers,
        max_retries=0,
    )

    max_tokens_val = int(kwargs.pop("max_tokens", 4096))
    temperature_val = float(kwargs.pop("temperature", 0.7))

    payload: dict[str, Any] = {
        "model": resolved_model,
        "messages": _build_messages(
            prompt=prompt,
            system_prompt=system_prompt,
            messages=messages,
        ),
        "temperature": temperature_val,
    }

    token_kwargs = get_token_limit_kwargs(resolved_model, max_tokens_val)
    payload.update(token_kwargs)

    if reasoning_effort:
        payload["reasoning_effort"] = reasoning_effort
    payload.update(kwargs)

    response = await client.chat.completions.create(**payload)
    usage = getattr(response, "usage", None)
    if usage is not None:
        record_usage(
            model=resolved_model,
            provider=provider_name,
            prompt_tokens=getattr(usage, "prompt_tokens", None),
            completion_tokens=getattr(usage, "completion_tokens", None),
            total_tokens=getattr(usage, "total_tokens", None),
        )
    choices = getattr(response, "choices", None) or []
    if not choices:
        return ""
    message = getattr(choices[0], "message", None)
    if message is None and isinstance(choices[0], dict):
        message = choices[0].get("message")
    return extract_response_content(message)


async def sdk_stream(
    *,
    prompt: str,
    system_prompt: str,
    provider_name: str,
    model: str,
    api_key: str | None,
    base_url: str | None,
    messages: list[dict[str, object]] | None = None,
    api_version: str | None = None,
    extra_headers: dict[str, str] | None = None,
    reasoning_effort: str | None = None,
    **kwargs: object,
) -> AsyncGenerator[str, None]:
    """Streaming completion using the openai SDK."""
    _setup_provider_env(provider_name, api_key, base_url)
    resolved_model, effective_base, effective_key = _resolve_model_and_base(
        provider_name, model, api_key, base_url,
    )

    default_headers: dict[str, str] = {"x-session-affinity": uuid.uuid4().hex}
    if extra_headers:
        default_headers.update(extra_headers)

    client = AsyncOpenAI(
        api_key=effective_key or "no-key",
        base_url=effective_base,
        default_headers=default_headers,
        max_retries=0,
    )

    max_tokens_val = int(kwargs.pop("max_tokens", 4096))
    temperature_val = float(kwargs.pop("temperature", 0.7))

    payload: dict[str, Any] = {
        "model": resolved_model,
        "messages": _build_messages(
            prompt=prompt,
            system_prompt=system_prompt,
            messages=messages,
        ),
        "temperature": temperature_val,
        "stream": True,
        # Ask OpenAI-compatible endpoints for a final usage-only chunk.
        # Providers that don't understand this field generally ignore it
        # rather than erroring; the usage capture below is a no-op when a
        # provider doesn't send one back.
        "stream_options": {"include_usage": True},
    }

    token_kwargs = get_token_limit_kwargs(resolved_model, max_tokens_val)
    payload.update(token_kwargs)

    if reasoning_effort:
        payload["reasoning_effort"] = reasoning_effort
    payload.update(kwargs)

    stream_response = await client.chat.completions.create(**payload)
    async for chunk in stream_response:
        usage = getattr(chunk, "usage", None)
        if usage is not None:
            record_usage(
                model=resolved_model,
                provider=provider_name,
                prompt_tokens=getattr(usage, "prompt_tokens", None),
                completion_tokens=getattr(usage, "completion_tokens", None),
                total_tokens=getattr(usage, "total_tokens", None),
            )
        choices = getattr(chunk, "choices", None) or []
        if not choices:
            continue
        choice = choices[0]
        delta = getattr(choice, "delta", None)
        if delta is None and isinstance(choice, dict):
            delta = choice.get("delta")
        if delta is None:
            continue
        raw_content = getattr(delta, "content", None) if not isinstance(delta, dict) else delta.get("content")
        if raw_content is None:
            continue
        content = extract_response_content(delta)
        if content:
            yield content
