from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess

TB_SHA = "2b0442c3c583b710ca8da14c8e601b99f2f1f244"
TB_TAG = "v3.0.0"
ENV_PACKET_SHA256 = "26566fea65da18291160d2f45598942182d4edf23e1b95485734bc196a67945e"


def file_sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def git(repo: Path, *args: str) -> str:
    return subprocess.check_output(["git", "-C", str(repo), *args], text=True).strip()


def canon(obj) -> bytes:
    return (json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True) + "\n").encode("utf-8")


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
        if len(matches) != 1:
            raise RuntimeError(f"INFRASTRUCTURE_INVALID_NO_UNIQUE_LINUX_AMD64:{ref}")
        platform_digest = str(matches[0]["digest"])
    return registry_digest, platform_digest


def verify(repo_root: Path, tb_root: Path, task: str) -> dict:
    packet_path = repo_root / "reproducibility/TASK_ENVIRONMENT_IDENTITIES.json"
    if file_sha(packet_path) != ENV_PACKET_SHA256:
        raise RuntimeError("INFRASTRUCTURE_INVALID_ENV_PACKET_HASH")
    if git(tb_root, "rev-parse", "HEAD") != TB_SHA:
        raise RuntimeError("INFRASTRUCTURE_INVALID_TERMINAL_BENCH_REVISION")
    try:
        tag = git(tb_root, "describe", "--tags", "--exact-match", "HEAD")
    except subprocess.CalledProcessError as exc:
        raise RuntimeError("INFRASTRUCTURE_INVALID_TERMINAL_BENCH_TAG") from exc
    if tag != TB_TAG:
        raise RuntimeError("INFRASTRUCTURE_INVALID_TERMINAL_BENCH_TAG")

    packet = json.loads(packet_path.read_text(encoding="utf-8"))
    rec = (packet.get("tasks") or {}).get(task)
    expected_identity = (packet.get("expected_task_environment_identity_sha256") or {}).get(task)
    if not isinstance(rec, dict) or not expected_identity:
        raise RuntimeError("INFRASTRUCTURE_INVALID_TASK_NOT_IN_PACKET")

    task_root = tb_root / "tasks" / task
    task_toml = task_root / "task.toml"
    task_rel = f"tasks/{task}/task.toml"
    env_rel = f"tasks/{task}/environment"
    if git(tb_root, "rev-parse", f"{TB_SHA}:{task_rel}") != rec["task_toml_git_blob_sha"]:
        raise RuntimeError("INFRASTRUCTURE_INVALID_TASK_TOML_BLOB")
    if file_sha(task_toml) != rec["task_toml_sha256"]:
        raise RuntimeError("INFRASTRUCTURE_INVALID_TASK_TOML_SHA256")
    if git(tb_root, "rev-parse", f"{TB_SHA}:{env_rel}") != rec["environment_git_tree_sha"]:
        raise RuntimeError("INFRASTRUCTURE_INVALID_ENVIRONMENT_TREE")

    for item in rec["container_definitions"]:
        path = tb_root / item["path"]
        if git(tb_root, "rev-parse", f"{TB_SHA}:{item['path']}") != item["git_blob_sha"]:
            raise RuntimeError("INFRASTRUCTURE_INVALID_CONTAINER_DEFINITION_BLOB")
        if file_sha(path) != item["sha256"]:
            raise RuntimeError("INFRASTRUCTURE_INVALID_CONTAINER_DEFINITION_SHA256")

    resolved = []
    for item in rec["external_base_images"]:
        registry_digest, platform_digest = resolve_ref(item["reference_at_freeze"])
        if registry_digest != item["resolved_registry_manifest_digest"]:
            raise RuntimeError(
                "INFRASTRUCTURE_INVALID_MOVING_TAG_REGISTRY_DRIFT:"
                f"{item['reference_at_freeze']}:{registry_digest}!={item['resolved_registry_manifest_digest']}"
            )
        if platform_digest != item["resolved_linux_amd64_manifest_digest"]:
            raise RuntimeError(
                "INFRASTRUCTURE_INVALID_MOVING_TAG_PLATFORM_DRIFT:"
                f"{item['reference_at_freeze']}:{platform_digest}!={item['resolved_linux_amd64_manifest_digest']}"
            )
        resolved.append(
            {
                "reference": item["reference_at_freeze"],
                "registry_manifest_digest": registry_digest,
                "linux_amd64_manifest_digest": platform_digest,
            }
        )

    actual_identity = hashlib.sha256(canon(rec)).hexdigest()
    if actual_identity != expected_identity:
        raise RuntimeError("INFRASTRUCTURE_INVALID_TASK_COMPOSITE_IDENTITY")

    return {
        "schema_version": 1,
        "status": "PASS",
        "terminal_bench_revision": TB_SHA,
        "terminal_bench_tag": TB_TAG,
        "environment_packet_sha256": ENV_PACKET_SHA256,
        "task_id": task,
        "task_environment_identity_sha256": actual_identity,
        "task_toml_git_blob_sha": rec["task_toml_git_blob_sha"],
        "environment_git_tree_sha": rec["environment_git_tree_sha"],
        "external_base_images_verified": resolved,
        "provider_calls": 0,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo-root", type=Path, required=True)
    ap.add_argument("--tb-root", type=Path, required=True)
    ap.add_argument("--task", required=True)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()
    result = verify(args.repo_root.resolve(), args.tb_root.resolve(), args.task)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(canon(result))
    print(f"V1_TASK_SOURCE_IDENTITY=PASS task={args.task} identity={result['task_environment_identity_sha256']}")
    print("PROVIDER_CALLS=0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
