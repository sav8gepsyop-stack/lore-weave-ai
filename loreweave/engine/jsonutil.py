from __future__ import annotations

import json
import re

_FENCE = re.compile(r"^```(?:json)?\s*|\s*```$", re.MULTILINE)


class JSONParseError(ValueError):
    pass


def parse_json_object(text: str) -> dict:
    """Parse the first JSON object in a model response, tolerating fences and stray prose."""
    t = _FENCE.sub("", text.strip())
    try:
        val = json.loads(t)
        if isinstance(val, dict):
            return val
    except json.JSONDecodeError:
        pass
    start, end = t.find("{"), t.rfind("}")
    if start == -1 or end <= start:
        raise JSONParseError("no JSON object found in model output")
    chunk = t[start : end + 1]
    try:
        return json.loads(chunk)
    except json.JSONDecodeError:
        # Common local-model slip: trailing commas.
        cleaned = re.sub(r",\s*([}\]])", r"\1", chunk)
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError as e:
            raise JSONParseError(str(e)) from e
