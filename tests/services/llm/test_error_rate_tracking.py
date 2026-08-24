from __future__ import annotations

import pytest

import deeptutor.services.llm.executors as executors_module
from deeptutor.services.provider_registry import ProviderSpec
from deeptutor.utils.error_rate_tracker import ErrorRateTracker


class _FakeMessage:
    content = "hello"


class _FakeChoice:
    message = _FakeMessage()


class _FakeUsage:
    prompt_tokens = 10
    completion_tokens = 5
    total_tokens = 15


class _FakeResponse:
    choices = [_FakeChoice()]
    usage = _FakeUsage()


class _FakeCompletions:
    def __init__(self, *, raises: bool):
        self._raises = raises

    async def create(self, **kwargs):
        if self._raises:
            raise RuntimeError("upstream 500")
        return _FakeResponse()


class _FakeChat:
    def __init__(self, *, raises: bool):
        self.completions = _FakeCompletions(raises=raises)


class _FakeAsyncOpenAI:
    def __init__(self, *, raises: bool = False, **_kwargs):
        self.chat = _FakeChat(raises=raises)


@pytest.fixture
def fresh_tracker(monkeypatch):
    tracker = ErrorRateTracker(window_size=60, threshold=0.5)
    monkeypatch.setattr(executors_module, "record_provider_call", tracker.record_call)
    return tracker


def _fake_find_by_name(monkeypatch):
    spec = ProviderSpec(name="acme", keywords=("acme",), env_key="ACME_API_KEY")
    monkeypatch.setattr(
        executors_module, "find_by_name", lambda name: spec if name == "acme" else None
    )


@pytest.mark.asyncio
async def test_sdk_complete_records_a_successful_call(monkeypatch, fresh_tracker):
    _fake_find_by_name(monkeypatch)
    monkeypatch.setattr(
        executors_module, "AsyncOpenAI", lambda **kwargs: _FakeAsyncOpenAI(raises=False)
    )

    await executors_module.sdk_complete(
        prompt="hi", system_prompt="sys", provider_name="acme", model="gpt-4o-mini",
        api_key="key", base_url=None,
    )

    assert fresh_tracker.get_error_rate("acme") == 0.0


@pytest.mark.asyncio
async def test_sdk_complete_records_a_failed_call_and_reraises(monkeypatch, fresh_tracker):
    _fake_find_by_name(monkeypatch)
    monkeypatch.setattr(
        executors_module, "AsyncOpenAI", lambda **kwargs: _FakeAsyncOpenAI(raises=True)
    )

    with pytest.raises(RuntimeError, match="upstream 500"):
        await executors_module.sdk_complete(
            prompt="hi", system_prompt="sys", provider_name="acme", model="gpt-4o-mini",
            api_key="key", base_url=None,
        )

    assert fresh_tracker.get_error_rate("acme") == 1.0


@pytest.mark.asyncio
async def test_repeated_failures_cross_the_error_rate_threshold(monkeypatch, fresh_tracker):
    _fake_find_by_name(monkeypatch)
    monkeypatch.setattr(
        executors_module, "AsyncOpenAI", lambda **kwargs: _FakeAsyncOpenAI(raises=True)
    )

    for _ in range(3):
        with pytest.raises(RuntimeError):
            await executors_module.sdk_complete(
                prompt="hi", system_prompt="sys", provider_name="acme", model="gpt-4o-mini",
                api_key="key", base_url=None,
            )

    assert fresh_tracker.check_threshold("acme") is True
