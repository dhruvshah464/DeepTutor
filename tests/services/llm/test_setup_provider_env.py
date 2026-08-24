from __future__ import annotations

import os

import deeptutor.services.llm.executors as executors_module
from deeptutor.services.llm.executors import _setup_provider_env
from deeptutor.services.provider_registry import ProviderSpec


def test_setup_provider_env_overwrites_a_previously_set_key(monkeypatch):
    """Regression test: this used to be os.environ.setdefault(...), which
    meant the first request to set a provider's env var stuck for the
    lifetime of the process — every later request for that provider
    silently reused the *first* caller's credentials regardless of what
    api_key it was actually given. It must now always overwrite.
    """
    spec = ProviderSpec(name="acme", keywords=("acme",), env_key="ACME_API_KEY")
    monkeypatch.setattr(
        executors_module, "find_by_name", lambda name: spec if name == "acme" else None
    )
    monkeypatch.setenv("ACME_API_KEY", "user-a-key")

    _setup_provider_env("acme", "user-b-key", None)

    assert os.environ["ACME_API_KEY"] == "user-b-key"


def test_setup_provider_env_overwrites_env_extras_too(monkeypatch):
    spec = ProviderSpec(
        name="acme",
        keywords=("acme",),
        env_key="ACME_API_KEY",
        env_extras=(("ACME_REGION_KEY", "region-for-{api_key}"),),
    )
    monkeypatch.setattr(
        executors_module, "find_by_name", lambda name: spec if name == "acme" else None
    )
    monkeypatch.setenv("ACME_REGION_KEY", "region-for-user-a-key")

    _setup_provider_env("acme", "user-b-key", None)

    assert os.environ["ACME_REGION_KEY"] == "region-for-user-b-key"


def test_setup_provider_env_is_a_noop_without_a_key_or_spec(monkeypatch):
    monkeypatch.setattr(executors_module, "find_by_name", lambda name: None)
    # Should not raise even with no matching spec / no api_key.
    _setup_provider_env("unknown-provider", "some-key", None)
    _setup_provider_env("acme", None, None)
