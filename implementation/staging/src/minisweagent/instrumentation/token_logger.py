from __future__ import annotations
from dataclasses import asdict, dataclass
from typing import Any
import json

INVALID = "TOKEN_ACCOUNTING_INVALID"

@dataclass
class AttemptUsage:
    attempt_id: str
    retry_index: int
    request_id: str | None
    raw_usage: dict | None
    input_tokens: int | None
    output_tokens: int | None
    total_tokens: int | None
    cached_fields: dict | None
    reasoning_fields: dict | None
    accounting_status: str


def _as_dict(value: Any) -> dict | None:
    if value is None:
        return None
    if isinstance(value, dict):
        return value
    if hasattr(value, "model_dump"):
        try:
            return value.model_dump(mode="json")
        except TypeError:
            return value.model_dump()
    try:
        return dict(value)
    except Exception:
        return None


def extract_provider_usage(response: Any, *, attempt_id: str, retry_index: int, possibly_generated: bool = True) -> AttemptUsage:
    data = _as_dict(response) or {}
    usage = _as_dict(data.get("usage") if isinstance(data, dict) else None)
    request_id = data.get("id") if isinstance(data, dict) else None
    if not usage:
        return AttemptUsage(attempt_id, retry_index, request_id, None, None, None, None, None, None,
                            INVALID if possibly_generated else "NO_GENERATION")
    inp = usage.get("prompt_tokens", usage.get("input_tokens"))
    out = usage.get("completion_tokens", usage.get("output_tokens"))
    total = usage.get("total_tokens")
    cached = {k: v for k, v in usage.items() if "cache" in k.casefold()}
    reasoning = {k: v for k, v in usage.items() if "reason" in k.casefold()}
    if total is None and inp is not None and out is not None:
        total = inp + out
    valid = all(isinstance(v, int) and v >= 0 for v in (inp, out, total))
    return AttemptUsage(attempt_id, retry_index, request_id, usage, inp, out, total, cached or None, reasoning or None,
                        "OK" if valid else INVALID)

class TokenLogger:
    def __init__(self, path):
        self.path = path

    def log(self, usage: AttemptUsage) -> None:
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(json.dumps(asdict(usage), sort_keys=True, separators=(",", ":"), ensure_ascii=True) + "\n")
