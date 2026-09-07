from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import subprocess
from tempfile import TemporaryDirectory

import yaml

from benchmark_execution import v1_acceptance_core as prior
from benchmark_execution.v1_identity import assert_main_runtime_identity, assert_service_references
from benchmark_execution.v1_runtime_task import assemble

IMAGE_REF_RE = re.compile(r"^[^@]+@sha256:[0-9a-f]{64}$")
HARBOR_MAIN_COMMAND = ["sh", "-c", "sleep infinity"]
TASK05 = "coq-block-bound"


def _pull_expected_ids(record: dict) -> dict[str, str]:
    out: dict[str, str] = {}
    for service, ref in record["service_identity"].items():
        if not IMAGE_REF_RE.fullmatch(str(ref)):
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
        out[service] = local_id
    assert_main_runtime_identity(record, out["main"])
    return out


def _harbor_faithful_compose(runtime_task: Path, record: dict) -> Path:
    source = runtime_task / "environment/docker-compose.yaml"
    if source.exists():
        compose = yaml.safe_load(source.read_text(encoding="utf-8")) or {}
        compose_path = source
    else:
        compose = {"services": {"main": {}}}
        compose_path = runtime_task / "environment/g3-harbor-runtime.yaml"

    services = compose.setdefault("services", {})
    if set(services) != set(record["service_identity"]):
        raise RuntimeError(
            f"V1_G3_SERVICE_SET_MISMATCH:{record['task_id']}:{sorted(services)}!={sorted(record['service_identity'])}"
        )

    for service, cfg in services.items():
        if "build" in cfg:
            raise RuntimeError(f"V1_G3_BUILD_DIRECTIVE_PRESENT:{record['task_id']}:{service}")
        ref = record["service_identity"][service]
        if not IMAGE_REF_RE.fullmatch(ref):
            raise RuntimeError(f"V1_G3_NONIMMUTABLE_SERVICE_REFERENCE:{record['task_id']}:{service}:{ref}")
        cfg["image"] = ref

    # Harbor v0.18 Terminal-Bench mapper defines this effective command for the
    # main task service. Sidecar commands/entrypoints/environment/dependencies
    # remain exactly as authored in the frozen task compose file.
    main = services["main"]
    main["command"] = list(HARBOR_MAIN_COMMAND)
    env = main.get("environment")
    if env is None:
        main["environment"] = {"TEST_DIR": "/tests"}
    elif isinstance(env, dict):
        env.setdefault("TEST_DIR", "/tests")
    elif isinstance(env, list):
        if not any(str(x).startswith("TEST_DIR=") for x in env):
            env.append("TEST_DIR=/tests")
    else:
        raise RuntimeError(f"V1_G3_MAIN_ENVIRONMENT_SHAPE_INVALID:{record['task_id']}")

    compose_path.write_text(yaml.safe_dump(compose, sort_keys=False), encoding="utf-8")
    rendered = yaml.safe_load(compose_path.read_text(encoding="utf-8")) or {}
    for service, cfg in (rendered.get("services") or {}).items():
        if "build" in cfg:
            raise RuntimeError(f"V1_G3_BUILD_DIRECTIVE_SURVIVED:{record['task_id']}:{service}")
        if cfg.get("image") != record["service_identity"][service]:
            raise RuntimeError(f"V1_G3_SERVICE_REFERENCE_DRIFT:{record['task_id']}:{service}")
    if rendered["services"]["main"].get("command") != HARBOR_MAIN_COMMAND:
        raise RuntimeError(f"V1_G3_MAIN_COMMAND_DRIFT:{record['task_id']}")
    return compose_path


def task05_negative_positive(record: dict, expected_main_id: str) -> dict:
    ref = record["service_identity"]["main"]
    bare_name = "v1-g3-task05-bare-negative"
    good_name = "v1-g3-task05-harbor-positive"
    subprocess.run(["docker", "rm", "-f", bare_name, good_name], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    bare = subprocess.run(
        ["docker", "create", "--name", bare_name, ref],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    bare_text = (bare.stdout + "\n" + bare.stderr).strip()
    if bare.returncode == 0:
        subprocess.run(["docker", "rm", "-f", bare_name], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        raise RuntimeError("V1_G3_TASK05_BARE_INSTANTIATION_UNEXPECTEDLY_SUCCEEDED")
    if "no command specified" not in bare_text.lower():
        raise RuntimeError(f"V1_G3_TASK05_BARE_FAILURE_UNEXPECTED:{bare_text}")

    cid = subprocess.check_output(
        ["docker", "run", "-d", "--name", good_name, ref, *HARBOR_MAIN_COMMAND], text=True
    ).strip()
    try:
        running = subprocess.check_output(
            ["docker", "inspect", cid, "--format", "{{.State.Running}}"], text=True
        ).strip().lower()
        image_id = subprocess.check_output(
            ["docker", "inspect", cid, "--format", "{{.Image}}"], text=True
        ).strip().lower()
        if running != "true":
            raise RuntimeError("V1_G3_TASK05_HARBOR_FAITHFUL_NOT_RUNNING")
        if image_id != expected_main_id:
            raise RuntimeError(f"V1_G3_TASK05_HARBOR_FAITHFUL_IMAGE_MISMATCH:{image_id}!={expected_main_id}")
    finally:
        subprocess.run(["docker", "rm", "-f", good_name], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    return {
        "bare_negative": {"status": "PASS", "returncode": bare.returncode, "error": bare_text},
        "harbor_faithful_positive": {
            "status": "PASS",
            "command": HARBOR_MAIN_COMMAND,
            "runtime_image_id": expected_main_id,
        },
    }


def gate3_four_instances(manifest: dict, tb_root: Path) -> tuple[list[dict], dict]:
    by_task = {r["task_id"]: r for r in manifest["tasks"]}
    expected_tasks = {task for _, task, _ in prior.TASKS}
    if set(by_task) != expected_tasks:
        raise RuntimeError("V1_G3_TASK_SET_MISMATCH")

    expected_ids_by_task: dict[str, dict[str, str]] = {}
    for _, task, _ in prior.TASKS:
        record = by_task[task]
        assert_service_references(record, record["service_identity"])
        expected_ids_by_task[task] = _pull_expected_ids(record)

    task05_proof = task05_negative_positive(
        by_task[TASK05], expected_ids_by_task[TASK05]["main"]
    )

    proof: list[dict] = []
    with TemporaryDirectory() as td:
        root = Path(td)
        # Re-run from task01, never resume at task05.
        for order, task, _ in prior.TASKS:
            record = by_task[task]
            expected_ids = expected_ids_by_task[task]
            instances = []
            for instance_index, condition in enumerate("ABCD", 1):
                runtime_task = root / f"task-{order:02d}-{condition}"
                assemble(tb_root / "tasks" / task, runtime_task, record)
                compose_path = _harbor_faithful_compose(runtime_task, record)
                project = f"v1g3r-{order:02d}-{instance_index}"
                base = ["docker", "compose", "-p", project, "-f", str(compose_path)]
                try:
                    rendered_images = subprocess.check_output(base + ["config", "--images"], text=True).splitlines()
                    if sorted(rendered_images) != sorted(record["service_identity"].values()):
                        raise RuntimeError(f"V1_G3_COMPOSE_IMAGE_SET_MISMATCH:{task}:{condition}:{rendered_images}")
                    subprocess.check_call(base + ["up", "-d", "--no-build"], stdout=subprocess.DEVNULL)
                    observed: dict[str, str] = {}
                    states: dict[str, str] = {}
                    for service in record["service_identity"]:
                        cid = subprocess.check_output(base + ["ps", "-a", "-q", service], text=True).strip()
                        if not cid:
                            raise RuntimeError(f"V1_G3_SERVICE_NOT_INSTANTIATED:{task}:{condition}:{service}")
                        image_id = subprocess.check_output(
                            ["docker", "inspect", cid, "--format", "{{.Image}}"], text=True
                        ).strip().lower()
                        running = subprocess.check_output(
                            ["docker", "inspect", cid, "--format", "{{.State.Running}}"], text=True
                        ).strip().lower()
                        if image_id != expected_ids[service]:
                            raise RuntimeError(
                                f"V1_G3_INSTANCE_IMAGE_MISMATCH:{task}:{condition}:{service}:{image_id}!={expected_ids[service]}"
                            )
                        if running != "true":
                            raise RuntimeError(f"V1_G3_SERVICE_NOT_RUNNING:{task}:{condition}:{service}")
                        observed[service] = image_id
                        states[service] = running
                    instances.append({
                        "instance_index": instance_index,
                        "condition_label": condition,
                        "compose_project": project,
                        "service_refs": record["service_identity"],
                        "observed_service_image_ids": observed,
                        "running": states,
                        "main_effective_command": HARBOR_MAIN_COMMAND,
                        "build_directives": 0,
                        "mutable_image_tags": 0,
                    })
                finally:
                    subprocess.run(base + ["down", "-v", "--remove-orphans"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            for service in record["service_identity"]:
                if len({x["observed_service_image_ids"][service] for x in instances}) != 1:
                    raise RuntimeError(f"V1_G3_FOUR_INSTANCES_DIFFER:{task}:{service}")
            proof.append({
                "task_order": order,
                "task_id": task,
                "task_environment_bundle_sha256": record["task_environment_bundle_sha256"],
                "service_identity": record["service_identity"],
                "canonical_runtime_image_ids": expected_ids,
                "four_harbor_faithful_running_bundle_instances": instances,
            })
    return proof, task05_proof


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

    g3, task05_proof = gate3_four_instances(manifest, args.tb_root)
    schedule = prior.gate6_schedule()
    g7 = prior.gate7_failure_continuation(schedule)
    g8 = prior.gate8_identity_fail_closed(manifest, env_packet)
    result = {
        "schema_version": 3,
        "g3_root_cause_classification": "VALIDATOR_DEFECT_BARE_OCI_INSTANTIATION_NOT_HARBOR_RUNTIME_CONTRACT",
        "task05_bare_negative_test": "PASS",
        "task05_harbor_faithful_positive_test": "PASS",
        "g3_four_instance_digest_identity": "PASS",
        "g6_schedule": "PASS",
        "g7_failure_continuation": "PASS",
        "g8_identity_fail_closed": "PASS",
        "provider_calls": 0,
        "task05_proof": task05_proof,
        "g3_proof": g3,
        "schedule": schedule,
        "g7_proof": g7,
        "g8_proof": g8,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8")
    print("G3_ROOT_CAUSE_CLASSIFICATION=VALIDATOR_DEFECT_BARE_OCI_INSTANTIATION_NOT_HARBOR_RUNTIME_CONTRACT")
    print("TASK05_BARE_NEGATIVE_TEST=PASS")
    print("TASK05_HARBOR_FAITHFUL_POSITIVE_TEST=PASS")
    print("FOUR_INSTANCE_DIGEST_IDENTITY_TEST=PASS tasks=12 instances=48")
    print("SCHEDULE_TEST=PASS count=48")
    print("FAILURE_CONTINUATION_TEST=PASS")
    print("IDENTITY_FAIL_CLOSED_TEST=PASS provider_calls=0")
    print("PROVIDER_CALLS=0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
