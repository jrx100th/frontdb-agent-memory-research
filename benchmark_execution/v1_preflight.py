from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import tomllib
import yaml

ENV_PACKET_SHA256 = "26566fea65da18291160d2f45598942182d4edf23e1b95485734bc196a67945e"
TB_SHA = "2b0442c3c583b710ca8da14c8e601b99f2f1f244"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canon(obj) -> bytes:
    return (json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True) + "\n").encode("utf-8")


def git(repo: Path, *args: str) -> str:
    return subprocess.check_output(["git", "-C", str(repo), *args], text=True).strip()


def one_task(images: dict, task: str) -> dict:
    matches = [x for x in images["tasks"] if x["task_id"] == task]
    if len(matches) != 1:
        raise RuntimeError(f"CONFIGURATION_INVALID_V1_TASK_IMAGE_RECORD:{task}:{len(matches)}")
    return matches[0]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo-root", type=Path, required=True)
    ap.add_argument("--tb-root", type=Path, required=True)
    ap.add_argument("--runtime-task", type=Path, required=True)
    ap.add_argument("--run-root", type=Path, required=True)
    ap.add_argument("--task", required=True)
    ap.add_argument("--task-order", type=int, required=True)
    ap.add_argument("--condition", required=True)
    ap.add_argument("--condition-position", type=int, required=True)
    ap.add_argument("--run-id", required=True)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()

    repo = args.repo_root.resolve()
    tb = args.tb_root.resolve()
    runtime_task = args.runtime_task.resolve()
    v1_path = repo / "manifests/experiment_manifest.v1.final.json"
    v1_hash_record = repo / "reproducibility/V1_MANIFEST_SHA256.txt"
    images_path = repo / "reproducibility/v1_task_images.json"
    images_hash_record = repo / "reproducibility/V1_TASK_IMAGE_MANIFEST_SHA256.txt"
    packet_path = repo / "reproducibility/TASK_ENVIRONMENT_IDENTITIES.json"

    if not all(p.is_file() for p in [v1_path, v1_hash_record, images_path, images_hash_record, packet_path]):
        raise RuntimeError("CONFIGURATION_INVALID_V1_CANONICAL_INPUT_MISSING")
    v1_sha = sha(v1_path)
    if v1_hash_record.read_text(encoding="utf-8").strip() != v1_sha:
        raise RuntimeError("CONFIGURATION_INVALID_V1_MANIFEST_HASH")
    v1 = json.loads(v1_path.read_text(encoding="utf-8"))
    if v1.get("experiment_version") != "v1-environment-materialized-1" or v1.get("v1_pre_provider_acceptance", {}).get("status") != "PASS":
        raise RuntimeError("CONFIGURATION_INVALID_V1_MANIFEST_STATE")
    images_sha = sha(images_path)
    if images_hash_record.read_text(encoding="utf-8").strip() != images_sha:
        raise RuntimeError("CONFIGURATION_INVALID_V1_IMAGE_MANIFEST_HASH")
    if v1["execution"]["environment_materialization"]["task_environment_bundle_manifest_sha256"] != images_sha:
        raise RuntimeError("CONFIGURATION_INVALID_V1_IMAGE_MANIFEST_BINDING")
    if sha(packet_path) != ENV_PACKET_SHA256:
        raise RuntimeError("INFRASTRUCTURE_INVALID_ENV_PACKET_HASH")
    if git(tb, "rev-parse", "HEAD") != TB_SHA:
        raise RuntimeError("INFRASTRUCTURE_INVALID_TERMINAL_BENCH_REVISION")

    schedule = v1["execution"]["schedule"]
    if args.task_order < 1 or args.task_order > len(schedule):
        raise RuntimeError("CONFIGURATION_INVALID_TASK_ORDER")
    slot = schedule[args.task_order - 1]
    if slot["task_order"] != args.task_order or slot["task_id"] != args.task:
        raise RuntimeError("CONFIGURATION_INVALID_TASK_SCHEDULE")
    if args.condition_position < 1 or args.condition_position > 4:
        raise RuntimeError("CONFIGURATION_INVALID_CONDITION_POSITION")
    if slot["condition_order"][args.condition_position - 1] != args.condition:
        raise RuntimeError("CONFIGURATION_INVALID_CONDITION_SCHEDULE")

    packet = json.loads(packet_path.read_text(encoding="utf-8"))
    rec = packet["tasks"].get(args.task)
    expected_identity = packet["expected_task_environment_identity_sha256"].get(args.task)
    if rec is None or expected_identity is None:
        raise RuntimeError("INFRASTRUCTURE_INVALID_TASK_PACKET_MISSING")
    task_rel = f"tasks/{args.task}/task.toml"
    env_rel = f"tasks/{args.task}/environment"
    if git(tb, "rev-parse", f"{TB_SHA}:{task_rel}") != rec["task_toml_git_blob_sha"]:
        raise RuntimeError("INFRASTRUCTURE_INVALID_TASK_TOML_BLOB")
    if git(tb, "rev-parse", f"{TB_SHA}:{env_rel}") != rec["environment_git_tree_sha"]:
        raise RuntimeError("INFRASTRUCTURE_INVALID_ENVIRONMENT_TREE")
    actual_identity = hashlib.sha256(canon(rec)).hexdigest()
    if actual_identity != expected_identity:
        raise RuntimeError("INFRASTRUCTURE_INVALID_TASK_COMPOSITE_IDENTITY")

    images = json.loads(images_path.read_text(encoding="utf-8"))
    image_rec = one_task(images, args.task)
    if image_rec["task_environment_source_identity_sha256"] != expected_identity:
        raise RuntimeError("INFRASTRUCTURE_INVALID_IMAGE_SOURCE_BINDING")
    runtime_prov_path = runtime_task / ".v1-runtime-materialization.json"
    runtime_prov = json.loads(runtime_prov_path.read_text(encoding="utf-8"))
    if runtime_prov["task_environment_bundle_sha256"] != image_rec["task_environment_bundle_sha256"]:
        raise RuntimeError("INFRASTRUCTURE_INVALID_RUNTIME_BUNDLE_BINDING")
    if runtime_prov["service_identity"] != image_rec["service_identity"]:
        raise RuntimeError("INFRASTRUCTURE_INVALID_RUNTIME_SERVICE_IDENTITY")

    task_cfg = tomllib.loads((runtime_task / "task.toml").read_text(encoding="utf-8"))
    if task_cfg["environment"].get("docker_image") != image_rec["primary_main_immutable_image_reference"]:
        raise RuntimeError("INFRASTRUCTURE_INVALID_RUNTIME_MAIN_IMAGE_REFERENCE")
    compose_path = runtime_task / "environment/docker-compose.yaml"
    if compose_path.exists():
        compose = yaml.safe_load(compose_path.read_text(encoding="utf-8")) or {}
        for service, cfg in (compose.get("services") or {}).items():
            if "build" in cfg:
                raise RuntimeError(f"INFRASTRUCTURE_INVALID_RUNTIME_REBUILD_DIRECTIVE:{service}")
            if service in image_rec["service_identity"] and cfg.get("image") != image_rec["service_identity"][service]:
                raise RuntimeError(f"INFRASTRUCTURE_INVALID_RUNTIME_SERVICE_REFERENCE:{service}")

    memory_side_effects = sorted(str(p) for p in args.run_root.rglob("memory*.sqlite*")) if args.run_root.exists() else []
    if memory_side_effects:
        raise RuntimeError(f"INFRASTRUCTURE_INVALID_NONFRESH_MEMORY_START:{memory_side_effects}")

    result = {
        "schema_version": 1,
        "status": "PASS",
        "manifest_sha256": v1_sha,
        "image_manifest_sha256": images_sha,
        "environment_packet_sha256": ENV_PACKET_SHA256,
        "terminal_bench_revision": TB_SHA,
        "task_id": args.task,
        "task_order": args.task_order,
        "condition": args.condition,
        "condition_position": args.condition_position,
        "run_id": args.run_id,
        "task_environment_identity_sha256": expected_identity,
        "task_environment_bundle_sha256": image_rec["task_environment_bundle_sha256"],
        "expected_main_immutable_image_reference": image_rec["primary_main_immutable_image_reference"],
        "expected_main_runtime_image_id": image_rec["built_services"]["main"]["runtime_image_id_at_materialization"],
        "service_identity": image_rec["service_identity"],
        "per_condition_rebuild": False,
        "memory_start_state": "ABSENT",
        "provider_calls": 0,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(canon(result))
    print(f"V1_PRE_PROVIDER_PREFLIGHT=PASS task={args.task} condition={args.condition}")
    print("PER_CONDITION_REBUILD=NO")
    print("PROVIDER_CALLS=0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
