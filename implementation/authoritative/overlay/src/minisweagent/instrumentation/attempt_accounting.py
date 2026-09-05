from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any
import json
import os

COUNTED = "COUNTED"
ZERO_CONFIRMED = "ZERO_CONFIRMED"
UNKNOWN = "UNKNOWN"
INVALID = "TOKEN_ACCOUNTING_INVALID"


@dataclass
class ProviderAttempt:
    attempt_id: str
    task_id: str | None
    run_id: str | None
    attempt_number: int
    retry_index: int
    retry: bool
    retry_reason: str | None
    request_id: str | None = None
    raw_usage: dict | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None
    total_tokens: int | None = None
    cached_fields: dict | None = None
    reasoning_fields: dict | None = None
    request_generated: bool = True
    response_received: bool = False
    parse_success: bool | None = None
    provider_error: str | None = None
    accounting_status: str = UNKNOWN


def _as_dict(value: Any) -> dict | None:
    if value is None:
        return None
    if isinstance(value, dict):
        return value
    if hasattr(value, "model_dump"):
        try:
            return value.model_dump(mode="json")
        except TypeError:
            try:
                return value.model_dump()
            except Exception:
                return None
        except Exception:
            return None
    try:
        return dict(value)
    except Exception:
        return None


def _contains_key(value: Any, needle: str) -> bool:
    if isinstance(value, dict):
        return any(needle in str(k).casefold() or _contains_key(v, needle) for k, v in value.items())
    if isinstance(value, (list, tuple)):
        return any(_contains_key(v, needle) for v in value)
    return False


def _audit_fields(usage: dict, needle: str) -> dict | None:
    found = {
        k: v
        for k, v in usage.items()
        if needle in str(k).casefold() or _contains_key(v, needle)
    }
    return found or None


def _token_int(value: Any) -> bool:
    return type(value) is int and value >= 0


def normalize_response_usage(response: Any) -> dict[str, Any]:
    data = _as_dict(response) or {}
    usage_obj = data.get("usage") if isinstance(data, dict) else None
    if usage_obj is None and hasattr(response, "usage"):
        usage_obj = getattr(response, "usage")
    usage = _as_dict(usage_obj)
    request_id = data.get("id") if isinstance(data, dict) else None
    if request_id is None and hasattr(response, "id"):
        request_id = getattr(response, "id")
    if not usage:
        return {
            "request_id": request_id,
            "raw_usage": None,
            "input_tokens": None,
            "output_tokens": None,
            "total_tokens": None,
            "cached_fields": None,
            "reasoning_fields": None,
            "accounting_status": INVALID,
        }
    inp = usage.get("prompt_tokens", usage.get("input_tokens"))
    out = usage.get("completion_tokens", usage.get("output_tokens"))
    total = usage.get("total_tokens")
    valid = _token_int(inp) and _token_int(out) and _token_int(total) and total == inp + out
    return {
        "request_id": request_id,
        "raw_usage": usage,
        "input_tokens": inp if _token_int(inp) else None,
        "output_tokens": out if _token_int(out) else None,
        "total_tokens": total if _token_int(total) else None,
        "cached_fields": _audit_fields(usage, "cache"),
        "reasoning_fields": _audit_fields(usage, "reason"),
        "accounting_status": COUNTED if valid else INVALID,
    }


class AttemptLedger:
    """Fail-closed provider-attempt accounting.

    The ledger records provider-reported usage only. It never calls a tokenizer,
    estimates usage, subtracts cache tokens, or adds reasoning tokens to totals.
    """

    def __init__(self, path: str | Path | None = None):
        self.path = Path(path) if path else None
        self.records: list[ProviderAttempt] = []
        self._counter = 0
        self.task_id: str | None = None
        self.run_id: str | None = None

    @classmethod
    def from_env(cls) -> "AttemptLedger":
        return cls(os.getenv("MSWEA_ATTEMPT_LOG_PATH") or None)

    def set_context(self, *, task_id: str | None = None, run_id: str | None = None) -> None:
        self.task_id = task_id
        self.run_id = run_id

    def begin(self, *, retry_index: int, retry: bool, retry_reason: str | None = None) -> ProviderAttempt:
        self._counter += 1
        prefix = self.run_id or self.task_id or "run"
        record = ProviderAttempt(
            attempt_id=f"{prefix}:{self._counter}",
            task_id=self.task_id,
            run_id=self.run_id,
            attempt_number=self._counter,
            retry_index=retry_index,
            retry=retry,
            retry_reason=retry_reason,
        )
        self.records.append(record)
        self._persist()
        return record

    def _find(self, attempt_id: str) -> ProviderAttempt:
        for record in reversed(self.records):
            if record.attempt_id == attempt_id:
                return record
        raise KeyError(attempt_id)

    def record_response(self, attempt_id: str, response: Any) -> None:
        record = self._find(attempt_id)
        normalized = normalize_response_usage(response)
        record.response_received = True
        record.request_id = normalized["request_id"]
        record.raw_usage = normalized["raw_usage"]
        record.input_tokens = normalized["input_tokens"]
        record.output_tokens = normalized["output_tokens"]
        record.total_tokens = normalized["total_tokens"]
        record.cached_fields = normalized["cached_fields"]
        record.reasoning_fields = normalized["reasoning_fields"]
        record.accounting_status = normalized["accounting_status"]
        self._persist()

    def record_provider_error(self, attempt_id: str, error: BaseException) -> None:
        record = self._find(attempt_id)
        record.provider_error = type(error).__name__
        if getattr(error, "mswea_zero_generation_confirmed", False) is True:
            record.accounting_status = ZERO_CONFIRMED
        else:
            record.accounting_status = UNKNOWN
        self._persist()

    def record_parse(self, attempt_id: str | None, success: bool) -> None:
        if attempt_id is None:
            return
        self._find(attempt_id).parse_success = bool(success)
        self._persist()

    def snapshot(self) -> list[dict]:
        return [asdict(record) for record in self.records]

    def aggregate(self) -> dict[str, Any]:
        total = 0
        invalid = False
        for record in self.records:
            if record.accounting_status == COUNTED:
                if record.total_tokens is None:
                    invalid = True
                else:
                    total += record.total_tokens
            elif record.accounting_status == ZERO_CONFIRMED:
                continue
            else:
                invalid = True
        return {
            "accounting_status": INVALID if invalid else COUNTED,
            "total_provider_tokens": None if invalid else total,
            "attempt_count": len(self.records),
        }

    def _persist(self) -> None:
        if self.path is None:
            return
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"attempts": self.snapshot(), "aggregate": self.aggregate()}
        self.path.write_text(
            json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True) + "\n",
            encoding="utf-8",
        )
