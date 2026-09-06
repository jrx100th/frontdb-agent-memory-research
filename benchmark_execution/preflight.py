from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess

MANIFEST_SHA = "88a98a4e191729b0d9a00afb40ade9c2985b3e4fa160034df58a4b01e83ebb4a"
ENV_PACKET_SHA = "26566fea65da18291160d2f45598942182d4edf23e1b95485734bc196a67945e"
PROVIDER_BASE_SHA = "f76d53a0e94e3837023542b48c5b2226b21c3ad37cae446272a2743b7579ee5d"
TB_SHA = "2b0442c3c583b710ca8da14c8e601b99f2f1f244"


def file_sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def git(repo: Path, *args: str) -> str:
    return subprocess.check_output(["git", "-C", str(repo), *args], text=True).strip()


def resolve_ref(ref: str) -> tuple[str, str]:
    raw = subprocess.check_output(["docker", "buildx", "imagetools", "inspect", ref, "--raw"])
    registry_digest = "sha256:" + hashlib.sha256(raw).hexdigest()
    obj = json.loads(raw)
    platform_digest = registry_digest
    if isinstance(obj, dict) and isinstance(obj.get("manifests"), list):
        matches = [
            m for m in obj["manifests"]
            if (m.get("platform") or {}).get("os") == "linux"
            and (m.get("platform") or {}).get("architecture") == "amd64"
        ]
        if not matches:
            raise RuntimeError(f"INFRASTRUCTURE_INVALID_NO_LINUX_AMD64:{ref}")
        platform_digest = matches[0]["digest"]
    return registry_digest, platform_digest


def canon(obj) -> bytes:
    return (json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True) + "\n").encode("utf-8")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo-root", type=Path, required=True)
    ap.add_argument("--tb-root", type=Path, required=True)
    ap.add_argument("--task", required=True)
    ap.add_argument("--condition", choices=list("ABCD"), required=True)
    ap.add_argument("--task-order", type=int, required=True)
    ap.add_argument("--condition-position", type=int, required=True)
    ap.add_argument("--run-id", required=True)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()

    root = args.repo_root.resolve()
    tb = args.tb_root.resolve()
    manifest_path = root / "manifests/experiment_manifest.final.json"
    packet_path = root / "reproducibility/TASK_ENVIRONMENT_IDENTITIES.json"

    if file_sha(manifest_path) != MANIFEST_SHA:
        raise RuntimeError("MANIFEST_IDENTITY_FAILURE")
    if file_sha(packet_path) != ENV_PACKET_SHA:
        raise RuntimeError("INFRASTRUCTURE_INVALID_ENV_PACKET_HASH")

    base = os.environ.get("TOKENROUTER_BASE_URL")
    if not base or hashlib.sha256(base.encode("utf-8")).hexdigest() != PROVIDER_BASE_SHA:
        raise RuntimeError("CONFIGURATION_INVALID_PROVIDER_BASE")
    if not os.environ.get("TOKENROUTER_API_KEY"):
        raise RuntimeError("CONFIGURATION_INVALID_PROVIDER_KEY_MISSING")

    if git(tb, "rev-parse", "HEAD") != TB_SHA:
        raise RuntimeError("INFRASTRUCTURE_INVALID_TERMINAL_BENCH_REVISION")
    try:
        tag = git(tb, "describe", "--tags", "--exact-match", "HEAD")
    except subprocess.CalledProcessError as exc:
        raise RuntimeError("INFRASTRUCTURE_INVALID_TERMINAL_BENCH_TAG") from exc
    if tag != "v3.0.0":
        raise RuntimeError("INFRASTRUCTURE_INVALID_TERMINAL_BENCH_TAG")

    packet = json.loads(packet_path.read_text(encoding="utf-8"))
    rec = packet["tasks"].get(args.task)
    expected_identity = packet["expected_task_environment_identity_sha256"].get(args.task)
    if rec is None or expected_identity is None:
        raise RuntimeError("INFRASTRUCTURE_INVALID_TASK_NOT_IN_PACKET")

    task_root = tb / "tasks" / args.task
    task_toml = task_root / "task.toml"
    env_root = task_root / "environment"
    task_rel = f"tasks/{args.task}/task.toml"
    env_rel = f"tasks/{args.task}/environment"
    if git(tb, "rev-parse", f"{TB_SHA}:{task_rel}") != rec["task_toml_git_blob_sha"]:
        raise RuntimeError("INFRASTRUCTURE_INVALID_TASK_TOML_BLOB")
    if file_sha(task_toml) != rec["task_toml_sha256"]:
        raise RuntimeError("INFRASTRUCTURE_INVALID_TASK_TOML_SHA256")
    if git(tb, "rev-parse", f"{TB_SHA}:{env_rel}") != rec["environment_git_tree_sha"]:
        raise RuntimeError("INFRASTRUCTURE_INVALID_ENVIRONMENT_TREE")

    for item in rec["container_definitions"]:
        path = tb / item["path"]
        if git(tb, "rev-parse", f"{TB_SHA}:{item['path']}") != item["git_blob_sha"]:
            raise RuntimeError("INFRASTRUCTURE_INVALID_CONTAINER_DEFINITION_BLOB")
        if file_sha(path) != item["sha256"]:
            raise RuntimeError("INFRASTRUCTURE_INVALID_CONTAINER_DEFINITION_SHA256")

    resolved = []
    for item in rec["external_base_images"]:
        registry_digest, platform_digest = resolve_ref(item["reference_at_freeze"])
        if registry_digest != item["resolved_registry_manifest_digest"]:
            raise RuntimeError("INFRASTRUCTURE_INVALID_MOVING_TAG_REGISTRY_DRIFT")
        if platform_digest != item["resolved_linux_amd64_manifest_digest"]:
            raise RuntimeError("INFRASTRUCTURE_INVALID_MOVING_TAG_PLATFORM_DRIFT")
        resolved.append(
            {
                "reference": item["reference_at_freeze"],
                "registry_digest": registry_digest,
                "linux_amd64_digest": platform_digest,
            }
        )

    # Identity is over the original immutable task record, before packet-level metadata was added.
    actual_identity = hashlib.sha256(canon(rec)).hexdigest()
    if actual_identity != expected_identity:
        raise RuntimeError("INFRASTRUCTURE_INVALID_TASK_COMPOSITE_IDENTITY")

    out = {
        "schema_version": 1,
        "status": "PASS",
        "manifest_sha256": MANIFEST_SHA,
        "environment_packet_sha256": ENV_PACKET_SHA,
        "provider_base_sha256": PROVIDER_BASE_SHA,
        "terminal_bench_revision": TB_SHA,
        "terminal_bench_tag": "v3.0.0",
        "task_id": args.task,
        "task_order": args.task_order,
        "condition": args.condition,
        "condition_order_position": args.condition_position,
        "run_id": args.run_id,
        "task_environment_identity_sha256": actual_identity,
        "external_base_images_verified": resolved,
        "provider_secret_exposed": False,
        "api_key_hashed": False,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(canon(out))
    print("FROZEN_PREFLIGHT=PASS")
    print(f"TASK={args.task} CONDITION={args.condition} RUN_ID={args.run_id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
