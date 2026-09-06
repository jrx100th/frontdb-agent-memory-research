from __future__ import annotations

import argparse
from datetime import datetime
import hashlib
import json
from pathlib import Path
import shutil

MANIFEST_SHA = "88a98a4e191729b0d9a00afb40ade9c2985b3e4fa160034df58a4b01e83ebb4a"
BASELINE_SHA = "81b7e326f91e5efdee43cf11349294c088e2731e"
RUNNER_SHA = "ff6a1303acb865c0e0689a18eb7fceb7af4e0cdc"
UPSTREAM_SHA = "a83fcae82d2a08f0ee0c688f9d137b3566c097f8"
TB_SHA = "2b0442c3c583b710ca8da14c8e601b99f2f1f244"
ENV_PACKET_SHA = "26566fea65da18291160d2f45598942182d4edf23e1b95485734bc196a67945e"


def canon(obj) -> bytes:
    return (json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True) + "\n").encode("utf-8")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def parse_dt(value):
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def duration_seconds(start, finish):
    a, b = parse_dt(start), parse_dt(finish)
    if a is None or b is None:
        return None
    return max(0.0, (b - a).total_seconds())


def _harbor_task_name_matches(task_name: object, task: str) -> bool:
    """Accept only the frozen Harbor namespace or the bare task id."""
    return task_name == task or task_name == f"terminal-bench/{task}"


def find_trial_result(jobs_dir: Path, task: str) -> tuple[Path, dict]:
    matches = []
    for path in jobs_dir.rglob("result.json"):
        try:
            obj = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        if _harbor_task_name_matches(obj.get("task_name"), task) and obj.get("trial_name"):
            matches.append((path, obj))
    if len(matches) != 1:
        raise RuntimeError(f"EXPECTED_ONE_TRIAL_RESULT_FOUND_{len(matches)}")
    return matches[0]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--jobs-dir", type=Path, required=True)
    ap.add_argument("--preflight", type=Path, required=True)
    ap.add_argument("--task", required=True)
    ap.add_argument("--task-order", type=int, required=True)
    ap.add_argument("--condition", choices=list("ABCD"), required=True)
    ap.add_argument("--condition-position", type=int, required=True)
    ap.add_argument("--run-id", required=True)
    ap.add_argument("--output-dir", type=Path, required=True)
    args = ap.parse_args()

    preflight = json.loads(args.preflight.read_text(encoding="utf-8"))
    if preflight.get("status") != "PASS" or preflight.get("manifest_sha256") != MANIFEST_SHA:
        raise RuntimeError("PREFLIGHT_EVIDENCE_INVALID")
    if preflight.get("task_id") != args.task or preflight.get("condition") != args.condition:
        raise RuntimeError("PREFLIGHT_RUN_IDENTITY_MISMATCH")

    result_path, trial = find_trial_result(args.jobs_dir, args.task)
    trial_dir = result_path.parent
    agent_dir = trial_dir / "agent"
    verifier_dir = trial_dir / "verifier"
    measurement_path = agent_dir / "measurement.json"
    trajectory_path = agent_dir / "mini-swe-agent.trajectory.json"
    attempt_path = agent_dir / "provider_attempts.json"

    measurement = json.loads(measurement_path.read_text(encoding="utf-8")) if measurement_path.exists() else None
    attempts_packet = json.loads(attempt_path.read_text(encoding="utf-8")) if attempt_path.exists() else None
    verifier_result = trial.get("verifier_result")
    rewards = verifier_result.get("rewards") if isinstance(verifier_result, dict) else None
    evaluator_reward = rewards.get("reward") if isinstance(rewards, dict) else None
    success = evaluator_reward == 1 or evaluator_reward == 1.0

    if measurement is not None:
        if measurement.get("manifest_sha256") != MANIFEST_SHA:
            raise RuntimeError("RUN_MANIFEST_IDENTITY_MISMATCH")
        if measurement.get("task_id") != args.task or measurement.get("condition") != args.condition:
            raise RuntimeError("RUN_TASK_CONDITION_IDENTITY_MISMATCH")
        if measurement.get("run_id") != args.run_id:
            raise RuntimeError("RUN_ID_MISMATCH")

    accounting = (measurement or {}).get("provider_accounting") or {}
    accounting_status = accounting.get("accounting_status") or "TOKEN_ACCOUNTING_INVALID"
    attempts = (measurement or {}).get("provider_attempts") or []
    if attempts_packet is not None and attempts_packet.get("attempts") != attempts:
        raise RuntimeError("ATTEMPT_LEDGER_MISMATCH")

    failure_class = None
    if (measurement or {}).get("implementation_defect"):
        failure_class = "BENCHMARK_INVALID_IMPLEMENTATION_DEFECT"
    elif accounting_status == "TOKEN_ACCOUNTING_INVALID":
        failure_class = "TOKEN_ACCOUNTING_INVALID"
    elif trial.get("exception_info"):
        failure_class = "AGENT_OR_HARNESS_EXCEPTION"
    elif verifier_result is None:
        failure_class = "VERIFIER_RESULT_MISSING"
    elif not success:
        failure_class = "TASK_FAILURE"

    memory_calls = (measurement or {}).get("memory_call_snapshots") or []
    retrieval_latency_total = sum(float(x.get("retrieval_latency_seconds") or 0.0) for x in memory_calls)
    memory_final = (measurement or {}).get("memory_final_telemetry")

    normalized = {
        "schema_version": 1,
        "experiment_manifest_sha256": MANIFEST_SHA,
        "run_id": args.run_id,
        "benchmark_repository": "harbor-framework/terminal-bench",
        "benchmark_tag": "v3.0.0",
        "benchmark_revision": TB_SHA,
        "task_id": args.task,
        "task_order": args.task_order,
        "condition": args.condition,
        "condition_order_position": args.condition_position,
        "success": success,
        "evaluator_result": verifier_result,
        "evaluator_reward": evaluator_reward,
        "failure_class": failure_class,
        "accounting_status": accounting_status,
        "provider_input_tokens": accounting.get("input_tokens"),
        "provider_output_tokens": accounting.get("output_tokens"),
        "provider_total_tokens": accounting.get("total_provider_tokens"),
        "provider_cached_tokens": accounting.get("cached_tokens"),
        "provider_reasoning_tokens": accounting.get("reasoning_tokens"),
        "provider_attempts_raw_and_normalized": attempts,
        "provider_attempt_count": len(attempts),
        "turns": (measurement or {}).get("turns"),
        "runtime_seconds": duration_seconds(trial.get("started_at"), trial.get("finished_at")),
        "agent_runtime_seconds": (measurement or {}).get("runtime_seconds_agent"),
        "provider_input_or_context_tokens_per_turn_if_available": [
            a.get("input_tokens") for a in attempts if a.get("input_tokens") is not None
        ],
        "local_context_packing_estimates_separately_labeled": [
            x.get("serialized_memory_local_units") for x in memory_calls
        ] if args.condition in {"C", "D"} else [],
        "baseline_sha": BASELINE_SHA,
        "condition_runner_sha": RUNNER_SHA,
        "upstream_sha": UPSTREAM_SHA,
        "mini_swe_agent_version": "2.4.6",
        "prompt_template_identity": "mini.yaml@8b72f71f8092ae805ec43221dbeaeefc2340cd3e",
        "tool_schema_identity": "actions_toolcall.py@8209113c4a1663d34468be6106b5661ec9e0be62",
        "model_route": "z-ai/glm-5.3-free",
        "provider_transport": "TokenRouter-compatible OpenAI chat-completions via LiteLLM 1.99.0",
        "provider_kwargs_canonical": (measurement or {}).get("provider_kwargs_canonical"),
        "provider_preflight_calls": (measurement or {}).get("provider_preflight_calls"),
        "task_environment_image_digest": (measurement or {}).get("runtime_image_digest"),
        "task_environment_identity_sha256": preflight.get("task_environment_identity_sha256"),
        "environment_packet_sha256": ENV_PACKET_SHA,
        "task_start_state_identity": (measurement or {}).get("start_state_identity"),
        "environment_run_identifier": trial.get("id"),
        "harbor_trial_name": trial.get("trial_name"),
        "harbor_trial_uri": trial.get("trial_uri"),
        "harbor_exception_info": trial.get("exception_info"),
        "output_path": f"results/v0/{args.task_order:02d}-{args.task}/{args.condition}/{args.run_id}/",
        "rank_policy": (measurement or {}).get("rank_policy"),
        "retrieval_latency_per_call_seconds": [x.get("retrieval_latency_seconds") for x in memory_calls],
        "retrieval_latency_total_seconds": retrieval_latency_total if args.condition in {"C", "D"} else None,
        "memory_db_reads": (memory_final or {}).get("db_reads") if memory_final else None,
        "memory_db_writes": (memory_final or {}).get("db_writes") if memory_final else None,
        "memory_record_count": (measurement or {}).get("memory_record_count"),
        "retrieval_candidate_counts": [x.get("candidate_count") for x in memory_calls],
        "retrieval_selected_counts": [x.get("selected_count") for x in memory_calls],
        "serialized_memory_local_units": [x.get("serialized_memory_local_units") for x in memory_calls],
        "fingerprint_file_count": len(set((memory_final or {}).get("fingerprint_files") or [])) if memory_final else None,
        "memory_db_size_bytes": (memory_final or {}).get("db_size_bytes") if memory_final else None,
        "memory_call_snapshots": memory_calls,
        "confirmation_policy": (measurement or {}).get("confirmation_policy"),
        "preflight_status": preflight.get("status"),
    }

    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "run_result.json").write_bytes(canon(normalized))
    shutil.copy2(args.preflight, args.output_dir / "preflight.json")
    shutil.copy2(result_path, args.output_dir / "harbor_trial_result.json")
    if measurement_path.exists():
        shutil.copy2(measurement_path, args.output_dir / "measurement.json")
    if trajectory_path.exists():
        shutil.copy2(trajectory_path, args.output_dir / "mini-swe-agent.trajectory.json")
    if attempt_path.exists():
        shutil.copy2(attempt_path, args.output_dir / "provider_attempts.json")
    if verifier_dir.exists():
        shutil.copytree(verifier_dir, args.output_dir / "verifier", dirs_exist_ok=True)

    hashes = []
    for path in sorted(p for p in args.output_dir.rglob("*") if p.is_file()):
        if path.name == "SHA256SUMS.txt":
            continue
        hashes.append(f"{sha256(path)}  {path.relative_to(args.output_dir).as_posix()}")
    (args.output_dir / "SHA256SUMS.txt").write_text("\n".join(hashes) + "\n", encoding="utf-8")
    print(
        f"RUN_EVIDENCE_NORMALIZED task={args.task} condition={args.condition} "
        f"success={success} accounting={accounting_status}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
