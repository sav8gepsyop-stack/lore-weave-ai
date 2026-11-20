"""Pluggable text-generation backends."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import AsyncIterator, Literal

Effort = Literal["low", "medium", "high", "xhigh", "max"]


@dataclass
class GenerationRequest:
    system: str  # stable context (story bible); backends may cache it
    prompt: str  # per-call instructions and volatile context
    task: str = "text"  # tag used for logging and by the mock backend
    max_tokens: int = 16000
    effort: Effort | None = None  # None = backend default for the task
    expect_json: bool = False
    meta: dict = field(default_factory=dict)


class BackendError(RuntimeError):
    pass


class BackendRefusal(BackendError):
    """The model declined the request. Surface this to the author; do not rephrase to evade it."""


class Backend(ABC):
    name: str = "base"

    @abstractmethod
    def stream(self, req: GenerationRequest) -> AsyncIterator[str]:
        """Yield text chunks as they are generated."""

    async def complete(self, req: GenerationRequest) -> str:
        parts: list[str] = []
        async for chunk in self.stream(req):
            parts.append(chunk)
        return "".join(parts)

    def describe(self) -> dict:
        return {"name": self.name}
