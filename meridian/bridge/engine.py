"""
The one seam through which meridian/ reaches into the inherited DeepTutor
engine (deeptutor/). See ARCHITECTURE.md.

Every other module under meridian/ must go through this module rather than
importing `deeptutor.*` directly. Keeping the imports in one place means the
engine can be swapped, mocked, or upgraded by touching this file alone.
"""

from __future__ import annotations

from typing import Any


def get_llm_client() -> Any:
    """Return the engine's configured LLM client."""
    from deeptutor.services.llm import get_llm_client as _get_llm_client

    return _get_llm_client()


def get_embedding_client() -> Any:
    """Return the engine's configured embedding client."""
    from deeptutor.services.embedding import get_embedding_client as _get_embedding_client

    return _get_embedding_client()
