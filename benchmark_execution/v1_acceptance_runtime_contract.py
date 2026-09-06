from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import subprocess
from tempfile import TemporaryDirectory

import yaml

from benchmark_execution.v1_acceptance_core import (
    TASKS,
    gate6_schedule,
    gate7_failure_continuation,
    gate8_identity_fail_closed,
)
from benchmark_execution.v1_identity import assert_main_runtime_identity, assert_service_references
from benchmark_execution.v1_runtime_task import assemble

IMAGE_REF_RE = re.compile(r"^[^@]+@sha256:[0-9a-f]{64}$")
HARBOR_MAIN_COMMAND = ["sh", "-c", "sleep infinity"]
TASK05 = "coq-block-bound"


def _pull_and_expected_ids(record: dict) -> dict[str, str]:
    expected_ids: dict[str, str] = {}
    for service, ref in record["service_identity"].items():
        if not IMAGE_REF_RE.fullmatch(str(ref)):
            raise RuntimeError(f"V1_G3_MUTABLE_REFERENCE:{record['task_id']}:{service}:{ref}")
        subprocess.check_call(
            ["docker", "pull", "--platform", "linux/amd64", ref],
            stdout=subprocess.DEVNULL,
        )
        local_id = subprocess.check_output(
            ["docker", "image", "inspect", ref, "--format", "{{.Id}}"],
            text=True,
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


def _harbor_faithful_compose(runtime_task: Path, record: dict) -> Path:
    original = runtime_task / "environment/docker-compose.yaml"
    if original.exists():
        compose = yaml.safe_load(original.read_text(encoding="utf-8")) or {}
    else:
        compose = {"services": {"main": {"image": record["service_identity"]["main"]}}}

    services = compose.get("services") or {}
    if set(services) != set(record["service_identity"]):
        raise RuntimeError(
            f"V1_G3_SERVICE_SET_MISMATCH:{record['task_id']}:{sorted(services)}!={sorted(record['service_identity'])}"
        )

    for service, cfg in services.items():
        if "build" in cfg:
            raise RuntimeError(f"V1_G3_BUILD_DIRECTIVE_PRESENT:{record['task_id']}:{service}")
        expected_ref = record["service_identity"][service]
        actual_ref = cfg.get("image")
        if actual_ref != expected_ref or not IMAGE_REF_RE.fullmatch(str(actual_ref)):
            raise RuntimeError(
                f"V1_G3_NONIMMUTABLE_SERVICE_REFERENCE:{record['task_id']}:{service}:{actual_ref}"
            )

    # Harbor v0.18.0 supplies this runtime command for the main task container.
    # Do not change entrypoint, workdir, env, relationships, volumes, or sidecar commands.
    services["main"]["command"] = list(HARBOR_MAIN_COMMAND)

    out = runtime_task / "g3-harbor-faithful-compose.yaml"
    out.write_text(yaml.safe_dump(compose, sort_keys=False), encoding="utf-8")
    return out


def _inspect_container(cid: str) -> dict:
    image_id = subprocess.check_output(
        ["docker", "inspect", cid, "--format", "{{.Image}}"], text=True
    ).strip().lower()
    running = subprocess.check_output(
        ["docker", "inspect", cid, "--format", "{{.State.Running}}"], text=True
    ).strip().lower()
    cmd = json.loads(
        subprocess.check_output(
            ["docker", "inspect", cid, "--format", "{{json .Config.Cmd}}"], text=True
        ).strip()
    )
    entrypoint = json.loads(
        subprocess.check_output(
            ["docker", "inspect", cid, "--format", "{{json .Config.Entrypoint}}"], text=True
        ).strip()
    )
    return {
        "image_id": image_id,
        "running": running == "true",
        "cmd": cmd,
        "entrypoint": entrypoint,
    }


def task05_bare_negative_and_harbor_positive(record: dict, expected_main_id: str) -> dict:
    ref = record["service_identity"]["main"]
    bare_name = "v1-g3-task05-bare-negative"
    subprocess.run(["docker", "rm", "-f", bare_name], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    bare = subprocess.run(
        ["docker", "create", "--name", bare_name, ref],
        text=True,
        capture_output=True,
    )
    if bare.returncode == 0:
        subprocess.run(["docker", "rm", "-f", bare_name], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        raise RuntimeError("V1_G3_TASK05_BARE_INSTANTIATION_UNEXPECTEDLY_SUCCEEDED")
    bare_error = (bare.stderr + "\n" + bare.stdout).strip()
    if "no command specified" not in bare_error.lower() and "no command" not in bare_error.lower():
        raise RuntimeError(f"V1_G3_TASK05_BARE_FAILURE_UNEXPECTED:{bare_error}")

    positive_name = "v1-g3-task05-harbor-positive"
    subprocess.run(["docker", "rm", "-f", positive_name], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    cid = subprocess.check_output(
        ["docker", "create", "--name", positive_name, ref, *HARBOR_MAIN_COMMAND],
        text=True,
    ).strip()
    try:
        subprocess.check_call(["docker", "start", cid], stdout=subprocess.DEVNULL)
        observed = _inspect_container(cid)
        if not observed["running"]:
            raise RuntimeError("V1_G3_TASK05_HARBOR_FAITHFUL_CONTAINER_NOT_RUNNING")
        if observed["image_id"] != expected_main_id:
            raise RuntimeError(
                f"V1_G3_TASK05_HARBOR_FAITHFUL_IMAGE_MISMATCH:{observed['image_id']}!={expected_main_id}"
            )
        if observed["cmd"] != HARBOR_MAIN_COMMAND:
            raise RuntimeError(f"V1_G3_TASK05_HARBOR_COMMAND_MISMATCH:{observed['cmd']}")
    finally:
        subprocess.run(["docker", "rm", "-f", cid], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    return {
        "task_id": TASK05,
        "bare_negative": {
            "status": "PASS",
            "returncode": bare.returncode,
            "error": bare_error,
        },
        "harbor_faithful_positive": {
            "status": "PASS",
            "command": HARBOR_MAIN_COMMAND,
            "image_id": expected_main_id,
        },
    }


def gate3_four_instances(manifest: dict, tb_root: Path) -> tuple[list[dict], dict]:
    by_task = {r["task_id"]: r for r in manifest["tasks"]}
    expected_task_set = {task for _, task, _ in TASKS}
    if set(by_task) != expected_task_set:
        raise RuntimeError("V1_G3_TASK_SET_MISMATCH")

    proof: list[dict] = []
    task05_contract: dict | None = None
    with TemporaryDirectory() as td:
        root = Path(td)
        for order, task, _ in TASKS:
            record = by_task[task]
            assert_service_references(record, record["service_identity"])
            expected_ids = _pull_and_expected_ids(record)

            if task == TASK05:
                task05_contract = task05_bare_negative_and_harbor_positive(
                    record, expected_ids["main"]
                )

            instances = []
            for instance_index, condition in enumerate("ABCD", 1):
                runtime_task = root / f"task-{order:02d}-{condition}"
                assemble(tb_root / "tasks" / task, runtime_task, record)
                compose_path = _harbor_faithful_compose(runtime_task, record)

                rendered_images = subprocess.check_output(
                    ["docker", "compose", "-f", str(compose_path), "config", "--images"],
                    text=True,
                ).splitlines()
                if sorted(rendered_images) != sorted(record["service_identity"].values()):
                    raise RuntimeError(
                        f"V1_G3_COMPOSE_IMAGE_SET_MISMATCH:{task}:{condition}:{rendered_images}"
                    )

                project = f"v1g3-{order:02d}-{instance_index}"
                base_cmd = ["docker", "compose", "-p", project, "-f", str(compose_path)]
                try:
                    subprocess.check_call(
                        base_cmd + ["up", "-d", "--no-build", "--pull", "never", "--remove-orphans"],
                        stdout=subprocess.DEVNULL,
                    )
                    observed: dict[str, dict] = {}
                    for service in record["service_identity"]:
                        cid = subprocess.check_output(
                            base_cmd + ["ps", "-a", "-q", service], text=True
                        ).strip()
                        if not cid:
                            raise RuntimeError(
                                f"V1_G3_SERVICE_NOT_INSTANTIATED:{task}:{condition}:{service}"
                            )
                        state = _inspect_container(cid)
                        if not state["running"]:
                            raise RuntimeError(
                                f"V1_G3_SERVICE_NOT_RUNNING:{task}:{condition}:{service}"
                            )
                        if state["image_id"] != expected_ids[service]:
                            raise RuntimeError(
                                f"V1_G3_INSTANCE_IMAGE_MISMATCH:{task}:{condition}:{service}:{state['image_id']}!={expected_ids[service]}"
                            )
                        if service == "main" and state["cmd"] != HARBOR_MAIN_COMMAND:
                            raise RuntimeError(
                                f"V1_G3_MAIN_RUNTIME_COMMAND_MISMATCH:{task}:{condition}:{state['cmd']}"
                            )
                        observed[service] = state
                    instances.append(
                        {
                            "instance_index": instance_index,
                            "condition_label": condition,
                            "compose_project": project,
                            "service_refs": record["service_identity"],
                            "observed_services": observed,
                            "build_directives": 0,
                            "mutable_image_tags": 0,
                            "main_harbor_command": HARBOR_MAIN_COMMAND,
                        }
                    )
                finally:
                    subprocess.run(
                        base_cmd + ["down", "-v", "--remove-orphans"],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )

            for service in record["service_identity"]:
                observed_ids = {
                    x["observed_services"][service]["image_id"] for x in instances
                }
                if observed_ids != {expected_ids[service]}:
                    raise RuntimeError(f"V1_G3_FOUR_INSTANCES_DIFFER:{task}:{service}")

            proof.append(
                {
                    "task_order": order,
                    "task_id": task,
                    "task_environment_bundle_sha256": record["task_environment_bundle_sha256"],
                    "service_identity": record["service_identity"],
                    "canonical_runtime_image_ids": expected_ids,
                    "four_complete_bundle_instances": instances,
                }
            )

    if task05_contract is None:
        raise RuntimeError("V1_G3_TASK05_CONTRACT_PROOF_MISSING")
    return proof, task05_contract


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--image-manifest", type=Path, required=True)
    ap.add_argument("--env-packet", type=Path, required=True)
    ap.add_argument("--tb-root", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()

    manifest = json.loads(args.image_manifest.read_text(encoding="utf-8"))
    env_packet = json.loads(args.env_packet.read_text(encoding="utf-8"))
    if manifest.get("task_environment_bundle_count") != 12:
        raise RuntimeError("V1_G1_G2_IMAGE_MANIFEST_INVALID")
    if manifest.get("provider_calls_during_materialization") != 0:
        raise RuntimeError("V1_G1_G2_PROVIDER_CALLS_NONZERO")

    g3, task05_contract = gate3_four_instances(manifest, args.tb_root)
    schedule = gate6_schedule()
    g7 = gate7_failure_continuation(schedule)
    g8 = gate8_identity_fail_closed(manifest, env_packet)

    result = {
        "schema_version": 3,
        "g1_images_built": 12,
        "g2_digest_manifest": "PASS",
        "g3_root_cause_classification": "VALIDATOR_DEFECT_BARE_OCI_INSTANTIATION_DID_NOT_REPRODUCE_HARBOR_MAIN_RUNTIME_COMMAND",
        "task05_bare_negative_test": "PASS",
        "task05_harbor_faithful_positive_test": "PASS",
        "g3_four_instance_digest_identity": "PASS",
        "g6_schedule": "PASS",
        "g7_failure_continuation": "PASS",
        "g8_identity_fail_closed": "PASS",
        "provider_calls": 0,
        "task05_runtime_contract_proof": task05_contract,
        "g3_proof": g3,
        "schedule": schedule,
        "g7_proof": g7,
        "g8_proof": g8,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    print("G3_ROOT_CAUSE_CLASSIFICATION=VALIDATOR_DEFECT")
    print("TASK05_BARE_NEGATIVE_TEST=PASS")
    print("TASK05_HARBOR_FAITHFUL_POSITIVE_TEST=PASS")
    print("FOUR_INSTANCE_DIGEST_IDENTITY_TEST=PASS tasks=12 instances=48")
    print("SCHEDULE_TEST=PASS count=48")
    print("FAILURE_CONTINUATION_TEST=PASS task_failure=1 agent_timeout=1")
    print("IDENTITY_FAIL_CLOSED_TEST=PASS provider_calls=0")
    print("PROVIDER_CALLS=0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
