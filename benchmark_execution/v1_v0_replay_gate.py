from __future__ import annotations

import argparse
import json
from pathlib import Path

from benchmark_execution import postprocess_resume as termination_safe

EXPECTED_RUNTIME_IMAGE = "sha256:f72bb3459aca556dfc0202acc1f74f3b10d558bc25af2318b7dd496a90be1638"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--artifact-root", type=Path, required=True)
    ap.add_argument("--output-dir", type=Path, required=True)
    args = ap.parse_args()

    root = args.artifact_root.resolve()
    checkpoint = root / "checkpoints/1-atrx-vep-crispr/A/34021511221-1-1-A"
    runtime_ledger = root / "runtime-image-1-atrx-vep-crispr.txt"
    if not checkpoint.is_dir() or not runtime_ledger.is_file():
        raise RuntimeError("V1_G9_V0_ARTIFACT_LAYOUT_INVALID")
    if runtime_ledger.read_text(encoding="utf-8").strip() != EXPECTED_RUNTIME_IMAGE:
        raise RuntimeError("V1_G9_V0_RUNTIME_IMAGE_CHANGED")

    result = termination_safe.normalize(
        jobs_dir=checkpoint / "harbor-jobs",
        preflight_path=checkpoint / "preflight-source.json",
        task="atrx-vep-crispr",
        task_order=1,
        condition="A",
        condition_position=1,
        run_id="34021511221-1-1-A",
        output_dir=args.output_dir,
        runtime_image_ledger=runtime_ledger,
    )

    attempts = result.get("provider_attempts_raw_and_normalized") or []
    counted = sum(1 for x in attempts if x.get("accounting_status") == "COUNTED")
    unknown = sum(1 for x in attempts if x.get("accounting_status") == "UNKNOWN")
    required = {
        "task_id": "atrx-vep-crispr",
        "condition": "A",
        "success": False,
        "evaluator_reward": 0,
        "provider_attempt_count": 56,
        "accounting_status": "TOKEN_ACCOUNTING_INVALID",
        "provider_total_tokens": None,
        "provider_known_counted_tokens": 938612,
        "agent_exception_type": "AgentTimeoutError",
        "task_environment_image_digest": EXPECTED_RUNTIME_IMAGE,
    }
    for key, expected in required.items():
        if result.get(key) != expected:
            raise RuntimeError(f"V1_G9_V0_REPLAY_CHANGED:{key}:{result.get(key)!r}!={expected!r}")
    if counted != 42 or unknown != 14 or len(attempts) != 56:
        raise RuntimeError(f"V1_G9_ATTEMPT_SPLIT_CHANGED:counted={counted}:unknown={unknown}:total={len(attempts)}")

    result["v1_acceptance_gate"] = "G9"
    result["counted_attempts"] = counted
    result["unknown_attempts"] = unknown
    result["provider_calls_during_replay"] = 0
    (args.output_dir / "run_result.json").write_bytes(termination_safe.canon(result))
    print("V0_ARTIFACT_REPLAY=PASS")
    print("V0_REPLAY_ATTEMPTS=56 COUNTED=42 UNKNOWN=14")
    print("V0_REPLAY_KNOWN_SUBTOTAL=938612 PROVIDER_TOTAL=null")
    print("V0_REPLAY_EXCEPTION=AgentTimeoutError")
    print("PROVIDER_CALLS=0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
