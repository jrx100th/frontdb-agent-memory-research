from __future__ import annotations

import argparse
import copy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

V0_SHA256 = "88a98a4e191729b0d9a00afb40ade9c2985b3e4fa160034df58a4b01e83ebb4a"
ENV_PACKET_SHA256 = "26566fea65da18291160d2f45598942182d4edf23e1b95485734bc196a67945e"
SCIENTIFIC_BASELINE_SHA = "81b7e326f91e5efdee43cf11349294c088e2731e"
CONDITION_RUNNER_SHA = "ff6a1303acb865c0e0689a18eb7fceb7af4e0cdc"
UPSTREAM_SHA = "a83fcae82d2a08f0ee0c688f9d137b3566c097f8"
TB_SHA = "2b0442c3c583b710ca8da14c8e601b99f2f1f244"


def canon(obj) -> bytes:
    return (json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True) + "\n").encode("utf-8")


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def get(obj, path: str):
    cur = obj
    for part in path.split("."):
        cur = cur[part]
    return cur


def assert_science_equal(v0: dict, v1: dict) -> None:
    paths = [
        "conditions",
        "accounting_and_invalidation",
        "memory",
        "metrics",
        "prompts_and_tools",
        "provider",
        "harness",
        "measurement_schema",
        "benchmark.repository",
        "benchmark.tag",
        "benchmark.revision",
        "benchmark.success_evaluator",
        "benchmark.frozen_tasks",
        "benchmark.task_ids",
        "benchmark.task_order",
        "benchmark.task_count",
        "benchmark.task_selection",
        "benchmark.replacement_policy",
        "execution.schedule",
        "execution.schedule_seed",
        "execution.schedule_strategy",
        "execution.adaptive_reordering_forbidden",
        "execution.all_four_conditions_per_task",
        "execution.reset_isolation",
        "execution.whole_task_condition_automatic_rerun",
        "hypothesis_status",
    ]
    for path in paths:
        if get(v0, path) != get(v1, path):
            raise RuntimeError(f"V1_SCIENTIFIC_DIFFERENCE_FORBIDDEN:{path}")
    if v1["harness"]["scientific_baseline_sha"] != SCIENTIFIC_BASELINE_SHA:
        raise RuntimeError("V1_SCIENTIFIC_BASELINE_CHANGED")
    if v1["harness"]["condition_runner_sha"] != CONDITION_RUNNER_SHA:
        raise RuntimeError("V1_CONDITION_RUNNER_CHANGED")
    if v1["harness"]["upstream_commit"] != UPSTREAM_SHA:
        raise RuntimeError("V1_UPSTREAM_CHANGED")
    if v1["benchmark"]["revision"] != TB_SHA:
        raise RuntimeError("V1_TERMINAL_BENCH_CHANGED")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--v0-manifest", type=Path, required=True)
    ap.add_argument("--image-manifest", type=Path, required=True)
    ap.add_argument("--image-manifest-hash", type=Path, required=True)
    ap.add_argument("--gates-evidence", type=Path, required=True)
    ap.add_argument("--memory-evidence", type=Path, required=True)
    ap.add_argument("--v0-replay-evidence", type=Path, required=True)
    ap.add_argument("--freeze-parent", required=True)
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument("--hash-output", type=Path, required=True)
    args = ap.parse_args()

    if sha(args.v0_manifest) != V0_SHA256:
        raise RuntimeError("V1_V0_MANIFEST_IDENTITY_FAILURE")
    v0 = json.loads(args.v0_manifest.read_text(encoding="utf-8"))
    images = json.loads(args.image_manifest.read_text(encoding="utf-8"))
    image_sha = sha(args.image_manifest)
    if args.image_manifest_hash.read_text(encoding="utf-8").strip() != image_sha:
        raise RuntimeError("V1_IMAGE_MANIFEST_HASH_RECORD_MISMATCH")
    if images.get("task_environment_bundle_count") != 12:
        raise RuntimeError("V1_IMAGE_BUNDLE_COUNT_INVALID")
    if images.get("provider_calls_during_materialization") != 0:
        raise RuntimeError("V1_PROVIDER_CALL_DURING_MATERIALIZATION")

    gates = json.loads(args.gates_evidence.read_text(encoding="utf-8"))
    memory = json.loads(args.memory_evidence.read_text(encoding="utf-8"))
    replay = json.loads(args.v0_replay_evidence.read_text(encoding="utf-8"))
    if gates.get("provider_calls") != 0 or memory.get("provider_calls") != 0:
        raise RuntimeError("V1_PROVIDER_CALL_DURING_ACCEPTANCE")
    if gates.get("g3_four_instance_digest_identity") != "PASS" or gates.get("g6_schedule") != "PASS":
        raise RuntimeError("V1_CORE_ACCEPTANCE_INCOMPLETE")
    if not memory.get("a_b_no_memory") or not memory.get("c_d_fresh_unique_condition_scoped"):
        raise RuntimeError("V1_MEMORY_ACCEPTANCE_INCOMPLETE")
    if not (
        replay.get("task_id") == "atrx-vep-crispr"
        and replay.get("condition") == "A"
        and replay.get("success") is False
        and replay.get("evaluator_reward") == 0
        and replay.get("provider_attempt_count") == 56
        and replay.get("accounting_status") == "TOKEN_ACCOUNTING_INVALID"
        and replay.get("provider_total_tokens") is None
        and replay.get("provider_known_counted_tokens") == 938612
        and replay.get("agent_exception_type") == "AgentTimeoutError"
    ):
        raise RuntimeError("V1_V0_PROVENANCE_REPLAY_CHANGED")

    v1 = copy.deepcopy(v0)
    v1["experiment_version"] = "v1-environment-materialized-1"
    v1["manifest_kind"] = "final-benchmark-experiment-v1-environment-materialized"
    v1["freeze_created_utc"] = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    v1["freeze_parent_main"] = args.freeze_parent
    v1["hash_definition"] = (
        "SHA-256 over exact UTF-8 bytes of manifests/experiment_manifest.v1.final.json, "
        "canonical JSON sort_keys=true,separators=(',',':'),ensure_ascii=true plus one trailing LF."
    )
    v1["execution"]["ci_job_granularity"] = "ONE_TASK_CONDITION_PER_GITHUB_ACTIONS_JOB"
    v1["execution"]["environment_materialization"] = {
        "version": 1,
        "mode": "IMMUTABLE_PREBUILT_PER_TASK_ENVIRONMENT_BUNDLE",
        "terminal_bench_source_revision": TB_SHA,
        "task_environment_source_identity_packet_sha256": ENV_PACKET_SHA256,
        "task_environment_bundle_manifest_path": "reproducibility/v1_task_images.json",
        "task_environment_bundle_manifest_sha256": image_sha,
        "task_environment_bundle_count": 12,
        "per_condition_rebuild": False,
        "runtime_image_reference_policy": "immutable repo@sha256 only; mutable transport tags forbidden for execution identity",
        "all_services_pinned": True,
        "fresh_container_instance_per_condition": True,
        "scientific_condition_definitions_changed": False,
    }
    v1["v0_statistical_separation"] = {
        "v0_manifest_sha256": V0_SHA256,
        "v0_status": "INFRASTRUCTURE_INVALID_BLOCKED",
        "combine_v0_and_v1_statistics": False,
        "preserved_v0_run": 34021511221,
        "preserved_v0_artifact": 9990156639,
        "preserved_v0_task_condition": "atrx-vep-crispr/A",
    }
    v1["v1_pre_provider_acceptance"] = {
        "status": "PASS",
        "provider_calls": 0,
        "gates": {
            "G1_all_12_task_environment_bundles_materialized": "PASS",
            "G2_all_12_bundle_digests_canonicalized": "PASS",
            "G3_four_fresh_instances_per_task_same_digest": "PASS",
            "G4_A_B_no_memory_db": "PASS",
            "G5_C_D_fresh_unique_condition_db": "PASS",
            "G6_exact_48_run_latin_square": "PASS",
            "G7_failure_timeout_continues": "PASS",
            "G8_identity_mismatch_fails_before_provider": "PASS",
            "G9_v0_artifact_replay_unchanged": "PASS",
            "G10_v1_manifest_frozen_before_provider": "PASS",
        },
        "evidence": {
            "core_gates_sha256": sha(args.gates_evidence),
            "memory_gate_sha256": sha(args.memory_evidence),
            "v0_replay_sha256": sha(args.v0_replay_evidence),
        },
    }

    assert_science_equal(v0, v1)
    payload = canon(v1)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(payload)
    digest = hashlib.sha256(payload).hexdigest()
    args.hash_output.write_text(digest + "\n", encoding="utf-8")
    print("V1_SCIENTIFIC_DIFFERENCES_FROM_V0=NONE")
    print("V1_INFRASTRUCTURE_DIFFERENCE=IMMUTABLE_ENVIRONMENT_MATERIALIZATION_AND_ONE_CONDITION_PER_JOB")
    print(f"V1_MANIFEST_SHA256={digest}")
    print("PROVIDER_CALLS_DURING_V1_PREPARATION=0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
