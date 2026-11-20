from __future__ import annotations

import os

from .base import Backend, BackendError, BackendRefusal, GenerationRequest

__all__ = ["Backend", "BackendError", "BackendRefusal", "GenerationRequest", "make_backend"]


def make_backend(name: str | None = None, **kwargs) -> Backend:
    """Create a backend by name: 'claude' (default), 'hf' (local Transformers) or 'mock' (offline)."""
    name = (name or os.environ.get("LOREWEAVE_BACKEND") or "claude").lower()
    if name == "claude":
        from .claude import ClaudeBackend

        return ClaudeBackend(**kwargs)
    if name in ("hf", "huggingface", "local"):
        from .hf import HFBackend

        return HFBackend(**kwargs)
    if name == "mock":
        from .mock import MockBackend

        return MockBackend(**kwargs)
    raise BackendError(f"Unknown backend '{name}'")
