from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess

TB_SHA = "2b0442c3c583b710ca8da14c8e601b99f2f1f244"
ENV_PACKET_SHA256 = "26566fea65da18291160d2f45598942182d4edf23e1b95485734bc196a67945e"
DIGEST_RE = re.compile(r"digest:\s*(sha256:[0-9a-f]{64})")
DIGEST_FULL_RE = re.compile(r"sha256:[0-9a-f]{64}")

# Exact build contexts implied by the pinned Terminal-Bench compose definitions.
# Every other frozen task has only the main environment/Dockerfile.
EXTRA_BUILD_CONTEXTS: dict[str, dict[str, str]] = {
    "cumulative-layout-shift": {
        "barber-shop-data-backend": "barber-shop-data-backend",
    },
    "live-database-cutover": {
        "mysql-db": "mysql",
        "postgres-db": "postgres",
        "customer": "customer",
    },
}

# Image-only sidecars from the pinned compose source. These are not rebuilt;
# they are pinned directly to the already-frozen linux/amd64 manifest digest.
EXTERNAL_RUNTIME_SERVICES: dict[str, dict[str, str]] = {
    "live-database-cutover": {"redis": "redis:7-alpine"},
}


def canon(obj) -> bytes:
    return (json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True) + "\n").encode("utf-8")


def file_sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def repo_without_tag(ref: str) -> str:
    if "@" in ref:
        return ref.split("@", 1)[0]
    slash = ref.rfind("/")
    colon = ref.rfind(":")
    if colon > slash:
        return ref[:colon]
    return ref


def safe_component(value: str) -> str:
    return re.sub(r"[^a-z0-9._-]+", "-", value.lower()).strip("-")


def pin_external_bases(record: dict) -> dict[str, dict]:
    pinned: dict[str, dict] = {}
    for item in record["external_base_images"]:
        reference = str(item["reference_at_freeze"])
        digest = str(item["resolved_linux_amd64_manifest_digest"])
        if not DIGEST_FULL_RE.fullmatch(digest):
            raise RuntimeError(f"V1_INVALID_FROZEN_BASE_DIGEST:{reference}:{digest}")
        immutable = f"{repo_without_tag(reference)}@{digest}"
        subprocess.check_call(["docker", "pull", "--platform", "linux/amd64", immutable], stdout=subprocess.DEVNULL)
        # Force the frozen mutable reference to resolve locally to the exact frozen base.
        subprocess.check_call(["docker", "tag", immutable, reference])
        pinned[reference] = {"immutable_reference": immutable, "linux_amd64_manifest_digest": digest}
    return pinned


def publish_local_image(local_ref: str, repository: str, tag: str) -> dict:
    image_id = subprocess.check_output(["docker", "image", "inspect", local_ref, "--format", "{{.Id}}"], text=True).strip().lower()
    if not DIGEST_FULL_RE.fullmatch(image_id):
        raise RuntimeError(f"V1_LOCAL_IMAGE_ID_INVALID:{local_ref}:{image_id}")
    tagged = f"{repository}:{tag}"
    subprocess.check_call(["docker", "tag", image_id, tagged])
    pushed = subprocess.check_output(["docker", "push", tagged], text=True, stderr=subprocess.STDOUT)
    matches = DIGEST_RE.findall(pushed)
    if len(matches) != 1:
        raise RuntimeError(f"V1_PUSH_DIGEST_UNRESOLVED:{repository}:{matches}")
    registry_digest = matches[0]
    immutable = f"{repository}@{registry_digest}"
    raw = subprocess.check_output(["docker", "buildx", "imagetools", "inspect", immutable, "--raw"])
    raw_digest = "sha256:" + hashlib.sha256(raw).hexdigest()
    if raw_digest != registry_digest:
        raise RuntimeError(f"V1_REGISTRY_DIGEST_MISMATCH:{repository}:{raw_digest}!={registry_digest}")
    subprocess.check_call(["docker", "pull", "--platform", "linux/amd64", immutable], stdout=subprocess.DEVNULL)
    roundtrip = subprocess.check_output(["docker", "image", "inspect", immutable, "--format", "{{.Id}}"], text=True).strip().lower()
    if roundtrip != image_id:
        raise RuntimeError(f"V1_ROUNDTRIP_IMAGE_ID_MISMATCH:{repository}:{roundtrip}!={image_id}")
    return {
        "registry_manifest_digest": registry_digest,
        "immutable_image_reference": immutable,
        "runtime_image_id_at_materialization": image_id,
        "roundtrip_runtime_image_id": roundtrip,
        "transport_tag_non_authoritative": tag,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo-root", type=Path, required=True)
    ap.add_argument("--task-root", type=Path, required=True)
    ap.add_argument("--task", required=True)
    ap.add_argument("--task-order", type=int, required=True)
    ap.add_argument("--registry-owner", required=True)
    ap.add_argument("--transport-tag", required=True)
    ap.add_argument("--source-proof", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()

    packet_path = args.repo_root / "reproducibility/TASK_ENVIRONMENT_IDENTITIES.json"
    if file_sha(packet_path) != ENV_PACKET_SHA256:
        raise RuntimeError("INFRASTRUCTURE_INVALID_ENV_PACKET_HASH")
    packet = json.loads(packet_path.read_text(encoding="utf-8"))
    rec = packet["tasks"][args.task]
    expected_identity = packet["expected_task_environment_identity_sha256"][args.task]
    source_proof = json.loads(args.source_proof.read_text(encoding="utf-8"))
    if source_proof.get("status") != "PASS" or source_proof.get("terminal_bench_revision") != TB_SHA:
        raise RuntimeError("V1_SOURCE_PROOF_INVALID")
    if source_proof.get("task_environment_identity_sha256") != expected_identity:
        raise RuntimeError("V1_SOURCE_PROOF_IDENTITY_MISMATCH")

    environment = args.task_root / "environment"
    if not (environment / "Dockerfile").is_file():
        raise RuntimeError("V1_MAIN_DOCKERFILE_MISSING")

    pinned_bases = pin_external_bases(rec)
    build_contexts = {"main": ".", **EXTRA_BUILD_CONTEXTS.get(args.task, {})}
    built_services: dict[str, dict] = {}
    owner = safe_component(args.registry_owner)
    order2 = f"{args.task_order:02d}"

    # Canonical materialization: every build service is built exactly once in this pass.
    for service, relative_context in build_contexts.items():
        context = (environment / relative_context).resolve()
        local_ref = f"v1-local-{order2}-{safe_component(args.task)}-{safe_component(service)}:{args.transport_tag}"
        subprocess.check_call([
            "docker", "build", "--platform", "linux/amd64", "--pull=false", "-t", local_ref, str(context)
        ])
        repository = f"ghcr.io/{owner}/frontdb-agent-memory-v1-task{order2}-{safe_component(args.task)}-{safe_component(service)}"
        published = publish_local_image(local_ref, repository, args.transport_tag)
        built_services[service] = {
            "kind": "built",
            "build_context_relative_to_environment": relative_context,
            "image_repository": repository,
            **published,
        }

    external_services: dict[str, dict] = {}
    frozen_by_ref = {x["reference_at_freeze"]: x for x in rec["external_base_images"]}
    for service, original_ref in EXTERNAL_RUNTIME_SERVICES.get(args.task, {}).items():
        frozen = frozen_by_ref.get(original_ref)
        if frozen is None:
            raise RuntimeError(f"V1_EXTERNAL_SERVICE_NOT_IN_FROZEN_PACKET:{service}:{original_ref}")
        digest = frozen["resolved_linux_amd64_manifest_digest"]
        immutable = f"{repo_without_tag(original_ref)}@{digest}"
        subprocess.check_call(["docker", "pull", "--platform", "linux/amd64", immutable], stdout=subprocess.DEVNULL)
        external_services[service] = {
            "kind": "external_pinned",
            "original_reference": original_ref,
            "registry_manifest_digest": digest,
            "immutable_image_reference": immutable,
        }

    service_identity = {
        name: value["immutable_image_reference"]
        for name, value in sorted({**built_services, **external_services}.items())
    }
    task_bundle_sha256 = hashlib.sha256(canon(service_identity)).hexdigest()
    result = {
        "schema_version": 2,
        "experiment_version": "v1-environment-materialized",
        "task_order": args.task_order,
        "task_id": args.task,
        "terminal_bench_revision": TB_SHA,
        "task_environment_source_identity_sha256": expected_identity,
        "platform": "linux/amd64",
        "build_policy": "canonical_build_only_once_per_service_in_this_materialization_pass",
        "per_condition_rebuild_forbidden": True,
        "primary_service": "main",
        "primary_main_registry_manifest_digest": built_services["main"]["registry_manifest_digest"],
        "primary_main_immutable_image_reference": built_services["main"]["immutable_image_reference"],
        "task_environment_bundle_sha256": task_bundle_sha256,
        "service_identity": service_identity,
        "built_services": built_services,
        "external_pinned_services": external_services,
        "frozen_external_bases_materialized_locally": pinned_bases,
        "provider_calls": 0,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(canon(result))
    print(f"V1_TASK_BUNDLE_MATERIALIZED task={args.task} bundle_sha256={task_bundle_sha256}")
    print(f"V1_PRIMARY_MAIN={result['primary_main_immutable_image_reference']}")
    print(f"V1_BUILT_SERVICE_COUNT={len(built_services)}")
    print(f"V1_EXTERNAL_PINNED_SERVICE_COUNT={len(external_services)}")
    print("BENCHMARK_PROVIDER_CALLS=0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
