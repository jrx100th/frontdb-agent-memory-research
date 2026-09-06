from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re

TB_SHA = "2b0442c3c583b710ca8da14c8e601b99f2f1f244"
ENV_PACKET_SHA256 = "26566fea65da18291160d2f45598942182d4edf23e1b95485734bc196a67945e"
TASKS = [
    (1, "atrx-vep-crispr"),(2, "batched-eval-parity"),(3, "cad-model"),(4, "cargo-flight-dispatch"),
    (5, "coq-block-bound"),(6, "cumulative-layout-shift"),(7, "data-anonymization"),(8, "live-database-cutover"),
    (9, "music-harmony"),(10, "uefi-bootkit"),(11, "production-planning"),(12, "wdm-design"),
]
DIGEST_RE = re.compile(r"sha256:[0-9a-f]{64}")


def canon(obj) -> bytes:
    return (json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True) + "\n").encode("utf-8")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input-root", type=Path, required=True)
    ap.add_argument("--environment-packet", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument("--hash-output", type=Path, required=True)
    args = ap.parse_args()

    packet_bytes = args.environment_packet.read_bytes()
    if hashlib.sha256(packet_bytes).hexdigest() != ENV_PACKET_SHA256:
        raise RuntimeError("INFRASTRUCTURE_INVALID_ENV_PACKET_HASH")
    packet = json.loads(packet_bytes)
    expected = packet["expected_task_environment_identity_sha256"]
    files = sorted(args.input_root.rglob("bundle.json"))
    if len(files) != 12:
        raise RuntimeError(f"V1_BUNDLE_RECORD_COUNT_INVALID:{len(files)}")
    records = [json.loads(p.read_text(encoding="utf-8")) for p in files]
    by_key = {(int(r["task_order"]), str(r["task_id"])): r for r in records}
    if len(by_key) != 12:
        raise RuntimeError("V1_BUNDLE_DUPLICATE_TASK_RECORD")

    ordered = []
    total_built_services = 0
    total_pinned_external_services = 0
    for order, task in TASKS:
        r = by_key.get((order, task))
        if r is None:
            raise RuntimeError(f"V1_BUNDLE_TASK_MISSING:{order}:{task}")
        if r.get("terminal_bench_revision") != TB_SHA or r.get("task_environment_source_identity_sha256") != expected[task]:
            raise RuntimeError(f"V1_BUNDLE_SOURCE_IDENTITY_INVALID:{task}")
        if r.get("provider_calls") != 0 or r.get("per_condition_rebuild_forbidden") is not True:
            raise RuntimeError(f"V1_BUNDLE_POLICY_INVALID:{task}")
        if not DIGEST_RE.fullmatch(str(r.get("primary_main_registry_manifest_digest") or "")):
            raise RuntimeError(f"V1_BUNDLE_MAIN_DIGEST_INVALID:{task}")
        services = r.get("service_identity") or {}
        if "main" not in services or not services:
            raise RuntimeError(f"V1_BUNDLE_SERVICE_IDENTITY_INVALID:{task}")
        recomputed = hashlib.sha256(canon({k: services[k] for k in sorted(services)})).hexdigest()
        if recomputed != r.get("task_environment_bundle_sha256"):
            raise RuntimeError(f"V1_BUNDLE_HASH_INVALID:{task}")
        for service, ref in services.items():
            if "@sha256:" not in str(ref):
                raise RuntimeError(f"V1_BUNDLE_MUTABLE_SERVICE_REFERENCE:{task}:{service}:{ref}")
        total_built_services += len(r.get("built_services") or {})
        total_pinned_external_services += len(r.get("external_pinned_services") or {})
        ordered.append(r)

    manifest = {
        "schema_version": 2,
        "manifest_kind": "v1-immutable-task-environment-bundle-manifest",
        "experiment_version": "v1-environment-materialized",
        "terminal_bench_revision": TB_SHA,
        "terminal_bench_tag": "v3.0.0",
        "environment_packet_sha256": ENV_PACKET_SHA256,
        "task_environment_bundle_count": 12,
        "built_service_image_count": total_built_services,
        "external_pinned_service_count": total_pinned_external_services,
        "identity_authority": "per-service immutable repo@sha256 reference; task_environment_bundle_sha256 canonically binds the complete agent-runtime service set",
        "per_condition_rebuild_forbidden": True,
        "provider_calls_during_materialization": 0,
        "tasks": ordered,
    }
    payload = canon(manifest)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(payload)
    digest = hashlib.sha256(payload).hexdigest()
    args.hash_output.write_text(digest + "\n", encoding="utf-8")
    print("V1_IMMUTABLE_TASK_ENVIRONMENT_BUNDLES=12")
    print(f"V1_BUILT_SERVICE_IMAGES={total_built_services}")
    print(f"V1_EXTERNAL_PINNED_SERVICES={total_pinned_external_services}")
    print(f"V1_TASK_IMAGE_MANIFEST_SHA256={digest}")
    print("PROVIDER_CALLS_DURING_V1_MATERIALIZATION=0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
