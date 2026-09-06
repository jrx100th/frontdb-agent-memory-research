from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import sqlite3
import sys
import time
import traceback

from minisweagent.agents import get_agent
from minisweagent.agents.utils.prompt_user import prompt_session
from minisweagent.config import get_config_from_spec
from minisweagent.environments import get_environment
from minisweagent.models import get_model
from minisweagent.memory.integration import MemoryRuntime

EXPECTED_MANIFEST_SHA256 = "88a98a4e191729b0d9a00afb40ade9c2985b3e4fa160034df58a4b01e83ebb4a"
EXPECTED_PROVIDER_BASE_SHA256 = "f76d53a0e94e3837023542b48c5b2226b21c3ad37cae446272a2743b7579ee5d"
EXPECTED_ENV_PACKET_SHA256 = "26566fea65da18291160d2f45598942182d4edf23e1b95485734bc196a67945e"
EXPECTED_ROUTE = "z-ai/glm-5.3-free"
TASK_IDENTITIES = {
    "atrx-vep-crispr": "7cfea578937dbd2103305419aea6391953838e40d33e87b04ce711b4f3432079",
    "batched-eval-parity": "b6331007ec8e73d94acf2ae4814b4a53c91013d22aaa972715d9a6c36e7f7ff4",
    "cad-model": "c3bc1a255c8d5218de9c535b0f8b5b2958f60f6bbe8f51c60fceb98c9d8ff8fb",
    "cargo-flight-dispatch": "05a43221d49b447a0456b121e3a598074fd4d244ebbde5cc3d9092a8e6148035",
    "coq-block-bound": "f4e6770542653e512f9e118d102b0f095f5bfc34fc3e4d870a89812949d49b6d",
    "cumulative-layout-shift": "904c8c50a5c32081ec5001fc6242383ebf008feec7f4a91324faa8c857c50c9a",
    "data-anonymization": "97befd9b118867c57e12b62ee557e3ef651e1e5a9cb7b2be8a0c0ad6c8c9a4c6",
    "live-database-cutover": "0b0815f5dd50877a8ee736508dedc760f45de405adcd96b0209bf8f3467dc82d",
    "music-harmony": "47f348720c5973a7f67b701c8c177215bf1e73e0a1f97f1fef2606a824d36619",
    "uefi-bootkit": "d6c0a9df1bc1fed093665c4d96153fac062b4412a2044b0ea229164a505cc701",
    "production-planning": "2e84c2b95fac213e9a49cfc00fa23253732a550d4deba5aa6d8ba4d459aaf069",
    "wdm-design": "90cdc72b1a2239d90bf0827a2f30d730ffdacfd63496dc864353c636929228ae",
}

LOGS = Path("/logs/agent")
TRAJECTORY = LOGS / "mini-swe-agent.trajectory.json"
ATTEMPTS = LOGS / "provider_attempts.json"
MEASUREMENT = LOGS / "measurement.json"


def _require(name: str) -> str:
    value = os.environ.get(name)
    if value is None or value == "":
        raise RuntimeError(f"CONFIGURATION_INVALID_MISSING_{name}")
    return value


def _provider_preflight(model, counters: dict) -> None:
    base = _require("TOKENROUTER_BASE_URL")
    if hashlib.sha256(base.encode("utf-8")).hexdigest() != EXPECTED_PROVIDER_BASE_SHA256:
        raise RuntimeError("CONFIGURATION_INVALID_PROVIDER_BASE")
    if _require("FROZEN_MANIFEST_SHA256") != EXPECTED_MANIFEST_SHA256:
        raise RuntimeError("MANIFEST_IDENTITY_FAILURE")
    if _require("FROZEN_ENV_PACKET_SHA256") != EXPECTED_ENV_PACKET_SHA256:
        raise RuntimeError("INFRASTRUCTURE_INVALID_ENV_PACKET")
    if _require("FROZEN_STATIC_ENV_PREFLIGHT") != "PASS":
        raise RuntimeError("INFRASTRUCTURE_INVALID_STATIC_PREFLIGHT")
    task_id = _require("FROZEN_TASK_ID")
    expected_task_identity = TASK_IDENTITIES.get(task_id)
    if expected_task_identity is None or _require("FROZEN_TASK_IDENTITY_SHA256") != expected_task_identity:
        raise RuntimeError("INFRASTRUCTURE_INVALID_TASK_IDENTITY")
    if _require("FROZEN_RUNTIME_IMAGE_ID") != _require("FROZEN_RUNTIME_IMAGE_EXPECTED_ID"):
        raise RuntimeError("INFRASTRUCTURE_INVALID_RUNTIME_IMAGE_DRIFT")
    if _require("FROZEN_MODEL_ROUTE") != EXPECTED_ROUTE or model.config.model_name != EXPECTED_ROUTE:
        raise RuntimeError("CONFIGURATION_INVALID_MODEL_ROUTE")
    kwargs = model.config.model_kwargs
    if kwargs.get("api_base") != base:
        raise RuntimeError("CONFIGURATION_INVALID_PROVIDER_BASE_MODEL_KWARG")
    if kwargs.get("stream") is not False or kwargs.get("custom_llm_provider") != "openai" or kwargs.get("drop_params") is not True:
        raise RuntimeError("CONFIGURATION_INVALID_PROVIDER_KWARGS")
    if not _require("OPENAI_API_KEY"):
        raise RuntimeError("CONFIGURATION_INVALID_PROVIDER_KEY")
    counters["provider_preflight_calls"] += 1


def _sum_nested_key(value, needle: str) -> int:
    if isinstance(value, dict):
        total = 0
        for key, item in value.items():
            if needle in str(key).casefold() and type(item) is int and item >= 0:
                total += item
            else:
                total += _sum_nested_key(item, needle)
        return total
    if isinstance(value, (list, tuple)):
        return sum(_sum_nested_key(x, needle) for x in value)
    return 0


def _attempt_totals(attempts: list[dict]) -> dict:
    invalid = any(a.get("accounting_status") not in {"COUNTED", "ZERO_CONFIRMED"} for a in attempts)
    counted = [a for a in attempts if a.get("accounting_status") == "COUNTED"]
    input_tokens = sum(int(a.get("input_tokens") or 0) for a in counted)
    output_tokens = sum(int(a.get("output_tokens") or 0) for a in counted)
    total_tokens = sum(int(a.get("total_tokens") or 0) for a in counted)
    cached_tokens = sum(_sum_nested_key(a.get("cached_fields"), "cached_tokens") for a in counted)
    reasoning_tokens = sum(_sum_nested_key(a.get("reasoning_fields"), "reasoning_tokens") for a in counted)
    return {
        "accounting_status": "TOKEN_ACCOUNTING_INVALID" if invalid else "COUNTED",
        "input_tokens": None if invalid else input_tokens,
        "output_tokens": None if invalid else output_tokens,
        "total_provider_tokens": None if invalid else total_tokens,
        "cached_tokens": None if invalid else cached_tokens,
        "reasoning_tokens": None if invalid else reasoning_tokens,
        "attempt_count": len(attempts),
    }


def _memory_record_count(db_path: Path | None) -> int | None:
    if db_path is None or not db_path.exists():
        return 0 if db_path is not None else None
    with sqlite3.connect(db_path) as con:
        return int(con.execute("SELECT count(*) FROM memories").fetchone()[0])


def main() -> int:
    LOGS.mkdir(parents=True, exist_ok=True)
    task_path = Path(sys.argv[1])
    task = task_path.read_text(encoding="utf-8")
    task_id = _require("FROZEN_TASK_ID")
    condition = _require("FROZEN_CONDITION")
    run_id = _require("FROZEN_RUN_ID")
    if condition not in {"A", "B", "C", "D"}:
        raise RuntimeError("CONFIGURATION_INVALID_CONDITION")

    # API key is environment-only. The frozen base is an explicit model kwarg per T10.
    base = _require("TOKENROUTER_BASE_URL")
    os.environ["OPENAI_API_KEY"] = _require("TOKENROUTER_API_KEY")
    os.environ["MSWEA_ATTEMPT_LOG_PATH"] = str(ATTEMPTS)
    os.environ["MSWEA_COST_TRACKING"] = "ignore_errors"

    config = get_config_from_spec("mini")
    config["model"]["model_name"] = EXPECTED_ROUTE
    config["model"]["cost_tracking"] = "ignore_errors"
    config["model"]["model_kwargs"] = dict(config["model"].get("model_kwargs") or {})
    config["model"]["model_kwargs"].update(
        {"api_base": base, "stream": False, "custom_llm_provider": "openai"}
    )
    config["agent"]["benchmark_condition"] = condition
    config["agent"]["memory_db_path"] = str(LOGS / "memory.sqlite")
    config["agent"]["memory_workspace"] = os.getcwd()
    config["agent"]["memory_task_id"] = task_id
    config["agent"]["output_path"] = str(TRAJECTORY)

    model = get_model(config=config["model"])
    if hasattr(model, "set_accounting_context"):
        model.set_accounting_context(task_id=task_id, run_id=run_id)

    counters = {"provider_preflight_calls": 0}
    original_low_level_query = model._query

    def guarded_query(messages, **kwargs):
        _provider_preflight(model, counters)
        return original_low_level_query(messages, **kwargs)

    model._query = guarded_query

    memory_call_snapshots: list[dict] = []
    original_build_provider_messages = MemoryRuntime.build_provider_messages

    def measured_build_provider_messages(runtime, native_messages, *, current_step):
        result = original_build_provider_messages(runtime, native_messages, current_step=current_step)
        snapshot = runtime.telemetry_snapshot()
        memory_call_snapshots.append(
            {
                "call_index": len(memory_call_snapshots) + 1,
                "current_step": current_step,
                "retrieval_latency_seconds": snapshot.get("retrieval_latency_seconds"),
                "candidate_count": len(snapshot.get("candidate_ids") or []),
                "selected_count": len(snapshot.get("selected_ids") or []),
                "serialized_memory_local_units": snapshot.get("message_local_units"),
                "db_reads": snapshot.get("db_reads"),
                "db_writes": snapshot.get("db_writes"),
                "fingerprint_count": len(set(snapshot.get("fingerprint_files") or [])),
                "db_size_bytes": snapshot.get("db_size_bytes"),
            }
        )
        return result

    MemoryRuntime.build_provider_messages = measured_build_provider_messages

    # Deterministic external confirmation input while preserving mode=confirm.
    original_prompt = prompt_session.prompt
    prompt_session.prompt = lambda *args, **kwargs: ""

    env = get_environment(config["environment"], default_type="local")
    agent = get_agent(model, env, config["agent"], default_type="interactive")
    # Validate the effective Pydantic/default-resolved policy, not raw YAML key presence.
    if getattr(agent.config, "mode", None) != "confirm" or getattr(agent.config, "confirm_exit", None) is not True:
        raise RuntimeError("CONFIGURATION_INVALID_CONFIRM_MODE")
    started = time.perf_counter()
    error = None
    exit_code = 0
    try:
        agent.run(task)
    except BaseException as exc:
        error = {"type": type(exc).__name__, "message": str(exc), "traceback": traceback.format_exc()}
        exit_code = 1
    finally:
        prompt_session.prompt = original_prompt
        MemoryRuntime.build_provider_messages = original_build_provider_messages

    elapsed = time.perf_counter() - started
    attempts = model.attempt_ledger.snapshot() if hasattr(model, "attempt_ledger") else []
    accounting = _attempt_totals(attempts)
    memory_runtime = getattr(agent, "_memory_runtime", None)
    memory_final = memory_runtime.telemetry_snapshot() if memory_runtime is not None else None
    db_path = Path(memory_runtime.db_path) if memory_runtime is not None else None
    memory_record_count = _memory_record_count(db_path)

    side_effect_dbs = sorted(str(p) for p in LOGS.glob("memory*.sqlite"))
    implementation_defect = None
    if condition in {"A", "B"} and side_effect_dbs:
        implementation_defect = "A_B_MEMORY_DB_SIDE_EFFECT"
        exit_code = 2
    if condition in {"C", "D"} and memory_runtime is None:
        implementation_defect = "C_D_MEMORY_RUNTIME_MISSING"
        exit_code = 2

    measurement = {
        "schema_version": 1,
        "manifest_sha256": EXPECTED_MANIFEST_SHA256,
        "task_id": task_id,
        "task_order": int(_require("FROZEN_TASK_ORDER")),
        "condition": condition,
        "condition_order_position": int(_require("FROZEN_CONDITION_POSITION")),
        "run_id": run_id,
        "model_route": EXPECTED_ROUTE,
        "provider_transport": "TokenRouter-compatible OpenAI chat-completions via LiteLLM",
        "provider_kwargs_canonical": {
            "api_base_sha256": EXPECTED_PROVIDER_BASE_SHA256,
            "stream": False,
            "custom_llm_provider": "openai",
            "drop_params": True,
        },
        "provider_preflight_calls": counters["provider_preflight_calls"],
        "provider_attempts": attempts,
        "provider_accounting": accounting,
        "turns": getattr(agent, "n_calls", None),
        "runtime_seconds_agent": elapsed,
        "runtime_image_digest": _require("FROZEN_RUNTIME_IMAGE_ID"),
        "start_state_identity": {
            "task_environment_identity_sha256": _require("FROZEN_TASK_IDENTITY_SHA256"),
            "runtime_image_digest": _require("FROZEN_RUNTIME_IMAGE_ID"),
            "environment_packet_sha256": EXPECTED_ENV_PACKET_SHA256,
        },
        "confirmation_policy": _require("FROZEN_CONFIRMATION_POLICY"),
        "rank_policy": "structured" if condition == "C" else ("lexical" if condition == "D" else None),
        "memory_call_snapshots": memory_call_snapshots,
        "memory_final_telemetry": memory_final,
        "memory_record_count": memory_record_count,
        "memory_db_path": str(db_path) if db_path is not None else None,
        "memory_db_exists": bool(db_path and db_path.exists()),
        "memory_db_side_effect_paths": side_effect_dbs,
        "implementation_defect": implementation_defect,
        "agent_exception": error,
        "exit_code": exit_code,
    }
    MEASUREMENT.write_text(
        json.dumps(measurement, sort_keys=True, separators=(",", ":"), ensure_ascii=True) + "\n",
        encoding="utf-8",
    )

    if implementation_defect:
        raise RuntimeError("BENCHMARK_INVALID_IMPLEMENTATION_DEFECT:" + implementation_defect)
    if error is not None:
        # Preserve measurement first, then let Harbor record the real agent failure.
        raise RuntimeError(f"AGENT_EXECUTION_FAILED:{error['type']}:{error['message']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
