from __future__ import annotations

import json
from types import SimpleNamespace

import pytest
from tenacity import Retrying, retry_if_exception_type, stop_after_attempt, wait_none

from minisweagent.exceptions import FormatError
from minisweagent.instrumentation.attempt_accounting import COUNTED, INVALID, UNKNOWN, ZERO_CONFIRMED
from minisweagent.models.litellm_model import LitellmModel
import minisweagent.models.litellm_model as lm


class Function:
    def __init__(self, name="bash", arguments='{"command":"printf ok"}'):
        self.name = name
        self.arguments = arguments


class ToolCall:
    def __init__(self, tool_id="tc", function=None):
        self.id = tool_id
        self.function = function or Function()
        self.type = "function"


class Message:
    def __init__(self, tool_calls):
        self.tool_calls = tool_calls
        self.role = "assistant"
        self.content = None

    def model_dump(self):
        calls = None
        if self.tool_calls is not None:
            calls = [
                {
                    "id": c.id,
                    "type": c.type,
                    "function": {"name": c.function.name, "arguments": c.function.arguments},
                }
                for c in self.tool_calls
            ]
        return {"role": self.role, "content": self.content, "tool_calls": calls}


class Response:
    def __init__(self, *, usage=None, tool_calls=None, request_id="req"):
        self.id = request_id
        self.usage = usage
        self.choices = [SimpleNamespace(message=Message(tool_calls), finish_reason="tool_calls")]

    def model_dump(self, mode=None):
        return {
            "id": self.id,
            "usage": self.usage,
            "choices": [
                {
                    "finish_reason": self.choices[0].finish_reason,
                    "message": self.choices[0].message.model_dump(),
                }
            ],
        }


def make_model():
    model = LitellmModel(model_name="openai/test", model_kwargs={"stream": False}, cost_tracking="ignore_errors")
    model._calculate_cost = lambda response: {"cost": 0.0}
    model.set_accounting_context(task_id="task", run_id="run")
    return model


def valid_usage(prompt=10, completion=3, **extra):
    return {"prompt_tokens": prompt, "completion_tokens": completion, "total_tokens": prompt + completion, **extra}


def test_valid_usage_captured_before_parse_and_audits_cache_reasoning(monkeypatch):
    model = make_model()
    response = Response(
        usage=valid_usage(
            prompt_tokens_details={"cached_tokens": 4},
            completion_tokens_details={"reasoning_tokens": 2},
        ),
        tool_calls=[ToolCall()],
    )
    monkeypatch.setattr(model, "_query", lambda *a, **k: response)
    model.query([{"role": "user", "content": "x"}])
    record = model.attempt_ledger.records[-1]
    assert record.accounting_status == COUNTED
    assert record.input_tokens == 10 and record.output_tokens == 3 and record.total_tokens == 13
    assert record.cached_fields is not None
    assert record.reasoning_fields is not None
    assert record.parse_success is True
    assert model.attempt_ledger.aggregate()["total_provider_tokens"] == 13


def test_parse_failure_keeps_usage_and_next_success_aggregates_both(monkeypatch):
    model = make_model()
    responses = iter(
        [
            Response(usage=valid_usage(10, 2), tool_calls=[], request_id="r1"),
            Response(usage=valid_usage(11, 3), tool_calls=[ToolCall("tc2")], request_id="r2"),
        ]
    )
    monkeypatch.setattr(model, "_query", lambda *a, **k: next(responses))
    with pytest.raises(FormatError):
        model.query([{"role": "user", "content": "x"}])
    first = model.attempt_ledger.records[0]
    assert first.accounting_status == COUNTED and first.total_tokens == 12 and first.parse_success is False
    model.query([{"role": "user", "content": "retry"}])
    second = model.attempt_ledger.records[1]
    assert second.accounting_status == COUNTED and second.total_tokens == 14 and second.parse_success is True
    assert second.retry is True and second.retry_reason == "action_parse_failure"
    assert model.attempt_ledger.aggregate() == {
        "accounting_status": COUNTED,
        "total_provider_tokens": 26,
        "attempt_count": 2,
    }


def _no_wait_retry(*, logger, abort_exceptions):
    return Retrying(
        reraise=True,
        stop=stop_after_attempt(2),
        wait=wait_none(),
        retry=retry_if_exception_type(Exception),
    )


class ZeroConfirmedError(RuntimeError):
    mswea_zero_generation_confirmed = True


def test_provider_error_zero_confirmed_then_retry_success(monkeypatch):
    model = make_model()
    calls = {"n": 0}

    def q(*a, **k):
        calls["n"] += 1
        if calls["n"] == 1:
            raise ZeroConfirmedError("not logged")
        return Response(usage=valid_usage(5, 1), tool_calls=[ToolCall()], request_id="ok")

    monkeypatch.setattr(lm, "retry", _no_wait_retry)
    monkeypatch.setattr(model, "_query", q)
    model.query([{"role": "user", "content": "x"}])
    first, second = model.attempt_ledger.records
    assert first.accounting_status == ZERO_CONFIRMED
    assert first.provider_error == "ZeroConfirmedError"
    assert second.retry is True and second.retry_reason == "provider_retry"
    assert second.accounting_status == COUNTED
    assert model.attempt_ledger.aggregate()["total_provider_tokens"] == 6


def test_provider_error_after_possible_generation_fails_closed(monkeypatch):
    model = make_model()
    calls = {"n": 0}

    def q(*a, **k):
        calls["n"] += 1
        if calls["n"] == 1:
            raise RuntimeError("possible generation")
        return Response(usage=valid_usage(5, 1), tool_calls=[ToolCall()], request_id="ok")

    monkeypatch.setattr(lm, "retry", _no_wait_retry)
    monkeypatch.setattr(model, "_query", q)
    model.query([{"role": "user", "content": "x"}])
    first = model.attempt_ledger.records[0]
    assert first.accounting_status == UNKNOWN
    aggregate = model.attempt_ledger.aggregate()
    assert aggregate["accounting_status"] == INVALID
    assert aggregate["total_provider_tokens"] is None


def test_missing_usage_is_token_accounting_invalid(monkeypatch):
    model = make_model()
    monkeypatch.setattr(model, "_query", lambda *a, **k: Response(usage=None, tool_calls=[ToolCall()]))
    model.query([{"role": "user", "content": "x"}])
    record = model.attempt_ledger.records[-1]
    assert record.response_received is True
    assert record.accounting_status == INVALID
    assert model.attempt_ledger.aggregate()["accounting_status"] == INVALID


def test_malformed_or_nonadditive_usage_is_invalid(monkeypatch):
    model = make_model()
    bad = {"prompt_tokens": 10, "completion_tokens": 3, "total_tokens": 99}
    monkeypatch.setattr(model, "_query", lambda *a, **k: Response(usage=bad, tool_calls=[ToolCall()]))
    model.query([{"role": "user", "content": "x"}])
    record = model.attempt_ledger.records[-1]
    assert record.raw_usage == bad
    assert record.accounting_status == INVALID
    assert model.attempt_ledger.aggregate()["total_provider_tokens"] is None


def test_serialize_preserves_all_attempts_for_audit(monkeypatch):
    model = make_model()
    monkeypatch.setattr(model, "_query", lambda *a, **k: Response(usage=valid_usage(2, 1), tool_calls=[ToolCall()]))
    model.query([{"role": "user", "content": "x"}])
    data = model.serialize()
    assert len(data["info"]["provider_attempts"]) == 1
    assert data["info"]["provider_accounting"]["total_provider_tokens"] == 3
    assert "raw_usage" in data["info"]["provider_attempts"][0]
