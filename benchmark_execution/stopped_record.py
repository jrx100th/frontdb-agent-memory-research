from __future__ import annotations

import argparse
import json
from pathlib import Path

MANIFEST_SHA = "88a98a4e191729b0d9a00afb40ade9c2985b3e4fa160034df58a4b01e83ebb4a"
TB_SHA = "2b0442c3c583b710ca8da14c8e601b99f2f1f244"


def canon(obj) -> bytes:
    return (json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True) + "\n").encode()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--task", required=True)
    ap.add_argument("--task-order", type=int, required=True)
    ap.add_argument("--condition", required=True)
    ap.add_argument("--condition-position", type=int, required=True)
    ap.add_argument("--run-id", required=True)
    ap.add_argument("--failure-class", required=True)
    ap.add_argument("--phase", required=True)
    ap.add_argument("--message", default="")
    ap.add_argument("--output-dir", type=Path, required=True)
    args = ap.parse_args()
    obj = {
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
        "success": False,
        "evaluator_result": None,
        "evaluator_reward": None,
        "failure_class": args.failure_class,
        "failure_phase": args.phase,
        "failure_message": args.message[:2000],
        "accounting_status": "TOKEN_ACCOUNTING_INVALID" if args.phase != "PRE_PROVIDER_PREFLIGHT" else "ZERO_CONFIRMED",
        "provider_input_tokens": None,
        "provider_output_tokens": None,
        "provider_total_tokens": None,
        "provider_cached_tokens": None,
        "provider_reasoning_tokens": None,
        "provider_attempts_raw_and_normalized": [],
        "provider_attempt_count": 0,
        "turns": 0,
        "runtime_seconds": None,
        "baseline_sha": "81b7e326f91e5efdee43cf11349294c088e2731e",
        "condition_runner_sha": "ff6a1303acb865c0e0689a18eb7fceb7af4e0cdc",
        "upstream_sha": "a83fcae82d2a08f0ee0c688f9d137b3566c097f8",
        "mini_swe_agent_version": "2.4.6",
        "model_route": "z-ai/glm-5.3-free",
        "provider_transport": "TokenRouter-compatible OpenAI chat-completions via LiteLLM 1.99.0",
        "output_path": f"results/v0/{args.task_order:02d}-{args.task}/{args.condition}/{args.run_id}/",
        "stopped_record": True,
    }
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "run_result.json").write_bytes(canon(obj))
    (args.output_dir / "STOPPED.txt").write_text(f"{args.failure_class}\n{args.phase}\n{args.message}\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
