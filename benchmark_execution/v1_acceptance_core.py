from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory

from benchmark_execution.completion_marker import build_completion_record
from benchmark_execution.resume_control import must_stop_after_condition
from benchmark_execution.v1_identity import assert_main_runtime_identity, assert_service_references

TASKS = [
    (1, "atrx-vep-crispr", "ABCD"),
    (2, "batched-eval-parity", "BCDA"),
    (3, "cad-model", "CDAB"),
    (4, "cargo-flight-dispatch", "DABC"),
    (5, "coq-block-bound", "ABCD"),
    (6, "cumulative-layout-shift", "BCDA"),
    (7, "data-anonymization", "CDAB"),
    (8, "live-database-cutover", "DABC"),
    (9, "music-harmony", "ABCD"),
    (10, "uefi-bootkit", "BCDA"),
    (11, "production-planning", "CDAB"),
    (12, "wdm-design", "DABC"),
]
V0_MANIFEST_SHA = "88a98a4e191729b0d9a00afb40ade9c2985b3e4fa160034df58a4b01e83ebb4a"


def exact_schedule() -> list[dict]:
    out = []
    for order, task, conditions in TASKS:
        for position, condition in enumerate(conditions, 1):
            out.append({
                "global_position": len(out) + 1,
                "task_order": order,
                "task_id": task,
                "condition": condition,
                "condition_position": position,
            })
    return out


def gate3_four_instances(manifest: dict) -> list[dict]:
    by_task = {r["task_id"]: r for r in manifest["tasks"]}
    proof = []
    for order, task, _ in TASKS:
        record = by_task[task]
        service_refs = record["service_identity"]
        assert_service_references(record, service_refs)
        expected_ids = {}
        for service, ref in service_refs.items():
            subprocess.check_call(["docker", "pull", "--platform", "linux/amd64", ref], stdout=subprocess.DEVNULL)
            expected_ids[service] = subprocess.check_output(
                ["docker", "image", "inspect", ref, "--format", "{{.Id}}"], text=True
            ).strip().lower()
        main_expected = assert_main_runtime_identity(record, expected_ids["main"])
        instances = []
        for condition in "ABCD":
            observed = {}
            for service, ref in service_refs.items():
                name = f"v1-g3-{order:02d}-{condition.lower()}-{service}".replace("_", "-")
                subprocess.run(["docker", "rm", "-f", name], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                container_id = subprocess.check_output(["docker", "create", "--name", name, ref], text=True).strip()
                try:
                    image_id = subprocess.check_output(
                        ["docker", "inspect", container_id, "--format", "{{.Image}}"], text=True
                    ).strip().lower()
                    if image_id != expected_ids[service]:
                        raise RuntimeError(
                            f"V1_G3_INSTANCE_IMAGE_MISMATCH:{task}:{condition}:{service}:{image_id}!={expected_ids[service]}"
                        )
                    observed[service] = image_id
                finally:
                    subprocess.check_call(["docker", "rm", "-f", container_id], stdout=subprocess.DEVNULL)
            if observed["main"] != main_expected:
                raise RuntimeError(f"V1_G3_MAIN_IDENTITY_MISMATCH:{task}:{condition}")
            instances.append({"condition_label": condition, "observed_service_image_ids": observed})
        if len({x["observed_service_image_ids"]["main"] for x in instances}) != 1:
            raise RuntimeError(f"V1_G3_FOUR_MAIN_INSTANCES_DIFFER:{task}")
        proof.append({
            "task_order": order,
            "task_id": task,
            "task_environment_bundle_sha256": record["task_environment_bundle_sha256"],
            "service_identity": service_refs,
            "four_instances": instances,
        })
    return proof


def gate6_schedule() -> list[dict]:
    schedule = exact_schedule()
    if len(schedule) != 48:
        raise RuntimeError("V1_G6_COUNT_INVALID")
    if len({(x["task_id"], x["condition"]) for x in schedule}) != 48:
        raise RuntimeError("V1_G6_DUPLICATE_OR_MISSING")
    expected_conditions = [c for _, _, s in TASKS for c in s]
    if [x["condition"] for x in schedule] != expected_conditions:
        raise RuntimeError("V1_G6_ORDER_INVALID")
    if schedule[0]["task_id"] != "atrx-vep-crispr" or schedule[0]["condition"] != "A":
        raise RuntimeError("V1_G6_FIRST_INVALID")
    return schedule


def gate7_failure_continuation(schedule: list[dict]) -> dict:
    with TemporaryDirectory() as td:
        root = Path(td)
        failure = {
            "experiment_manifest_sha256": "v1-provider-free-gate",
            "run_id": "v1-g7-fixture",
            "task_id": schedule[0]["task_id"],
            "task_order": schedule[0]["task_order"],
            "condition": schedule[0]["condition"],
            "condition_order_position": schedule[0]["condition_position"],
            "success": False,
            "evaluator_result": {"rewards": {"reward": 0}},
            "evaluator_reward": 0,
            "failure_class": "AGENT_OR_HARNESS_EXCEPTION",
            "agent_exception_type": "AgentTimeoutError",
            "accounting_status": "TOKEN_ACCOUNTING_INVALID",
            "provider_attempt_count": 2,
            "task_environment_image_digest": "sha256:" + "a" * 64,
        }
        if must_stop_after_condition(failure["failure_class"]):
            raise RuntimeError("V1_G7_TIMEOUT_INCORRECTLY_FATAL")
        marker = build_completion_record(failure)
        marker_path = root / "condition_complete.json"
        marker_path.write_text(json.dumps(marker, sort_keys=True) + "\n", encoding="utf-8")
        persisted = json.loads(marker_path.read_text(encoding="utf-8"))
        if persisted.get("status") != "COMPLETE" or not persisted.get("continuation_permitted"):
            raise RuntimeError("V1_G7_COMPLETION_MARKER_INVALID")
        next_item = schedule[1]
        if next_item["task_id"] != "atrx-vep-crispr" or next_item["condition"] != "B":
            raise RuntimeError("V1_G7_NEXT_CONDITION_INVALID")
        return {"failed_condition": schedule[0], "completion_marker": persisted, "next_condition": next_item}


def gate8_identity_fail_closed(manifest: dict) -> dict:
    task = manifest["tasks"][0]
    expected = task["built_services"]["main"]["runtime_image_id_at_materialization"]
    wrong = "sha256:" + ("0" if expected[7] != "0" else "1") + expected[8:]
    provider_calls = 0
    error = None
    try:
        assert_main_runtime_identity(task, wrong)
        provider_calls += 1  # unreachable; represents provider boundary
    except RuntimeError as exc:
        error = str(exc)
    if error is None or "INFRASTRUCTURE_INVALID_RUNTIME_IMAGE_DRIFT" not in error:
        raise RuntimeError("V1_G8_IDENTITY_MISMATCH_DID_NOT_FAIL_CLOSED")
    if provider_calls != 0:
        raise RuntimeError("V1_G8_PROVIDER_CALL_OCCURRED")
    return {"expected": expected, "mutated_actual": wrong, "error": error, "provider_calls": 0}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--image-manifest", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()
    manifest = json.loads(args.image_manifest.read_text(encoding="utf-8"))
    if manifest.get("task_environment_bundle_count") != 12 or manifest.get("provider_calls_during_materialization") != 0:
        raise RuntimeError("V1_G1_G2_IMAGE_MANIFEST_INVALID")
    g3 = gate3_four_instances(manifest)
    schedule = gate6_schedule()
    g7 = gate7_failure_continuation(schedule)
    g8 = gate8_identity_fail_closed(manifest)
    result = {
        "schema_version": 1,
        "g1_images_built": 12,
        "g2_digest_manifest": "PASS",
        "g3_four_instance_digest_identity": "PASS",
        "g6_schedule": "PASS",
        "g7_failure_continuation": "PASS",
        "g8_identity_fail_closed": "PASS",
        "provider_calls": 0,
        "g3_proof": g3,
        "schedule": schedule,
        "g7_proof": g7,
        "g8_proof": g8,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8")
    print("FOUR_INSTANCE_DIGEST_IDENTITY_TEST=PASS")
    print("SCHEDULE_TEST=PASS count=48")
    print("FAILURE_CONTINUATION_TEST=PASS")
    print("IDENTITY_FAIL_CLOSED_TEST=PASS")
    print("PROVIDER_CALLS=0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
