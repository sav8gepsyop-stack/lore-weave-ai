"""Optional local backend using Hugging Face Transformers.

    pip install "lore-weave-ai[local]"
    LOREWEAVE_BACKEND=hf LOREWEAVE_HF_MODEL=Qwen/Qwen2.5-7B-Instruct loreweave serve

Any chat/instruct causal LM works. Smaller local models keep less of a long manuscript straight,
so the engine's ledger and consistency passes matter even more here.
"""

from __future__ import annotations

import asyncio
import os
import threading
from typing import AsyncIterator

from .base import Backend, BackendError, GenerationRequest

DEFAULT_HF_MODEL = "Qwen/Qwen2.5-7B-Instruct"


class HFBackend(Backend):
    name = "hf"

    def __init__(self, model_id: str | None = None, max_context_tokens: int | None = None):
        try:
            import torch  # noqa: F401
            import transformers  # noqa: F401
        except ImportError as e:
            raise BackendError(
                "The local backend needs extra packages: pip install 'lore-weave-ai[local]'"
            ) from e
        from transformers import AutoModelForCausalLM, AutoTokenizer

        self.model_id = model_id or os.environ.get("LOREWEAVE_HF_MODEL", DEFAULT_HF_MODEL)
        self.tokenizer = AutoTokenizer.from_pretrained(self.model_id)
        self.model = AutoModelForCausalLM.from_pretrained(self.model_id, torch_dtype="auto", device_map="auto")
        self.max_context_tokens = max_context_tokens or int(os.environ.get("LOREWEAVE_HF_CONTEXT", "32768"))
        self._lock = threading.Lock()  # one generation at a time per loaded model

    def describe(self) -> dict:
        return {"name": self.name, "model": self.model_id}

    def _build_inputs(self, req: GenerationRequest):
        messages = [{"role": "system", "content": req.system}, {"role": "user", "content": req.prompt}]
        if getattr(self.tokenizer, "chat_template", None):
            ids = self.tokenizer.apply_chat_template(messages, add_generation_prompt=True, return_tensors="pt")
        else:
            text = f"{req.system}\n\n### Instruction\n{req.prompt}\n\n### Response\n"
            ids = self.tokenizer(text, return_tensors="pt").input_ids
        # Keep the tail if the prompt is longer than the model can see (the bible sits first, the task last).
        budget = self.max_context_tokens - min(req.max_tokens, self.max_context_tokens // 2)
        if ids.shape[-1] > budget:
            ids = ids[:, -budget:]
        return ids.to(self.model.device)

    async def stream(self, req: GenerationRequest) -> AsyncIterator[str]:
        from transformers import TextIteratorStreamer

        input_ids = self._build_inputs(req)
        streamer = TextIteratorStreamer(self.tokenizer, skip_prompt=True, skip_special_tokens=True)
        max_new = min(req.max_tokens, 8192)

        def run():
            with self._lock:
                self.model.generate(
                    input_ids=input_ids,
                    streamer=streamer,
                    max_new_tokens=max_new,
                    do_sample=True,
                    temperature=0.8 if not req.expect_json else 0.3,
                    top_p=0.95,
                    repetition_penalty=1.05,
                )

        thread = threading.Thread(target=run, daemon=True)
        thread.start()
        loop = asyncio.get_running_loop()
        it = iter(streamer)
        sentinel = object()
        while True:
            chunk = await loop.run_in_executor(None, next, it, sentinel)
            if chunk is sentinel:
                break
            if chunk:
                yield chunk
        thread.join(timeout=1)
