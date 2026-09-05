from __future__ import annotations

import importlib.metadata
import json
import os
import re
from pathlib import Path
from typing import Any

os.environ.setdefault("MSWEA_SILENT_STARTUP", "1")

ARTIFACT_DIR = Path("integration_artifacts")
OUT = ARTIFACT_DIR / "provider-adapter-diagnostic.json"
MODEL_EXPECTED = "z-ai/glm-5.3-free"
BASE_EXPECTED = "https://api.tokenrouter.com/v1"


def _redact(text: str, *, key: str, base: str) -> str:
    text = text.replace(key, "[REDACTED_API_KEY]") if key else text
    # Defensive redaction for bearer-like material even if it does not equal the supplied key.
    text = re.sub(r"(?i)(authorization\s*[:=]\s*bearer\s+)[^\s,;]+", r"\1[REDACTED]", text)
    text = re.sub(r"(?i)(api[_-]?key\s*[:=]\s*)[^\s,;]+", r"\1[REDACTED]", text)
    return text


def _dumpish(obj: Any) -> dict[str, Any]:
    if obj is None:
        return {}
    if isinstance(obj, dict):
        return obj
    if hasattr(obj, "model_dump"):
        try:
            value = obj.model_dump(mode="json")
        except TypeError:
            value = obj.model_dump()
        if isinstance(value, dict):
            return value
    if hasattr(obj, "dict"):
        value = obj.dict()
        if isinstance(value, dict):
            return value
    return {}


def _usage_summary(response: Any) -> dict[str, Any]:
    data = _dumpish(response)
    usage_obj = data.get("usage")
    if usage_obj is None and hasattr(response, "usage"):
        usage_obj = getattr(response, "usage")
    usage = _dumpish(usage_obj)
    prompt_details = _dumpish(usage.get("prompt_tokens_details") or usage.get("input_tokens_details"))
    completion_details = _dumpish(usage.get("completion_tokens_details") or usage.get("output_tokens_details"))
    return {
        "usage_present": bool(usage),
        "usage_field_names": sorted(usage.keys()),
        "input_tokens": usage.get("prompt_tokens", usage.get("input_tokens")),
        "output_tokens": usage.get("completion_tokens", usage.get("output_tokens")),
        "total_tokens": usage.get("total_tokens"),
        "cached_detail_shape": sorted(prompt_details.keys()),
        "cached_tokens": prompt_details.get("cached_tokens"),
        "reasoning_detail_shape": sorted(completion_details.keys()),
        "reasoning_tokens": completion_details.get("reasoning_tokens"),
    }


def _response_model(response: Any) -> Any:
    if hasattr(response, "model"):
        return getattr(response, "model")
    return _dumpish(response).get("model")


def _install_httpx_outbound_probe(target: dict[str, Any]):
    import httpx

    original_send = httpx.Client.send

    def wrapped_send(self, request, *args, **kwargs):
        try:
            body = json.loads(request.content.decode("utf-8")) if request.content else {}
        except Exception:
            body = {}
        # Never capture headers/authentication material.
        target["request_seen"] = True
        target["outbound_model"] = body.get("model")
        target["outbound_stream"] = body.get("stream")
        target["request_path"] = request.url.path
        return original_send(self, request, *args, **kwargs)

    httpx.Client.send = wrapped_send
    return httpx, original_send


def _restore_httpx(httpx_module, original_send) -> None:
    httpx_module.Client.send = original_send


def main() -> None:
    ARTIFACT_DIR.mkdir(exist_ok=True)
    key = os.getenv("TOKENROUTER_API_KEY", "")
    base = os.getenv("TOKENROUTER_BASE_URL", "")
    route = os.getenv("TOKENROUTER_MODEL", "")
    result: dict[str, Any] = {
        "credential_presence": {
            "api_key_present": bool(key),
            "base_url_present": bool(base),
            "model_route_present": bool(route),
        },
        "expected_base_url_match": base.rstrip("/") == BASE_EXPECTED,
        "expected_model_route_match": route == MODEL_EXPECTED,
        "litellm_version": importlib.metadata.version("litellm"),
        "openai_version": importlib.metadata.version("openai"),
        "terminal_bench": "NOT_RUN",
    }
    if not all(result["credential_presence"].values()):
        result["status"] = "BLOCKED_NO_CREDENTIALS_OR_ROUTE"
        OUT.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
        print(json.dumps(result, sort_keys=True))
        raise SystemExit(2)
    if not result["expected_base_url_match"] or not result["expected_model_route_match"]:
        result["status"] = "BLOCKED_PROVIDER_ROUTE_CONFIGURATION_MISMATCH"
        OUT.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
        print(json.dumps(result, sort_keys=True))
        raise SystemExit(2)

    # TEST A: one direct OpenAI-compatible request, no SDK retries.
    from openai import OpenAI

    direct: dict[str, Any] = {"request_count": 1, "stream": False}
    try:
        client = OpenAI(api_key=key, base_url=base, max_retries=0, timeout=90.0)
        response = client.chat.completions.create(
            model=route,
            messages=[{"role": "user", "content": "Reply with exactly: provider_control_ok"}],
            stream=False,
        )
        direct.update(
            {
                "response_received": True,
                "response_model": _response_model(response),
                "usage": _usage_summary(response),
                "status": "PASS",
            }
        )
    except Exception as error:
        direct.update(
            {
                "response_received": False,
                "exception_type": type(error).__name__,
                "exception_message": _redact(str(error), key=key, base=base),
                "status": "FAIL",
            }
        )
        result["direct_openai_control"] = direct
        result["status"] = "BLOCKED_PROVIDER_ROUTE"
        serialized = json.dumps(result, indent=2, sort_keys=True)
        assert key not in serialized
        OUT.write_text(serialized, encoding="utf-8")
        print(json.dumps(result, sort_keys=True))
        raise SystemExit(3)
    result["direct_openai_control"] = direct

    # TEST B: current raw LiteLLM configuration, exactly one completion call.
    import litellm

    current: dict[str, Any] = {"stream": False}
    try:
        raw = litellm.completion(
            model=route,
            api_base=base,
            api_key=key,
            messages=[{"role": "user", "content": "Reply with exactly: provider_control_ok"}],
            stream=False,
        )
        current.update(
            {
                "response_received": True,
                "response_model": _response_model(raw),
                "usage": _usage_summary(raw),
                "status": "PASS",
            }
        )
    except Exception as error:
        current.update(
            {
                "response_received": False,
                "exception_type": type(error).__name__,
                "exception_message": _redact(str(error), key=key, base=base),
                "status": "FAIL",
            }
        )
    result["litellm_current_control"] = current

    # TEST C: explicit OpenAI provider selection while preserving provider-facing model string.
    outbound_c: dict[str, Any] = {}
    httpx_module, original_send = _install_httpx_outbound_probe(outbound_c)
    hinted: dict[str, Any] = {"custom_llm_provider": "openai", "stream": False}
    try:
        hinted_response = litellm.completion(
            model=route,
            custom_llm_provider="openai",
            api_base=base,
            api_key=key,
            messages=[{"role": "user", "content": "Reply with exactly: provider_control_ok"}],
            stream=False,
        )
        hinted.update(
            {
                "response_received": True,
                "response_model": _response_model(hinted_response),
                "usage": _usage_summary(hinted_response),
                "status": "PASS",
            }
        )
    except Exception as error:
        hinted.update(
            {
                "response_received": False,
                "exception_type": type(error).__name__,
                "exception_message": _redact(str(error), key=key, base=base),
                "status": "FAIL",
            }
        )
    finally:
        _restore_httpx(httpx_module, original_send)
    hinted["request_evidence"] = outbound_c
    hinted["outbound_model_exact"] = outbound_c.get("outbound_model") == MODEL_EXPECTED
    hinted["outbound_stream_false"] = outbound_c.get("outbound_stream") is False
    result["litellm_provider_hint_control"] = hinted

    if not hinted.get("response_received"):
        result["status"] = "BLOCKED_PROVIDER_ACCOUNTING_INVALID"
    elif not hinted["outbound_model_exact"]:
        result["status"] = "BLOCKED_PROVIDER_MODEL_REWRITE"
    else:
        # PHASE 2: one actual mini-SWE request shape using BASH_TOOL. We deliberately use
        # _query + the real attempt ledger/parser to prevent the retry wrapper from turning
        # a deterministic tool-compatibility diagnostic into ten provider requests.
        from minisweagent.exceptions import FormatError
        from minisweagent.models.litellm_model import LitellmModel

        tool_outbound: dict[str, Any] = {}
        httpx_module, original_send = _install_httpx_outbound_probe(tool_outbound)
        tool: dict[str, Any] = {"stream": False, "custom_llm_provider": "openai"}
        tool_model = LitellmModel(
            model_name=route,
            model_kwargs={
                "api_base": base,
                "api_key": key,
                "stream": False,
                "custom_llm_provider": "openai",
            },
            cost_tracking="ignore_errors",
        )
        tool_model.set_accounting_context(task_id="non-benchmark-provider-adapter-diagnostic", run_id="tool-call-control")
        record = tool_model.attempt_ledger.begin(retry_index=0, retry=False, retry_reason=None)
        try:
            tool_response = tool_model._query(
                tool_model._prepare_messages_for_api(
                    [
                        {"role": "system", "content": "This is a non-benchmark provider tool-call compatibility probe."},
                        {"role": "user", "content": "Call the bash tool exactly once with command: printf tool_call_control"},
                    ]
                )
            )
        except Exception as error:
            tool_model.attempt_ledger.record_provider_error(record.attempt_id, error)
            tool.update(
                {
                    "response_received": False,
                    "exception_type": type(error).__name__,
                    "exception_message": _redact(str(error), key=key, base=base),
                    "parse_or_tool_call_status": "NOT_REACHED",
                    "status": "FAIL",
                }
            )
        else:
            # Same accounting boundary as the authoritative integration: response first,
            # then action parsing. This is the property under test.
            tool_model.attempt_ledger.record_response(record.attempt_id, tool_response)
            tool.update(
                {
                    "response_received": True,
                    "response_model": _response_model(tool_response),
                    "usage": _usage_summary(tool_response),
                }
            )
            try:
                actions = tool_model._parse_actions(tool_response)
            except FormatError as error:
                tool_model.attempt_ledger.record_parse(record.attempt_id, False)
                tool["parse_or_tool_call_status"] = "FORMAT_ERROR"
                tool["parse_exception_message"] = _redact(str(error), key=key, base=base)
                tool["status"] = "FAIL"
            except Exception as error:
                tool_model.attempt_ledger.record_parse(record.attempt_id, False)
                tool["parse_or_tool_call_status"] = type(error).__name__
                tool["parse_exception_message"] = _redact(str(error), key=key, base=base)
                tool["status"] = "FAIL"
            else:
                tool_model.attempt_ledger.record_parse(record.attempt_id, True)
                tool["parse_or_tool_call_status"] = "PASS"
                tool["action_count"] = len(actions)
                tool["tool_name_valid"] = bool(actions) and all("command" in action for action in actions)
                tool["status"] = "PASS" if tool["tool_name_valid"] else "FAIL"
        finally:
            _restore_httpx(httpx_module, original_send)
        tool["request_evidence"] = tool_outbound
        tool["outbound_model_exact"] = tool_outbound.get("outbound_model") == MODEL_EXPECTED
        tool["outbound_stream_false"] = tool_outbound.get("outbound_stream") is False
        tool["attempts"] = tool_model.attempt_ledger.snapshot()
        tool["aggregate"] = tool_model.attempt_ledger.aggregate()
        result["tool_call_control"] = tool
        if tool.get("response_received") and tool.get("status") == "PASS" and tool["outbound_model_exact"]:
            result["status"] = "PROVIDER_HINT_AND_TOOL_CALL_COMPATIBLE"
        else:
            result["status"] = "TOOL_CALL_COMPATIBILITY_BLOCKER"

    serialized = json.dumps(result, indent=2, sort_keys=True)
    assert key not in serialized, "secret must not be serialized"
    OUT.write_text(serialized, encoding="utf-8")
    # Print only the already-sanitized artifact, never environment/header values.
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
