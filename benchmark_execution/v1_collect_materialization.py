from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

TB_SHA = "2b0442c3c583b710ca8da14c8e601b99f2f1f244"
ENV_PACKET_SHA256 = "26566fea65da18291160d2f45598942182d4edf23e1b95485734bc196a67945e"
TASKS = [
    (1, "atrx-vep-crispr"),
    (2, "batched-eval-parity"),
    (3, "cad-model"),
    (4, "cargo-flight-dispatch"),
    (5, "coq-block-bound"),
    (6, "cumulative-layout-shift"),
    (7, "data-anonymization"),
    (8, "live-database-cutover"),
    (9, "music-harmony"),
    (10, "uefi-bootkit"),
    (11, "production-planning"),
    (12, "wdm-design"),
]


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
    expected_identities = packet["expected_task_environment_identity_sha256"]

    files = sorted(args.input_root.rglob("materialization.json"))
    if len(files) != 12:
        raise RuntimeError(f"V1_MATERIALIZATION_RECORD_COUNT_INVALID:{len(files)}")
    records = [json.loads(path.read_text(encoding="utf-8")) for path in files]
    by_key = {(int(r["task_order"]), str(r["task_id"])): r for r in records}
    if len(by_key) != 12:
        raise RuntimeError("V1_MATERIALIZATION_DUPLICATE_TASK_RECORD")

    ordered = []
    for order, task in TASKS:
        rec = by_key.get((order, task))
        if rec is None:
            raise RuntimeError(f"V1_MATERIALIZATION_TASK_MISSING:{order}:{task}")
        if rec.get("task_environment_source_identity_sha256") != expected_identities[task]:
            raise RuntimeError(f"V1_MATERIALIZATION_SOURCE_IDENTITY_MISMATCH:{task}")
        digest = str(rec.get("registry_manifest_digest") or "")
        immutable = str(rec.get("immutable_image_reference") or "")
        runtime_id = str(rec.get("runtime_image_id_at_materialization") or "")
        if not digest.startswith("sha256:") or len(digest) != 71:
            raise RuntimeError(f"V1_MATERIALIZATION_DIGEST_INVALID:{task}")
        if immutable != f"{rec['image_repository']}@{digest}":
            raise RuntimeError(f"V1_MATERIALIZATION_IMMUTABLE_REFERENCE_INVALID:{task}")
        if rec.get("roundtrip_runtime_image_id") != runtime_id:
            raise RuntimeError(f"V1_MATERIALIZATION_ROUNDTRIP_MISMATCH:{task}")
        if rec.get("platform") != "linux/amd64" or rec.get("provider_calls") != 0:
            raise RuntimeError(f"V1_MATERIALIZATION_PLATFORM_OR_PROVIDER_INVALID:{task}")
        ordered.append(rec)

    manifest = {
        "schema_version": 1,
        "manifest_kind": "v1-task-immutable-image-manifest",
        "experiment_version": "v1-environment-materialized",
        "terminal_bench_revision": TB_SHA,
        "terminal_bench_tag": "v3.0.0",
        "environment_packet_sha256": ENV_PACKET_SHA256,
        "image_count": 12,
        "identity_authority": "registry_manifest_digest; execution uses immutable_image_reference only; transport tags are non-authoritative",
        "per_condition_rebuild_forbidden": True,
        "provider_calls_during_materialization": 0,
        "images": ordered,
    }
    payload = canon(manifest)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(payload)
    digest = hashlib.sha256(payload).hexdigest()
    args.hash_output.write_text(digest + "\n", encoding="utf-8")
    print(f"V1_IMMUTABLE_IMAGES_BUILT={len(ordered)}")
    print(f"V1_TASK_IMAGE_MANIFEST_SHA256={digest}")
    print("PROVIDER_CALLS_DURING_V1_MATERIALIZATION=0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
