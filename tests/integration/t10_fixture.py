from __future__ import annotations

import copy
import json
import os
from pathlib import Path
import sqlite3
import sys
import types

os.environ.setdefault("MSWEA_SILENT_STARTUP", "1")
os.environ.setdefault("MSWEA_GLOBAL_CONFIG_DIR", "/tmp/mswea-t10-config")

from minisweagent.agents.default import DefaultAgent
from minisweagent.models.litellm_model import LitellmModel
from minisweagent.models.utils.actions_toolcall import BASH_TOOL
import minisweagent.models.litellm_model as litellm_module


class FakeFunction:
    def __init__(self, name: str, arguments: str):
        self.name = name
        self.arguments = arguments


class FakeToolCall:
    def __init__(self, tool_id: str, command: str):
        self.id = tool_id
        self.type = "function"
        self.function = FakeFunction("bash", json.dumps({"command": command}, separators=(",", ":")))


class FakeMessage:
    def __init__(self, *, tool_id: str, command: str):
        self.role = "assistant"
        self.content = None
        self.tool_calls = [FakeToolCall(tool_id, command)]

    def model_dump(self):
        return {
            "role": self.role,
            "content": self.content,
            "tool_calls": [
                {
                    "id": call.id,
                    "type": call.type,
                    "function": {"name": call.function.name, "arguments": call.function.arguments},
                }
                for call in self.tool_calls
            ],
        }


class FakeChoice:
    def __init__(self):
        self.message = FakeMessage(tool_id="tc-response", command="printf response")
        self.finish_reason = "tool_calls"


class FakeResponse:
    def __init__(self):
        self.id = "req-t10"
        self.choices = [FakeChoice()]
        self.usage = {"prompt_tokens": 10, "completion_tokens": 3, "total_tokens": 13}

    def model_dump(self, mode=None):
        return {
            "id": self.id,
            "choices": [
                {
                    "finish_reason": self.choices[0].finish_reason,
                    "message": self.choices[0].message.model_dump(),
                }
            ],
            "usage": dict(self.usage),
        }


class FakeEnv:
    def get_template_vars(self):
        return {}

    def execute(self, action, cwd=""):
        return {"output": "ok", "returncode": 0}

    def serialize(self):
        return {"info": {"config": {"environment": "fake"}}}


def canonical(value) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def main() -> None:
    out_path = Path(sys.argv[1])
    patched = os.getenv("PATCHED") == "1"
    captured: dict = {}

    def fake_completion(**kwargs):
        captured.update(copy.deepcopy(kwargs))
        return FakeResponse()

    litellm_module.litellm.completion = fake_completion

    sqlite_calls = 0
    original_connect = sqlite3.connect

    def counting_connect(*args, **kwargs):
        nonlocal sqlite_calls
        sqlite_calls += 1
        return original_connect(*args, **kwargs)

    sqlite3.connect = counting_connect

    sentinel_counts = {
        "runtime_init": 0,
        "db_writes": 0,
        "fingerprints": 0,
        "retrieval": 0,
        "context": 0,
        "synthetic": 0,
    }
    if patched:
        sentinel = types.ModuleType("minisweagent.memory.integration")

        class SentinelRuntime:
            def __init__(self, *args, **kwargs):
                sentinel_counts["runtime_init"] += 1

            def start_task(self, *args, **kwargs):
                pass

            def build_provider_messages(self, messages, **kwargs):
                sentinel_counts["context"] += 1
                sentinel_counts["retrieval"] += 1
                return messages

            def ingest_step(self, *args, **kwargs):
                sentinel_counts["db_writes"] += 1

        sentinel.MemoryRuntime = SentinelRuntime
        sys.modules["minisweagent.memory.integration"] = sentinel

    model = LitellmModel(
        model_name="openai/test-model",
        model_kwargs={
            "api_base": "https://provider.invalid/v1",
            "temperature": 0.2,
            "top_p": 0.9,
            "seed": 12345,
            "max_tokens": 321,
            "stream": False,
        },
        cost_tracking="ignore_errors",
    )
    model._calculate_cost = lambda response: {"cost": 0.0}

    agent_kwargs = {
        "system_template": "SYSTEM {{ task }}",
        "instance_template": "TASK {{ task }}",
        "step_limit": 0,
        "cost_limit": 0.0,
        "wall_time_limit_seconds": 0,
        "max_consecutive_format_errors": 3,
    }
    if patched:
        agent_kwargs["memory_enabled"] = False

    agent = DefaultAgent(model=model, env=FakeEnv(), **agent_kwargs)
    agent.extra_template_vars = {"task": "deterministic-task"}
    agent.messages = []
    agent.add_messages(
        model.format_message(role="system", content=agent._render_template(agent.config.system_template)),
        model.format_message(role="user", content=agent._render_template(agent.config.instance_template)),
    )
    agent.add_messages(
        {
            "role": "assistant",
            "content": None,
            "tool_calls": [
                {
                    "id": "tc-history",
                    "type": "function",
                    "function": {"name": "bash", "arguments": '{"command":"printf history"}'},
                }
            ],
            "extra": {"actions": [{"command": "printf history", "tool_call_id": "tc-history"}]},
        },
        {
            "role": "tool",
            "tool_call_id": "tc-history",
            "content": "<returncode>0</returncode>\n<output>history</output>",
            "extra": {"returncode": 0, "raw_output": "history"},
        },
    )
    agent.query()

    provider_config = {
        "model_name": model.config.model_name,
        "model_kwargs": model.config.model_kwargs,
        "set_cache_control": model.config.set_cache_control,
        "cost_tracking": model.config.cost_tracking,
    }
    memory_synthetic = sum(
        1
        for message in captured.get("messages", [])
        if message.get("role") == "user"
        and str(message.get("content", "")).startswith("HISTORICAL_MEMORY_DATA_V1")
    )
    result = {
        "request": captured,
        "canonical_request": canonical(captured),
        "provider_config": provider_config,
        "canonical_provider_config": canonical(provider_config),
        "tool_schema": BASH_TOOL,
        "canonical_tool_schema": canonical(BASH_TOOL),
        "memory_side_effects": {
            **sentinel_counts,
            "sqlite_connect_calls": sqlite_calls,
            "synthetic_messages_in_request": memory_synthetic,
        },
    }
    out_path.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")


if __name__ == "__main__":
    main()
