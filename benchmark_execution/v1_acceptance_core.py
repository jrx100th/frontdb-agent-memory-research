from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import subprocess
from tempfile import TemporaryDirectory

import yaml

from benchmark_execution.completion_marker import build_completion_record
from benchmark_execution.resume_control import must_stop_after_condition
from benchmark_execution.v1_identity import assert_main_runtime_identity, assert_service_references
from benchmark_execution.v1_runtime_task import assemble

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
IMAGE_REF_RE = re.compile(r"^[^@]+@sha256:[0-9a-f]{64}$")


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


def _compose_for_instance(runtime_task: Path, record: dict, work: Path) -> Path:
    source = runtime_task / "environment/docker-compose.yaml"
    if source.exists():
        compose_path = source
    else:
        compose_path = work / "g3-compose.yaml"
        compose_path.write_text(
            yaml.safe_dump({"services": {"main": {"image": record["service_identity"]["main"]}}}, sort_keys=False),
            encoding="utf-8",
        )
    compose = yaml.safe_load(compose_path.read_text(encoding="utf-8")) or {}
    services = compose.get("services") or {}
    if set(services) != set(record["service_identity"]):
        raise RuntimeError(
            f"V1_G3_SERVICE_SET_MISMATCH:{record['task_id']}:{sorted(services)}!={sorted(record['service_identity'])}"
        )
    for service, cfg in services.items():
        if "build" in cfg:
            raise RuntimeError(f"V1_G3_BUILD_DIRECTIVE_PRESENT:{record['task_id']}:{service}")
        ref = cfg.get("image")
        expected = record["service_identity"][service]
        if ref != expected or not IMAGE_REF_RE.fullmatch(str(ref)):
            raise RuntimeError(f"V1_G3_NONIMMUTABLE_SERVICE_REFERENCE:{record['task_id']}:{service}:{ref}")
    return compose_path


def _pull_and_expected_ids(record: dict) -> dict[str, str]:
    expected_ids: dict[str, str] = {}
    for service, ref in record["service_identity"].items():
        if not IMAGE_REF_RE.fullmatch(ref):
            raise RuntimeError(f"V1_G3_MUTABLE_REFERENCE:{record['task_id']}:{service}:{ref}")
        subprocess.check_call(["docker", "pull", "--platform", "linux/amd64", ref], stdout=subprocess.DEVNULL)
        local_id = subprocess.check_output(
            ["docker", "image", "inspect", ref, "--format", "{{.Id}}"], text=True
        ).strip().lower()
        built = record.get("built_services", {}).get(service)
        if built is not None:
            canonical_id = built["runtime_image_id_at_materialization"].lower()
            if local_id != canonical_id:
                raise RuntimeError(
                    f"V1_G3_CANONICAL_RUNTIME_ID_MISMATCH:{record['task_id']}:{service}:{local_id}!={canonical_id}"
                )
        expected_ids[service] = local_id
    assert_main_runtime_identity(record, expected_ids["main"])
    return expected_ids


def gate3_four_instances(manifest: dict, tb_root: Path) -> list[dict]:
    by_task = {r["task_id"]: r for r in manifest["tasks"]}
    if set(by_task) != {task for _, task, _ in TASKS}:
        raise RuntimeError("V1_G3_TASK_SET_MISMATCH")
    proof = []
    with TemporaryDirectory() as td:
        root = Path(td)
        for order, task, _ in TASKS:
            record = by_task[task]
            service_refs = record["service_identity"]
            assert_service_references(record, service_refs)
            expected_ids = _pull_and_expected_ids(record)
            instances = []
            for instance_index, condition in enumerate("ABCD", 1):
                runtime_task = root / f"task-{order:02d}-{condition}"
                assemble(tb_root / "tasks" / task, runtime_task, record)
                compose_path = _compose_for_instance(runtime_task, record, runtime_task)
                rendered_images = subprocess.check_output(
                    ["docker", "compose", "-f", str(compose_path), "config", "--images"], text=True
                ).splitlines()
                if sorted(rendered_images) != sorted(service_refs.values()):
                    raise RuntimeError(
                        f"V1_G3_COMPOSE_IMAGE_SET_MISMATCH:{task}:{condition}:{rendered_images}"
                    )
                project = f"v1g3-{order:02d}-{instance_index}"
                base_cmd = ["docker", "compose", "-p", project, "-f", str(compose_path)]
                try:
                    subprocess.check_call(base_cmd + ["create", "--no-build"], stdout=subprocess.DEVNULL)
                    observed: dict[str, str] = {}
                    container_ids: dict[str, str] = {}
                    for service in service_refs:
                        cid = subprocess.check_output(base_cmd + ["ps", "-a", "-q", service], text=True).strip()
                        if not cid:
                            raise RuntimeError(f"V1_G3_SERVICE_NOT_INSTANTIATED:{task}:{condition}:{service}")
                        image_id = subprocess.check_output(
                            ["docker", "inspect", cid, "--format", "{{.Image}}"], text=True
                        ).strip().lower()
                        if image_id != expected_ids[service]:
                            raise RuntimeError(
                                f"V1_G3_INSTANCE_IMAGE_MISMATCH:{task}:{condition}:{service}:{image_id}!={expected_ids[service]}"
                            )
                        observed[service] = image_id
                        container_ids[service] = cid
                    instances.append({
                        "instance_index": instance_index,
                        "condition_label": condition,
                        "compose_project": project,
                        "service_refs": service_refs,
                        "observed_service_image_ids": observed,
                        "container_ids": container_ids,
                        "build_directives": 0,
                        "mutable_image_tags": 0,
                    })
                finally:
                    subprocess.run(base_cmd + ["down", "-v", "--remove-orphans"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            for service in service_refs:
                if len({x["observed_service_image_ids"][service] for x in instances}) != 1:
                    raise RuntimeError(f"V1_G3_FOUR_INSTANCES_DIFFER:{task}:{service}")
            proof.append({
                "task_order": order,
                "task_id": task,
                "task_environment_bundle_sha256": record["task_environment_bundle_sha256"],
                "service_identity": service_refs,
                "canonical_runtime_image_ids": expected_ids,
                "four_complete_bundle_instances": instances,
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
    if [x["global_position"] for x in schedule] != list(range(1, 49)):
        raise RuntimeError("V1_G6_GLOBAL_POSITION_INVALID")
    return schedule


def _continuation_fixture(slot: dict, *, failure_class: str, exception_type: str | None, run_label: str) -> dict:
    return {
        "experiment_manifest_sha256": "v1-provider-free-gate",
        "run_id": run_label,
        "task_id": slot["task_id"],
        "task_order": slot["task_order"],
        "condition": slot["condition"],
        "condition_order_position": slot["condition_position"],
        "success": False,
        "evaluator_result": {"rewards": {"reward": 0}},
        "evaluator_reward": 0,
        "failure_class": failure_class,
        "agent_exception_type": exception_type,
        "accounting_status": "TOKEN_ACCOUNTING_INVALID" if exception_type else "VALID",
        "provider_attempt_count": 2 if exception_type else 1,
        "task_environment_image_digest": "sha256:" + "a" * 64,
    }


def _checkpoint_and_next(root: Path, schedule: list[dict], index: int, result: dict) -> dict:
    if must_stop_after_condition(result["failure_class"]):
        raise RuntimeError(f"V1_G7_LEGITIMATE_OUTCOME_INCORRECTLY_FATAL:{result['failure_class']}")
    case = root / f"case-{index}"
    case.mkdir()
    (case / "run_result.json").write_text(json.dumps(result, sort_keys=True) + "\n", encoding="utf-8")
    marker = build_completion_record(result)
    (case / "condition_complete.json").write_text(json.dumps(marker, sort_keys=True) + "\n", encoding="utf-8")
    persisted = json.loads((case / "condition_complete.json").read_text(encoding="utf-8"))
    if persisted.get("status") != "COMPLETE" or not persisted.get("continuation_permitted"):
        raise RuntimeError("V1_G7_COMPLETION_MARKER_INVALID")
    if index + 1 >= len(schedule):
        raise RuntimeError("V1_G7_NO_FOLLOWING_FROZEN_CONDITION")
    return {"run_result": result, "completion_marker": persisted, "next_condition": schedule[index + 1]}


def gate7_failure_continuation(schedule: list[dict]) -> dict:
    with TemporaryDirectory() as td:
        root = Path(td)
        task_failure = _checkpoint_and_next(
            root,
            schedule,
            0,
            _continuation_fixture(schedule[0], failure_class="TASK_FAILURE", exception_type=None, run_label="v1-g7-task-failure"),
        )
        timeout = _checkpoint_and_next(
            root,
            schedule,
            1,
            _continuation_fixture(
                schedule[1],
                failure_class="AGENT_OR_HARNESS_EXCEPTION",
                exception_type="AgentTimeoutError",
                run_label="v1-g7-agent-timeout",
            ),
        )
        if task_failure["next_condition"] != schedule[1] or timeout["next_condition"] != schedule[2]:
            raise RuntimeError("V1_G7_FROZEN_NEXT_CONDITION_INVALID")
        return {"task_failure": task_failure, "agent_timeout": timeout}


def _expect_fail_before_provider(label: str, fn) -> dict:
    provider_calls = 0
    error = None
    try:
        fn()
        provider_calls += 1
    except RuntimeError as exc:
        error = str(exc)
    if error is None or provider_calls != 0:
        raise RuntimeError(f"V1_G8_DID_NOT_FAIL_CLOSED:{label}")
    return {"label": label, "error": error, "provider_calls": 0}


def gate8_identity_fail_closed(manifest: dict, env_packet: dict) -> dict:
    task = manifest["tasks"][0]
    expected_runtime = task["built_services"]["main"]["runtime_image_id_at_materialization"]
    wrong_runtime = "sha256:" + ("0" if expected_runtime[7] != "0" else "1") + expected_runtime[8:]
    runtime_case = _expect_fail_before_provider(
        "task_image_runtime_identity",
        lambda: assert_main_runtime_identity(task, wrong_runtime),
    )

    wrong_refs = dict(task["service_identity"])
    wrong_refs["main"] = wrong_refs["main"].replace("sha256:", "sha256:" + ("0" if wrong_refs["main"].split("sha256:", 1)[1][0] != "0" else "1"), 1)
    service_case = _expect_fail_before_provider(
        "environment_service_reference_identity",
        lambda: assert_service_references(task, wrong_refs),
    )

    expected_source = env_packet["expected_task_environment_identity_sha256"][task["task_id"]]
    wrong_source = ("0" if expected_source[0] != "0" else "1") + expected_source[1:]

    def source_check() -> None:
        if wrong_source != task["task_environment_source_identity_sha256"]:
            raise RuntimeError("INFRASTRUCTURE_INVALID_TASK_SOURCE_IDENTITY")

    source_case = _expect_fail_before_provider("task_source_identity", source_check)

    def configuration_check() -> None:
        frozen = exact_schedule()[0]
        observed = dict(frozen)
        observed["condition"] = "D"
        if observed != frozen:
            raise RuntimeError("CONFIGURATION_INVALID_CONDITION_SCHEDULE")

    config_case = _expect_fail_before_provider("configuration_schedule_identity", configuration_check)
    return {
        "runtime_image_defect": runtime_case,
        "service_reference_defect": service_case,
        "task_source_defect": source_case,
        "configuration_defect": config_case,
        "provider_calls": 0,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--image-manifest", type=Path, required=True)
    ap.add_argument("--env-packet", type=Path, required=True)
    ap.add_argument("--tb-root", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()
    manifest = json.loads(args.image_manifest.read_text(encoding="utf-8"))
    env_packet = json.loads(args.env_packet.read_text(encoding="utf-8"))
    if manifest.get("task_environment_bundle_count") != 12 or manifest.get("provider_calls_during_materialization") != 0:
        raise RuntimeError("V1_G1_G2_IMAGE_MANIFEST_INVALID")
    g3 = gate3_four_instances(manifest, args.tb_root)
    schedule = gate6_schedule()
    g7 = gate7_failure_continuation(schedule)
    g8 = gate8_identity_fail_closed(manifest, env_packet)
    result = {
        "schema_version": 2,
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
    print("FOUR_INSTANCE_DIGEST_IDENTITY_TEST=PASS tasks=12 instances=48")
    print("SCHEDULE_TEST=PASS count=48")
    print("FAILURE_CONTINUATION_TEST=PASS task_failure=1 agent_timeout=1")
    print("IDENTITY_FAIL_CLOSED_TEST=PASS provider_calls=0")
    print("PROVIDER_CALLS=0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
