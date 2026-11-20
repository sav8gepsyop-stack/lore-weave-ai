"""Claude API backend (default).

- Streams every call, so long chapters never hit HTTP timeouts.
- Adaptive thinking with per-task effort: high for prose and planning, low for bookkeeping.
- The story bible is sent as a cached system block, so chapter after chapter reuses it cheaply.
- Server-side refusal fallbacks are enabled by default; if a request is still declined the engine
  raises BackendRefusal and the author sees it.
"""

from __future__ import annotations

import os
from typing import AsyncIterator

from .base import Backend, BackendError, BackendRefusal, GenerationRequest

DEFAULT_MODEL = "claude-opus-5-5"
FALLBACK_BETA = "server-side-fallback-2026-07-01"

TASK_EFFORT = {
    "chapter": "high",
    "revise": "high",
    "outline": "high",
    "macro_outline": "high",
    "replan": "high",
    "characters": "medium",
    "world": "medium",
    "style": "medium",
    "preview": "medium",
    "extract": "low",
    "continuity": "medium",
    "compress": "low",
    "repair_json": "low",
}


class ClaudeBackend(Backend):
    name = "claude"

    def __init__(self, model: str | None = None, effort: str | None = None, use_fallbacks: bool = True):
        try:
            import anthropic  # noqa: F401
        except ImportError as e:  # pragma: no cover
            raise BackendError("Install the 'anthropic' package to use the Claude backend") from e
        import anthropic

        self._anthropic = anthropic
        self.client = anthropic.AsyncAnthropic()
        self.model = model or os.environ.get("LOREWEAVE_CLAUDE_MODEL", DEFAULT_MODEL)
        self.effort_override = effort or os.environ.get("LOREWEAVE_EFFORT") or None
        self.use_fallbacks = use_fallbacks and os.environ.get("LOREWEAVE_FALLBACKS", "1") != "0"

    def describe(self) -> dict:
        return {"name": self.name, "model": self.model, "effort": self.effort_override or "per-task"}

    def _params(self, req: GenerationRequest, with_fallbacks: bool) -> dict:
        effort = req.effort or self.effort_override or TASK_EFFORT.get(req.task, "medium")
        params: dict = {
            "model": self.model,
            "max_tokens": req.max_tokens,
            "system": [{"type": "text", "text": req.system, "cache_control": {"type": "ephemeral"}}],
            "messages": [{"role": "user", "content": req.prompt}],
            "thinking": {"type": "adaptive"},
            "output_config": {"effort": effort},
        }
        if with_fallbacks:
            params["betas"] = [FALLBACK_BETA]
            params["fallbacks"] = "default"
        return params

    async def stream(self, req: GenerationRequest) -> AsyncIterator[str]:
        anthropic = self._anthropic
        with_fallbacks = self.use_fallbacks
        while True:
            yielded = False
            try:
                async with self.client.beta.messages.stream(**self._params(req, with_fallbacks)) as stream:
                    async for text in stream.text_stream:
                        yielded = True
                        yield text
                    final = await stream.get_final_message()
                if final.stop_reason == "refusal":
                    details = getattr(final, "stop_details", None)
                    why = getattr(details, "explanation", None) or "no explanation given"
                    raise BackendRefusal(f"The model declined this {req.task} request ({why}).")
                return
            except anthropic.BadRequestError as e:
                # Older accounts/platforms may not accept server-side fallbacks; retry once without.
                if with_fallbacks and not yielded and "fallback" in str(e).lower():
                    with_fallbacks = False
                    continue
                raise BackendError(f"Claude API rejected the request: {e}") from e
            except anthropic.AuthenticationError as e:
                raise BackendError("Claude API authentication failed. Set ANTHROPIC_API_KEY.") from e
            except anthropic.RateLimitError as e:
                raise BackendError("Claude API rate limit reached; try again shortly.") from e
            except anthropic.APIStatusError as e:
                raise BackendError(f"Claude API error {e.status_code}: {e}") from e
            except anthropic.APIConnectionError as e:
                raise BackendError(f"Could not reach the Claude API: {e}") from e
