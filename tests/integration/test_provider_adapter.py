from __future__ import annotations

import json
from types import SimpleNamespace

import litellm
import pytest

from minisweagent.exceptions import FormatError
from minisweagent.instrumentation.attempt_accounting import COUNTED
from minisweagent.models.litellm_model import LitellmModel
import minisweagent.models.litellm_model as lm


ROUTE = "z-ai/glm-5.3-free"
BASE = "https://api.tokenrouter.com/v1"


class _Function:
    name = "bash"
    arguments = '{"command":"printf ok"}'


class _ToolCall:
    id = "tc"
    type = "function"
    function = _Function()


class _Message:
    def __init__(self, tool_calls):
        self.tool_calls = tool_calls
        self.role = "assistant"
        self.content = None

    def model_dump(self):
        calls = None
        if self.tool_calls is not None:
            calls = [
                {
                    "id": call.id,
                    "type": call.type,
                    "function": {"name": call.function.name, "arguments": call.function.arguments},
                }
                for call in self.tool_calls
            ]
        return {"role": "assistant", "content": None, "tool_calls": calls}


class _Response:
    def __init__(self, *, tool_calls):
        self.id = "provider-adapter-test"
        self.usage = {
            "prompt_tokens": 11,
            "completion_tokens": 4,
            "total_tokens": 15,
            "prompt_tokens_details": {"cached_tokens": 0},
            "completion_tokens_details": {"reasoning_tokens": 2},
        }
        self.choices = [SimpleNamespace(message=_Message(tool_calls), finish_reason="tool_calls")]

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


def _model() -> LitellmModel:
    model = LitellmModel(
        model_name=ROUTE,
        model_kwargs={
            "api_base": BASE,
            "stream": False,
            "custom_llm_provider": "openai",
        },
        cost_tracking="ignore_errors",
    )
    model._calculate_cost = lambda response: {"cost": 0.0}
    model.set_accounting_context(task_id="provider-adapter-test", run_id="provider-adapter-test")
    return model


def test_raw_tokenrouter_route_reproduces_litellm_provider_inference_failure():
    with pytest.raises(litellm.exceptions.BadRequestError):
        litellm.get_llm_provider(model=ROUTE)


def test_explicit_openai_hint_preserves_route_base_and_nonstreaming(monkeypatch):
    seen = {}

    def fake_completion(**kwargs):
        seen.update(kwargs)
        return _Response(tool_calls=[_ToolCall()])

    monkeypatch.setattr(lm.litellm, "completion", fake_completion)
    response = _model()._query([{"role": "user", "content": "x"}])
    assert response.id == "provider-adapter-test"
    assert seen["model"] == ROUTE
    assert seen["api_base"] == BASE
    assert seen["stream"] is False
    assert seen["custom_llm_provider"] == "openai"
    assert "api_key" not in seen


def test_provider_hint_accounting_captures_response_before_parse(monkeypatch):
    model = _model()
    monkeypatch.setattr(model, "_query", lambda *args, **kwargs: _Response(tool_calls=[]))
    with pytest.raises(FormatError):
        model.query([{"role": "user", "content": "x"}])
    record = model.attempt_ledger.records[-1]
    assert record.response_received is True
    assert record.accounting_status == COUNTED
    assert record.input_tokens == 11
    assert record.output_tokens == 4
    assert record.total_tokens == 15
    assert record.parse_success is False
    assert record.cached_fields is not None
    assert record.reasoning_fields is not None


def test_tokenrouter_secret_is_environment_only_and_not_serialized(monkeypatch):
    secret = "unit-test-tokenrouter-secret-do-not-log"
    monkeypatch.setenv("OPENAI_API_KEY", secret)
    model = _model()
    serialized = json.dumps(model.serialize(), sort_keys=True)
    assert secret not in serialized
    assert "api_key" not in serialized.lower()
    assert model.config.model_kwargs == {
        "api_base": BASE,
        "stream": False,
        "custom_llm_provider": "openai",
    }


def test_provider_adapter_does_not_change_model_identity():
    model = _model()
    assert model.config.model_name == ROUTE
    assert model.config.model_kwargs["custom_llm_provider"] == "openai"
    assert model.config.model_kwargs["api_base"] == BASE
    assert model.config.model_kwargs["stream"] is False
