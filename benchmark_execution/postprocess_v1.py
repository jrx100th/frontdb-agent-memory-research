from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import benchmark_execution.postprocess_resume as v0pp


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--jobs-dir", type=Path, required=True)
    ap.add_argument("--preflight", type=Path, required=True)
    ap.add_argument("--task", required=True)
    ap.add_argument("--task-order", type=int, required=True)
    ap.add_argument("--condition", required=True)
    ap.add_argument("--condition-position", type=int, required=True)
    ap.add_argument("--run-id", required=True)
    ap.add_argument("--output-dir", type=Path, required=True)
    ap.add_argument("--runtime-image-ledger", type=Path, default=None)
    ap.add_argument("--v1-manifest", type=Path, required=True)
    ap.add_argument("--v1-manifest-hash", type=Path, required=True)
    args = ap.parse_args()

    v1_sha = sha(args.v1_manifest)
    if args.v1_manifest_hash.read_text(encoding="utf-8").strip() != v1_sha:
        raise RuntimeError("V1_POSTPROCESS_MANIFEST_HASH_INVALID")
    v1 = json.loads(args.v1_manifest.read_text(encoding="utf-8"))
    if v1.get("experiment_version") != "v1-environment-materialized-1":
        raise RuntimeError("V1_POSTPROCESS_EXPERIMENT_VERSION_INVALID")

    # Reuse the independently validated termination-safe reconciler while
    # binding this normalization call to v1 only. The v0 source file remains
    # byte-for-byte hard-bound to the v0 manifest for provenance replay.
    old = v0pp.MANIFEST_SHA
    try:
        v0pp.MANIFEST_SHA = v1_sha
        result = v0pp.normalize(
            jobs_dir=args.jobs_dir,
            preflight_path=args.preflight,
            task=args.task,
            task_order=args.task_order,
            condition=args.condition,
            condition_position=args.condition_position,
            run_id=args.run_id,
            output_dir=args.output_dir,
            runtime_image_ledger=args.runtime_image_ledger,
        )
    finally:
        v0pp.MANIFEST_SHA = old

    if result.get("experiment_manifest_sha256") != v1_sha:
        raise RuntimeError("V1_POSTPROCESS_RESULT_MANIFEST_INVALID")
    result["experiment_version"] = "v1-environment-materialized-1"
    result["output_path"] = f"results/v1/{args.task_order:02d}-{args.task}/{args.condition}/{args.run_id}/"
    preflight = json.loads(args.preflight.read_text(encoding="utf-8"))
    result["task_environment_bundle_sha256"] = preflight.get("task_environment_bundle_sha256")
    result["task_environment_service_identity"] = preflight.get("service_identity")
    (args.output_dir / "run_result.json").write_bytes(v0pp.canon(result))
    print(
        f"V1_RUN_EVIDENCE_NORMALIZED task={args.task} condition={args.condition} "
        f"success={result['success']} accounting={result['accounting_status']} attempts={result['provider_attempt_count']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
